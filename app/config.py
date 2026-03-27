"""
Centralised config loader.
Reads all configuration from the config/ folder so non-technical users
can edit JSON files and prompt text without touching Python code.

Config structure:
    config/
        app.json              - App name, defaults, AI settings
        sites.json            - Operating sites
        form_types.json       - Form type definitions
        prompts/
            incident.txt      - AI prompt template for incidents
            safebase.txt      - AI prompt template for SafeBase
        fields/
            shared.json       - Options shared across forms (gender, age)
            incident.json     - Incident-specific field options
            safebase.json     - SafeBase-specific field options
            client.json       - Client-specific field options (Phase 2)
"""

import json
from pathlib import Path
from functools import lru_cache

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
FIELDS_DIR = CONFIG_DIR / "fields"


@lru_cache()
def _load_json(path: str) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json(filename: str) -> dict | list:
    return _load_json(str(CONFIG_DIR / filename))


def load_prompt(filename: str, **kwargs) -> str:
    """Load a prompt template and fill in placeholders from config."""
    path = CONFIG_DIR / "prompts" / filename
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    return template.format(**kwargs)


# ── App config ───────────────────────────────────────────────────────

def get_app_config() -> dict:
    return load_json("app.json")


def get_sites() -> list[dict]:
    return load_json("sites.json")


def get_site_keys() -> list[str]:
    return [s["key"] for s in get_sites()]


def get_form_types() -> list[dict]:
    return load_json("form_types.json")


def get_form_type_config(form_type_key: str) -> dict | None:
    for ft in get_form_types():
        if ft["key"] == form_type_key:
            return ft
    return None


# ── Field options (per-form) ─────────────────────────────────────────

def get_shared_fields() -> dict:
    return _load_json(str(FIELDS_DIR / "shared.json"))


def get_form_fields(form_type_key: str) -> dict:
    """
    Return merged field options for a form: shared options + form-specific options.
    """
    shared = dict(get_shared_fields())
    # Remove _comment keys
    shared.pop("_comment", None)

    form_path = FIELDS_DIR / f"{form_type_key}.json"
    if form_path.exists():
        form_specific = dict(_load_json(str(form_path)))
        form_specific.pop("_comment", None)
        shared.update(form_specific)

    return shared


def get_all_form_fields() -> dict:
    """
    Return field options grouped by form type.
    Used by GET /api/config so the frontend knows all options.
    """
    result = {}
    for ft in get_form_types():
        result[ft["key"]] = get_form_fields(ft["key"])
    # Also include client fields for future use
    client_path = FIELDS_DIR / "client.json"
    if client_path.exists():
        client_fields = dict(_load_json(str(client_path)))
        client_fields.pop("_comment", None)
        shared = dict(get_shared_fields())
        shared.pop("_comment", None)
        shared.update(client_fields)
        result["client"] = shared
    return result


def _option_keys(form_type: str, field_name: str) -> str:
    """Return comma-separated keys for a field option group within a form."""
    fields = get_form_fields(form_type)
    options = fields.get(field_name, [])
    return ", ".join(o["key"] for o in options)


# ── Prompt builders ──────────────────────────────────────────────────

def get_incident_prompt() -> str:
    app = get_app_config()
    return load_prompt(
        "incident.txt",
        organisation_name=app["organisation_name"],
        site_keys=", ".join(get_site_keys()),
        encountered_by_keys=_option_keys("incident", "encountered_by"),
        other_services_keys=_option_keys("incident", "other_services"),
    )


def get_safebase_prompt() -> str:
    app = get_app_config()
    return load_prompt(
        "safebase.txt",
        organisation_name=app["organisation_name"],
        site_keys=", ".join(get_site_keys()),
        gender_keys=_option_keys("safebase", "gender"),
        age_group_keys=_option_keys("safebase", "age_group"),
        assistance_keys=_option_keys("safebase", "assistance_rendered"),
    )
