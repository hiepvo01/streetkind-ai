"""Structured output for Magic narrative: description + outcome only."""

from pydantic import BaseModel


class IncidentNarrativeDraft(BaseModel):
    incidentDescription: str = ""
    incidentOutcome: str = ""
