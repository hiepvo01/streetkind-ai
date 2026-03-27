"""
Pydantic models matching the SKSSIR safeSpaceForms/{id} schema.
Used as the structured output target for Claude extraction.
"""

from pydantic import BaseModel


class GenderAgeCount(BaseModel):
    lessThan18: int = 0
    from18to25: int = 0
    from26to39: int = 0
    over40: int = 0


class AssistanceRendered(BaseModel):
    directions: int = 0
    bus: int = 0
    train: int = 0
    taxi: int = 0
    deviceCharge: int = 0
    familyReconnect: int = 0


class SafeBaseFormSchema(BaseModel):
    """Matches the SKSSIR safeSpaceForms node structure."""

    site: str = ""
    male: GenderAgeCount = GenderAgeCount()
    female: GenderAgeCount = GenderAgeCount()
    nonBinary: GenderAgeCount = GenderAgeCount()
    assistanceRendered: AssistanceRendered = AssistanceRendered()
