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

import copy
import json
from pathlib import Path
from functools import lru_cache

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
FIELDS_DIR = CONFIG_DIR / "fields"


@lru_cache()
def _load_json(path: str) -> dict | list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {path}: {e}")


def load_json(filename: str) -> dict | list:
    return copy.deepcopy(_load_json(str(CONFIG_DIR / filename)))


def load_prompt(filename: str, **kwargs) -> str:
    """Load a prompt template and fill in placeholders from config."""
    path = CONFIG_DIR / "prompts" / filename
    try:
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        raise RuntimeError(f"Prompt file not found: {path}")
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
    data = copy.deepcopy(_load_json(str(FIELDS_DIR / "shared.json")))
    data.pop("_comment", None)
    return data


def get_form_fields(form_type_key: str) -> dict:
    """
    Return merged field options for a form: shared options + form-specific options.
    """
    merged = get_shared_fields()

    form_path = FIELDS_DIR / f"{form_type_key}.json"
    if form_path.exists():
        form_specific = copy.deepcopy(_load_json(str(form_path)))
        form_specific.pop("_comment", None)
        merged.update(form_specific)

    return merged


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
        result["client"] = get_form_fields("client")
    return result


def _option_keys(form_type: str, field_name: str) -> str:
    """Return comma-separated keys for a field option group within a form."""
    fields = get_form_fields(form_type)
    options = fields.get(field_name, [])
    return ", ".join(o["key"] for o in options)


# ── Prompt builders ──────────────────────────────────────────────────

def _client_risk_indicator_doc() -> str:
    """Derive the client-record risk-indicator field structure from the live
    Pydantic schema so the prompt stays in sync if the schema evolves.

    Returns a short newline-separated block like:
        client.sexualAssault: observed, visibleSigns, disclosed, notVisible
        client.physicalAssault: observed, visibleSigns, disclosed, notVisible
        ...
    """
    from .schemas.combined_incident_schema import CombinedIncidentSchema

    schema = CombinedIncidentSchema.model_json_schema()
    defs = schema.get("$defs") or schema.get("definitions") or {}
    client_props = defs.get("ClientFormSchema", {}).get("properties", {})

    # Field names (under client) whose nested object carries the risk Booleans
    # we want the model to toggle. Order matches the form layout.
    indicator_fields = [
        "intoxicationSigns",
        "drugUseSigns",
        "offensiveConduct",
        "selfHarmSigns",
        "suicidalSigns",
        "sexualAssault",
        "physicalAssault",
        "domesticViolence",
    ]

    lines: list[str] = []
    for fname in indicator_fields:
        prop = client_props.get(fname, {})
        ref = prop.get("$ref") or next(
            (x.get("$ref") for x in prop.get("anyOf", []) if "$ref" in x),
            None,
        )
        if not ref:
            continue
        target = ref.split("/")[-1]
        sub_props = defs.get(target, {}).get("properties", {})
        if not sub_props:
            continue
        lines.append(f"client.{fname}: {', '.join(sub_props.keys())}")
    return "\n".join(lines)


def get_incident_prompt() -> str:
    app = get_app_config()
    return load_prompt(
        "incident.txt",
        organisation_name=app["organisation_name"],
        site_keys=", ".join(get_site_keys()),
        encountered_by_keys=_option_keys("incident", "encountered_by"),
        other_services_keys=_option_keys("incident", "other_services"),
        client_risk_indicator_fields=_client_risk_indicator_doc(),
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


def get_incident_narrative_prompt() -> str:
    app = get_app_config()
    return load_prompt(
        "incident_narrative.txt",
        organisation_name=app["organisation_name"],
    )
