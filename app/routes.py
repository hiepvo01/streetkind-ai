import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .config import get_sites, get_form_types, get_all_form_fields, get_app_config
from .services.ai_extractor import extract_incident, extract_safebase
from .services.firebase_client import push_incident_form, push_safebase_form
from .schemas.combined_incident_schema import CombinedIncidentSchema
from .schemas.safebase_schema import SafeBaseFormSchema

router = APIRouter()

MAX_TRANSCRIPT_LENGTH = int(os.getenv("MAX_TRANSCRIPT_LENGTH", "5000"))


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


@router.get("/api/user/{uid}")
def get_user_profile(uid: str):
    """Fetch user profile from RTDB."""
    from .services.firebase_client import get_user_profile
    profile = get_user_profile(uid)
    if not profile:
        raise HTTPException(404, detail="User not found")
    return profile


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
    user_uid: str = Field(..., min_length=1)


_SUBMITTERS = {
    "incident": (CombinedIncidentSchema, push_incident_form),
    "safebase": (SafeBaseFormSchema, push_safebase_form),
}


@router.post("/api/submit", response_model=SubmitResponse)
def submit_form(req: SubmitRequest):
    """
    Accepts the reviewed/edited form data and writes it to Firebase.
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
        key = push_fn(validated.model_dump(by_alias=True), req.user_uid)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation failed: {str(e)}")

    return {"key": key}
