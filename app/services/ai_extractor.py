"""
AI-powered extraction service.
Takes a voice transcript and returns structured form data using Claude's
structured output via tool use (guaranteed valid JSON matching the schema).

All prompts and config are loaded from config/ files - not hardcoded here.
"""

import os
import anthropic
from ..config import get_app_config, get_incident_prompt, get_safebase_prompt
from ..schemas.incident_schema import IncidentFormSchema
from ..schemas.safebase_schema import SafeBaseFormSchema


def _get_client():
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _get_model() -> str:
    app = get_app_config()
    return os.getenv("AI_MODEL", app["ai"]["default_model"])


def _get_max_tokens() -> int:
    app = get_app_config()
    return app["ai"]["max_tokens"]


def _build_tool(name: str, description: str, schema_class) -> dict:
    """Build a Claude tool definition from a Pydantic model."""
    return {
        "name": name,
        "description": description,
        "input_schema": schema_class.model_json_schema(),
    }


def _extract_tool_input(response) -> dict:
    """Extract the tool input from a Claude response that used tool_use."""
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Claude did not return a tool_use block.")


def extract_incident(transcript: str, site: str = "") -> dict:
    """Extract incident form fields from a voice transcript using structured output."""
    client = _get_client()

    tool = _build_tool(
        name="fill_incident_form",
        description="Fill in the incident report form with structured data extracted from the volunteer's spoken description.",
        schema_class=IncidentFormSchema,
    )

    response = client.messages.create(
        model=_get_model(),
        max_tokens=_get_max_tokens(),
        system=get_incident_prompt(),
        tools=[tool],
        tool_choice={"type": "tool", "name": "fill_incident_form"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Volunteer's site: {site}\n\n"
                    f"Volunteer's spoken description:\n\"{transcript}\""
                ),
            }
        ],
    )

    raw_input = _extract_tool_input(response)
    validated = IncidentFormSchema(**raw_input)
    return validated.model_dump(by_alias=True)


def extract_safebase(transcript: str, site: str = "") -> dict:
    """Extract SafeBase form fields from a voice transcript using structured output."""
    client = _get_client()

    tool = _build_tool(
        name="fill_safebase_form",
        description="Fill in the SafeBase form with headcount and assistance data extracted from the volunteer's spoken description.",
        schema_class=SafeBaseFormSchema,
    )

    response = client.messages.create(
        model=_get_model(),
        max_tokens=_get_max_tokens(),
        system=get_safebase_prompt(),
        tools=[tool],
        tool_choice={"type": "tool", "name": "fill_safebase_form"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Volunteer's site: {site}\n\n"
                    f"Volunteer's spoken description:\n\"{transcript}\""
                ),
            }
        ],
    )

    raw_input = _extract_tool_input(response)
    validated = SafeBaseFormSchema(**raw_input)
    return validated.model_dump()
