import logging
import os
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, ValidationError

from .auth import get_current_uid
from .config import get_sites, get_form_types, get_all_form_fields, get_app_config
from .services.ai_extractor import extract_incident, extract_safebase
from .services.firebase_client import push_incident_form, push_safebase_form
from .schemas.combined_incident_schema import CombinedIncidentSchema
from .schemas.safebase_schema import SafeBaseFormSchema
from .schemas.transcript_schema import TranscriptSchema

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_LENGTH = int(os.getenv("MAX_TRANSCRIPT_LENGTH", "5000"))
_RTDB_PUSH_ID_RE = re.compile(r"^-[A-Za-z0-9_-]{19}$")


# ── Response models ──────────────────────────────────────────────────

class ConfigResponse(BaseModel):
    app_name: str
    app_subtitle: str
    default_site: str
    default_form_type: str
    speech_recognition: dict
    sites: list
    form_types: list
    field_options: dict


class SubmitResponse(BaseModel):
    key: str


# ── Config endpoint (frontend reads this instead of hardcoding) ──────


@router.get("/api/config", response_model=ConfigResponse)
def get_config():
    """
    Returns all UI-facing configuration.
    Frontend fetches this once on load instead of hardcoding values.
    """
    app_config = get_app_config()
    return {
        "app_name": app_config["app_name"],
        "app_subtitle": app_config["app_subtitle"],
        "default_site": app_config["default_site"],
        "default_form_type": app_config["default_form_type"],
        "speech_recognition": app_config["speech_recognition"],
        "sites": get_sites(),
        "form_types": get_form_types(),
        "field_options": get_all_form_fields(),
    }


@router.get("/api/dashboard")
def get_dashboard():
    """Returns dashboard impact statistics from Firebase."""
    from .services.firebase_client import get_dashboard_stats
    stats = get_dashboard_stats()
    return stats


@router.get("/api/me")
def me(uid: str = Depends(get_current_uid)):
    """Return the authenticated user's own profile including role."""
    from .services.firebase_client import get_user_profile
    profile = get_user_profile(uid)
    if not profile:
        raise HTTPException(404, detail="User not found")
    return {
        "uid": uid,
        "firstName": profile.get("firstName", ""),
        "lastName": profile.get("lastName", ""),
        "userLevel": profile.get("userLevel", ""),
        "site": profile.get("site", ""),
        "accountStatus": profile.get("accountStatus", ""),
    }


# ── Monitor / hierarchy endpoints ────────────────────────────────────


@router.get("/api/team/{uid}")
def get_team(uid: str, caller_uid: str = Depends(get_current_uid)):
    """
    Return the direct reports of the given user, grouped by userLevel.
    The caller must be the user themselves or an ancestor in the
    createdBy hierarchy.
    """
    from .services.firebase_client import (
        get_all_users, get_direct_reports, is_ancestor, get_user_profile,
    )

    all_users = get_all_users()

    if not is_ancestor(caller_uid, uid, all_users):
        raise HTTPException(403, detail="Access denied: user is outside your hierarchy")

    profile = get_user_profile(uid)
    if not profile:
        raise HTTPException(404, detail="User not found")

    reports = get_direct_reports(uid, all_users)

    def _summarise(u: dict) -> dict:
        return {
            "uid": u["uid"],
            "firstName": u.get("firstName", ""),
            "lastName": u.get("lastName", ""),
            "userLevel": u.get("userLevel", ""),
            "site": u.get("site", ""),
            "accountStatus": u.get("accountStatus", ""),
        }

    return {
        "user": {
            "uid": uid,
            "firstName": profile.get("firstName", ""),
            "lastName": profile.get("lastName", ""),
            "userLevel": profile.get("userLevel", ""),
            "site": profile.get("site", ""),
        },
        "teamLeaders": [
            _summarise(r) for r in reports if r.get("userLevel") == "teamLeader"
        ],
        "teamMembers": [
            _summarise(r) for r in reports if r.get("userLevel") == "teamMember"
        ],
    }


@router.get("/api/monitor/{uid}/forms")
def get_monitor_forms(uid: str, caller_uid: str = Depends(get_current_uid)):
    """
    Return incidentForms and safeSpaceForms created by the given user.
    The caller must be the user themselves or an ancestor in the hierarchy.
    """
    from .services.firebase_client import get_all_users, is_ancestor, get_forms_by_user

    all_users = get_all_users()

    if not is_ancestor(caller_uid, uid, all_users):
        raise HTTPException(403, detail="Access denied: user is outside your hierarchy")

    return get_forms_by_user(uid)


# ── Incident CRUD (view / edit / delete) ──────────────────────────────


def _check_incident_access(form_id: str, caller_uid: str):
    """Verify the caller is the incident creator or an ancestor. Returns the incident data."""
    from .services.firebase_client import get_all_users, is_ancestor, get_incident_full

    if not _RTDB_PUSH_ID_RE.match(form_id):
        raise HTTPException(status_code=400, detail="Invalid form_id")

    data = get_incident_full(form_id)
    if not data:
        raise HTTPException(404, detail="Incident not found")

    owner_uid = data["incident"].get("createdBy", "")
    all_users = get_all_users()

    if not is_ancestor(caller_uid, owner_uid, all_users):
        raise HTTPException(403, detail="Access denied: incident is outside your hierarchy")

    return data


@router.get("/api/forms/incident/{form_id}")
def get_incident(form_id: str, caller_uid: str = Depends(get_current_uid)):
    """Fetch full incident data (incident + clients) for editing."""
    return _check_incident_access(form_id, caller_uid)


def _check_safebase_access(form_id: str, caller_uid: str):
    """Verify the caller is the SafeBase creator or an ancestor. Returns the SafeBase data."""
    from .services.firebase_client import get_all_users, is_ancestor, get_safebase_full

    if not _RTDB_PUSH_ID_RE.match(form_id):
        raise HTTPException(status_code=400, detail="Invalid form_id")

    data = get_safebase_full(form_id)
    if not data:
        raise HTTPException(404, detail="SafeBase form not found")

    owner_uid = data.get("createdBy", "")
    all_users = get_all_users()

    if not is_ancestor(caller_uid, owner_uid, all_users):
        raise HTTPException(403, detail="Access denied: SafeBase form is outside your hierarchy")

    return data


@router.get("/api/forms/safebase/{form_id}")
def get_safebase(form_id: str, caller_uid: str = Depends(get_current_uid)):
    """Fetch full SafeBase form data."""
    return _check_safebase_access(form_id, caller_uid)


class UpdateIncidentRequest(BaseModel):
    form_data: dict
    status: str = "completed"


@router.put("/api/forms/incident/{form_id}")
def update_incident_route(form_id: str, req: UpdateIncidentRequest, caller_uid: str = Depends(get_current_uid)):
    """Update an existing incident. Caller must be creator or ancestor."""
    from .services.firebase_client import update_incident

    _check_incident_access(form_id, caller_uid)

    validated = CombinedIncidentSchema(**req.form_data)
    update_incident(
        form_id,
        validated.model_dump(by_alias=True, exclude_none=True),
        caller_uid,
        req.status,
    )
    return {"status": "updated", "form_id": form_id}


@router.delete("/api/forms/incident/{form_id}")
def delete_incident_route(form_id: str, caller_uid: str = Depends(get_current_uid)):
    """Delete an incident and its clients. Caller must be creator or ancestor."""
    from .services.firebase_client import delete_incident

    _check_incident_access(form_id, caller_uid)
    delete_incident(form_id)
    return {"status": "deleted", "form_id": form_id}


class IncidentNarrativeRequest(BaseModel):
    """Current incident form state (same shape as /api/submit form_data for incidents)."""

    form_data: dict


@router.post("/api/incident/narrative")
def post_incident_narrative(
    req: IncidentNarrativeRequest,
    caller_uid: str = Depends(get_current_uid),
):
    """
    Generate incidentDescription and incidentOutcome drafts from structured data
    plus quickNote. Authenticated; does not read or write Firebase.
    Per-user rate limit (default 10/min, env-tunable) limits LLM spend.
    """
    from .services.ai_extractor import generate_incident_narrative
    from .services.narrative_rate_limit import enforce_incident_narrative_rate_limit

    try:
        enforce_incident_narrative_rate_limit(caller_uid)
        return generate_incident_narrative(req.form_data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation failed: {e}") from e
    except ValueError as e:
        msg = str(e)
        if "Rate limit" in msg:
            raise HTTPException(status_code=429, detail=msg) from e
        raise HTTPException(status_code=502, detail=msg) from e
    except Exception as e:
        logger.exception("Incident narrative generation failed")
        raise HTTPException(
            status_code=502,
            detail="Narrative generation failed. Please try again later.",
        ) from e


@router.get("/api/geocode/reverse")
def reverse_geocode_route(
    lat: float,
    lon: float,
    caller_uid: str = Depends(get_current_uid),
):
    """
    Reverse geocode coordinates using a Nominatim-backed proxy.

    Authenticated to prevent anonymous abuse. Applies a small in-memory cache and
    rate limiting. Does not write Firebase.
    """
    from .services.geocode import reverse_geocode

    # Identify ourselves per Nominatim usage policy.
    # Prefer env override so deployments can set a valid contact string.
    ua = os.getenv("NOMINATIM_USER_AGENT", "StreetKind-AI/0.1 (contact: ops@streetkind.example)")

    try:
        res = reverse_geocode(lat=lat, lon=lon, caller_key=caller_uid, user_agent=ua)
    except ValueError as e:
        raise HTTPException(status_code=429 if "Rate limit" in str(e) else 502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Reverse geocode failed: {str(e)}") from e

    return {
        "address": res.address,
        "latitude": res.latitude,
        "longitude": res.longitude,
    }


@router.get("/api/health")
def health():
    return {"status": "ok"}


# ── Transcript + audio storage ────────────────────────────────────────

MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_BYTES", str(20 * 1024 * 1024)))  # 20MB default
_ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/webm;codecs=opus", "audio/mp4", "audio/mpeg", "audio/ogg"}


@router.get("/api/forms/incident/{form_id}/transcripts")
def list_incident_transcripts(form_id: str, caller_uid: str = Depends(get_current_uid)):
    """Return every transcript linked to the incident, oldest first."""
    from .services.firebase_client import get_transcripts_for_incident

    _check_incident_access(form_id, caller_uid)
    return {"transcripts": get_transcripts_for_incident(form_id)}


class CreateTranscriptRequest(BaseModel):
    text: str
    audioDurationMs: int = 0
    extractionMeta: dict | None = None


@router.post("/api/forms/incident/{form_id}/transcripts")
def create_transcript(
    form_id: str,
    req: CreateTranscriptRequest,
    caller_uid: str = Depends(get_current_uid),
):
    """Create a transcript record linked to the incident. Audio is uploaded separately."""
    from .services.firebase_client import push_transcript

    _check_incident_access(form_id, caller_uid)

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")
    if len(req.text) > MAX_TRANSCRIPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Transcript too long ({len(req.text)} chars). Max: {MAX_TRANSCRIPT_LENGTH}",
        )

    validated = TranscriptSchema(
        text=req.text,
        audioDurationMs=req.audioDurationMs,
        extractionMeta=req.extractionMeta or {},
    )
    transcript_id = push_transcript(
        form_id, validated.model_dump(exclude={"incidentId"}), caller_uid,
    )
    return {"transcriptId": transcript_id}


_AUDIO_MAGIC = {
    b"\x1a\x45\xdf\xa3": "webm/matroska EBML",  # WebM + MKV
    b"OggS": "ogg",
    b"ID3": "mp3 (with ID3 tag)",
    b"\xff\xfb": "mp3 (MPEG frame)",
    b"\xff\xf3": "mp3 (MPEG frame)",
    b"\xff\xf2": "mp3 (MPEG frame)",
}


def _looks_like_audio(head: bytes) -> bool:
    """Reject payloads whose first bytes don't match any allowed audio magic.

    MP4/M4A uses an ftyp box at bytes 4-8, so we handle it separately.
    """
    if not head:
        return False
    if head[4:8] == b"ftyp":
        return True  # MP4 / M4A / M4B
    return any(head.startswith(prefix) for prefix in _AUDIO_MAGIC)


@router.post("/api/forms/incident/{form_id}/transcripts/{transcript_id}/audio")
async def upload_transcript_audio(
    form_id: str,
    transcript_id: str,
    audio: UploadFile = File(...),
    caller_uid: str = Depends(get_current_uid),
):
    """Upload an audio blob for an existing transcript. Updates transcripts/{id}/audioUrl."""
    import logging
    from firebase_admin import db as _db
    from .services.firebase_client import upload_audio, delete_audio_blob

    _log = logging.getLogger(__name__)

    _check_incident_access(form_id, caller_uid)

    if not _RTDB_PUSH_ID_RE.match(transcript_id):
        raise HTTPException(status_code=400, detail="Invalid transcript_id")

    if not os.getenv("FIREBASE_STORAGE_BUCKET"):
        raise HTTPException(
            status_code=503,
            detail="Audio storage is not configured on this deployment",
        )

    content_type = audio.content_type or ""
    if content_type.split(";")[0].strip() not in {t.split(";")[0] for t in _ALLOWED_AUDIO_TYPES}:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {content_type}")

    body = await audio.read()
    if len(body) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio too large ({len(body)} bytes). Max: {MAX_AUDIO_BYTES}",
        )
    if not body:
        raise HTTPException(status_code=400, detail="Empty audio blob")

    # Magic-byte check prevents the endpoint from becoming a file-upload backdoor
    # for arbitrary binary content that only *claims* to be audio.
    if not _looks_like_audio(body[:16]):
        raise HTTPException(
            status_code=400,
            detail="Payload does not look like a supported audio container",
        )

    # Make sure the transcript actually belongs to this incident before writing.
    existing = _db.reference(f"transcripts/{transcript_id}").get()
    if not existing or existing.get("incidentId") != form_id:
        raise HTTPException(status_code=404, detail="Transcript not found for this incident")

    blob_path = upload_audio(form_id, transcript_id, body, content_type)
    try:
        # Store the blob PATH (not a URL). Signed URLs are generated on read.
        _db.reference(f"transcripts/{transcript_id}/audioPath").set(blob_path)
    except Exception as e:
        # Compensate: the blob is already in Storage. If we can't persist the
        # path on the transcript, delete the blob so it can't orphan.
        _log.error(
            "Failed to persist audioPath for transcript=%s; compensating by deleting blob: %s",
            transcript_id, e,
        )
        delete_audio_blob(form_id, transcript_id)
        raise HTTPException(status_code=500, detail="Failed to persist audio path")

    from .services.firebase_client import signed_audio_url
    signed_url = signed_audio_url(blob_path)
    if not signed_url:
        # Rare: upload + DB write succeeded but signing failed (credentials
        # misconfigured?). Return the path so the client can retry the fetch;
        # the blob is safe because it's private without a signed URL.
        _log.warning(
            "Uploaded %s but failed to mint signed URL - client will see empty audioUrl",
            blob_path,
        )
    return {"audioUrl": signed_url or ""}


# ── Step 1: AI extracts structured data from transcript ──────────────


class ExtractRequest(BaseModel):
    transcript: str
    form_type: str
    site: str = ""


_EXTRACTORS = {
    "incident": extract_incident,
    "safebase": extract_safebase,
}


@router.post("/api/extract")
def extract_form(req: ExtractRequest):
    """
    Voice transcript -> AI structured output -> JSON returned to frontend.
    The volunteer reviews this before anything is saved.
    """
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")

    if len(req.transcript) > MAX_TRANSCRIPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Transcript too long ({len(req.transcript)} chars). Max: {MAX_TRANSCRIPT_LENGTH}",
        )

    valid_form_keys = [ft["key"] for ft in get_form_types()]
    if req.form_type not in valid_form_keys:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {req.form_type}")

    extractor = _EXTRACTORS.get(req.form_type)
    if not extractor:
        raise HTTPException(
            status_code=501,
            detail=f"Extraction not implemented for form type: {req.form_type}",
        )

    return extractor(req.transcript, req.site)


# ── Step 2: Volunteer reviews, edits, then submits ───────────────────


class SubmitRequest(BaseModel):
    form_type: str
    form_data: dict
    status: str = "completed"


_SUBMITTERS = {
    "incident": (CombinedIncidentSchema, push_incident_form),
    "safebase": (SafeBaseFormSchema, push_safebase_form),
}


@router.post("/api/submit", response_model=SubmitResponse)
def submit_form(req: SubmitRequest, caller_uid: str = Depends(get_current_uid)):
    """
    Accepts the reviewed/edited form data and writes it to Firebase.
    Requires a valid Firebase ID token; createdBy is always the token UID.
    Intentionally separate from /api/extract so the volunteer
    always has a chance to review before anything hits the database.
    """
    valid_form_keys = [ft["key"] for ft in get_form_types()]
    if req.form_type not in valid_form_keys:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {req.form_type}")

    entry = _SUBMITTERS.get(req.form_type)
    if not entry:
        raise HTTPException(
            status_code=501,
            detail=f"Submission not implemented for form type: {req.form_type}",
        )

    schema_class, push_fn = entry

    try:
        validated = schema_class(**req.form_data)
        push_kwargs = {
            "data": validated.model_dump(by_alias=True, exclude_none=True),
            "user_uid": caller_uid,
        }
        if req.form_type == "incident":
            push_kwargs["status"] = req.status
        key = push_fn(**push_kwargs)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation failed: {str(e)}")

    return {"key": key}
