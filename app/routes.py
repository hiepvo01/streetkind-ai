import os
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import get_current_uid
from .config import get_sites, get_form_types, get_all_form_fields, get_app_config
from .services.ai_extractor import extract_incident, extract_safebase
from .services.firebase_client import push_incident_form, push_safebase_form
from .schemas.combined_incident_schema import CombinedIncidentSchema
from .schemas.safebase_schema import SafeBaseFormSchema

router = APIRouter()

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


class UpdateIncidentRequest(BaseModel):
    form_data: dict
    status: str = "completed"


@router.put("/api/forms/incident/{form_id}")
def update_incident_route(form_id: str, req: UpdateIncidentRequest, caller_uid: str = Depends(get_current_uid)):
    """Update an existing incident. Caller must be creator or ancestor."""
    from .services.firebase_client import update_incident

    _check_incident_access(form_id, caller_uid)

    validated = CombinedIncidentSchema(**req.form_data)
    update_incident(form_id, validated.model_dump(by_alias=True), caller_uid, req.status)
    return {"status": "updated", "form_id": form_id}


@router.delete("/api/forms/incident/{form_id}")
def delete_incident_route(form_id: str, caller_uid: str = Depends(get_current_uid)):
    """Delete an incident and its clients. Caller must be creator or ancestor."""
    from .services.firebase_client import delete_incident

    _check_incident_access(form_id, caller_uid)
    delete_incident(form_id)
    return {"status": "deleted", "form_id": form_id}


@router.get("/api/health")
def health():
    return {"status": "ok"}


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
        push_kwargs = {"data": validated.model_dump(by_alias=True), "user_uid": caller_uid}
        if req.form_type == "incident":
            push_kwargs["status"] = req.status
        key = push_fn(**push_kwargs)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation failed: {str(e)}")

    return {"key": key}
