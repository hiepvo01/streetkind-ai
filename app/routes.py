from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .config import get_sites, get_form_types, get_all_form_fields, get_app_config
from .services.ai_extractor import extract_incident, extract_safebase
from .services.firebase_client import push_incident_form, push_safebase_form
from .schemas.incident_schema import IncidentFormSchema
from .schemas.safebase_schema import SafeBaseFormSchema

router = APIRouter()


# ── Config endpoints (frontend reads these instead of hardcoding) ────


@router.get("/api/config")
async def get_config():
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


# ── Step 1: AI extracts structured data from transcript ──────────────


class ExtractRequest(BaseModel):
    transcript: str
    form_type: str
    site: str = ""


@router.post("/api/extract")
async def extract_form(req: ExtractRequest):
    """
    Voice transcript -> AI structured output -> JSON returned to frontend.
    The volunteer reviews this before anything is saved.
    """
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")

    valid_form_keys = [ft["key"] for ft in get_form_types()]
    if req.form_type not in valid_form_keys:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {req.form_type}")

    if req.form_type == "incident":
        return extract_incident(req.transcript, req.site)
    elif req.form_type == "safebase":
        return extract_safebase(req.transcript, req.site)


# ── Step 2: Volunteer reviews, edits, then submits ───────────────────


class SubmitRequest(BaseModel):
    form_type: str
    form_data: dict
    user_uid: str


@router.post("/api/submit")
async def submit_form(req: SubmitRequest):
    """
    Accepts the reviewed/edited form data and writes it to Firebase.
    Intentionally separate from /api/extract so the volunteer
    always has a chance to review before anything hits the database.
    """
    if not req.user_uid:
        raise HTTPException(status_code=400, detail="No user_uid provided")

    valid_form_keys = [ft["key"] for ft in get_form_types()]
    if req.form_type not in valid_form_keys:
        raise HTTPException(status_code=400, detail=f"Unknown form type: {req.form_type}")

    try:
        if req.form_type == "incident":
            validated = IncidentFormSchema(**req.form_data)
            key = push_incident_form(validated.model_dump(by_alias=True), req.user_uid)
        elif req.form_type == "safebase":
            validated = SafeBaseFormSchema(**req.form_data)
            key = push_safebase_form(validated.model_dump(), req.user_uid)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation failed: {str(e)}")

    return {"key": key}
