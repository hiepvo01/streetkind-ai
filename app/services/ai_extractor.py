"""
AI-powered extraction service.
Takes a voice transcript and returns structured form data using Claude's
structured output via tool use (guaranteed valid JSON matching the schema).

All prompts and config are loaded from config/ files - not hardcoded here.
"""

import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from anthropic import AnthropicFoundry
from pydantic import ValidationError

from ..config import (
    get_app_config,
    get_incident_narrative_prompt,
    get_incident_prompt,
    get_safebase_prompt,
)
from ..schemas.combined_incident_schema import CombinedIncidentSchema
from ..schemas.incident_narrative_schema import IncidentNarrativeDraft
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


def _current_time_context() -> str:
    """
    Human-readable current time plus the epoch-ms anchor, so the model can
    resolve relative times ("last night", "about 30 minutes ago") into the
    epoch-millisecond timestamps startTime/endTime expect. Sydney tz because
    the volunteers are on the ground in Sydney.
    """
    now_ms = int(time.time() * 1000)
    sydney = datetime.now(ZoneInfo("Australia/Sydney"))
    human = sydney.strftime("%A, %d %B %Y, %I:%M %p")
    return (
        f"Current date and time (Australia/Sydney): {human}.\n"
        f"Current time as epoch milliseconds: {now_ms}.\n"
        "Use this as the anchor when converting any time the volunteer mentions "
        "into startTime/endTime (epoch milliseconds)."
    )


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
                    f"{_current_time_context()}\n\n"
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


def generate_incident_narrative(form_data: dict) -> dict:
    """
    From current structured incident + clients + quickNote, generate prose for
    incidentDescription and incidentOutcome only (no Firebase writes).
    """
    validated = CombinedIncidentSchema(**form_data)
    payload = validated.model_dump(mode="json", by_alias=True)
    user_text = json.dumps(payload, ensure_ascii=False, indent=2)

    client = _get_client()
    tool = _build_tool(
        name="write_incident_narrative",
        description=(
            "Return incidentDescription and incidentOutcome as professional prose. "
            "Base content only on the JSON incident data in the user message."
        ),
        schema_class=IncidentNarrativeDraft,
    )

    response = client.messages.create(
        model=_get_model(),
        max_tokens=_get_max_tokens(),
        system=get_incident_narrative_prompt(),
        tools=[tool],
        tool_choice={"type": "tool", "name": "write_incident_narrative"},
        messages=[{"role": "user", "content": user_text}],
    )

    raw_input = _extract_tool_input(response)
    try:
        draft = IncidentNarrativeDraft(**raw_input)
    except ValidationError as e:
        raise ValueError(f"Invalid narrative tool output: {e}") from e
    return draft.model_dump()
