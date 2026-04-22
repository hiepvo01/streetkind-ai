"""
AI-powered extraction service.
Takes a voice transcript and returns structured form data using Claude's
structured output via tool use (guaranteed valid JSON matching the schema).

All prompts and config are loaded from config/ files - not hardcoded here.
"""

import os

from anthropic import AnthropicFoundry

from ..config import get_app_config, get_incident_prompt, get_safebase_prompt
from ..schemas.combined_incident_schema import CombinedIncidentSchema
from ..schemas.safebase_schema import SafeBaseFormSchema

# Singleton client - reuses HTTP connection pool across requests
_client = None


def _get_client():
    """Microsoft Foundry-hosted Claude via Anthropic-compatible Messages API."""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
        base_url = os.getenv("ANTHROPIC_FOUNDRY_BASE_URL")
        resource = os.getenv("ANTHROPIC_FOUNDRY_RESOURCE")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_FOUNDRY_API_KEY is not set. "
                "If you have ANTHROPIC_API_KEY in your .env, rename it - "
                "this project now uses Microsoft Foundry (see .env.example)."
            )
        if not (base_url or resource):
            raise RuntimeError(
                "Set ANTHROPIC_FOUNDRY_BASE_URL or ANTHROPIC_FOUNDRY_RESOURCE in your .env."
            )
        if base_url:
            _client = AnthropicFoundry(api_key=api_key, base_url=base_url)
        else:
            _client = AnthropicFoundry(api_key=api_key, resource=resource)
    return _client


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
        name="fill_incident_report",
        description="Fill in the incident report including details about each client/person helped",
        schema_class=CombinedIncidentSchema,
    )

    response = client.messages.create(
        model=_get_model(),
        max_tokens=_get_max_tokens(),
        system=get_incident_prompt(),
        tools=[tool],
        tool_choice={"type": "tool", "name": "fill_incident_report"},
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
    validated = CombinedIncidentSchema(**raw_input)
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
    return validated.model_dump(by_alias=True)
