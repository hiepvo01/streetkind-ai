"""
Pydantic models matching the SKSSIR incidentForms/{id} schema.
Used as the structured output target for Claude extraction.
"""

from pydantic import BaseModel, Field
from typing import Optional


class EncounteredBy(BaseModel):
    tkAmbassador: bool = False
    cctv: bool = False
    self_referred: bool = Field(False, alias="self")
    friend: bool = False
    generalPublic: bool = False
    venueSecurity: bool = False
    transportStaff: bool = False
    police: bool = False
    fireRescue: bool = False
    rangers: bool = False
    ambulance: bool = False
    other: str = ""

    model_config = {"populate_by_name": True}


class OtherServicesInvolved(BaseModel):
    police: bool = False
    ambulance: bool = False
    fireRescue: bool = False
    cctv: bool = False
    rangers: bool = False
    venueSecurity: bool = False
    others: str = ""


class Location(BaseModel):
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class IncidentFormSchema(BaseModel):
    """Matches the SKSSIR incidentForms node structure."""

    teamLeaderName: str = ""
    site: str = ""
    location: Location = Location()
    encounteredBy: EncounteredBy = EncounteredBy()
    otherServicesInvolved: OtherServicesInvolved = OtherServicesInvolved()
    incidentDescription: str = ""
    incidentOutcome: str = ""
    majorIncident: bool = False
