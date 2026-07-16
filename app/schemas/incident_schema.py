"""
Pydantic models matching the SKSSIR incidentForms/{id} schema.
Used as the structured output target for Claude extraction.
"""

from pydantic import AliasChoices, BaseModel, Field
from typing import Optional


class EncounteredBy(BaseModel):
    # Legacy RTDB may use tkAmbassador; accept on read and always serialise skAmbassador.
    skAmbassador: bool = Field(
        False,
        validation_alias=AliasChoices("skAmbassador", "tkAmbassador"),
        serialization_alias="skAmbassador",
    )
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
    # RTDB epoch ms. Set ONLY when the volunteer states a concrete time/duration;
    # otherwise left null (blank in the UI). The volunteer can also edit it manually.
    startTime: Optional[int] = Field(
        None,
        description=(
            "When the incident started, as epoch milliseconds. Only set this if the "
            "volunteer states a concrete time or moment (e.g. 'we found him around "
            "11:30 last night'); otherwise leave null."
        ),
    )
    endTime: Optional[int] = Field(
        None,
        description=(
            "When the incident ended, as epoch milliseconds. Only set this if the "
            "volunteer states an end time or a duration (e.g. 'we were with her for "
            "about 30 minutes'); otherwise leave null."
        ),
    )
    location: Location = Location()
    encounteredBy: EncounteredBy = EncounteredBy()
    otherServicesInvolved: OtherServicesInvolved = OtherServicesInvolved()
    quickNote: str = ""
    incidentDescription: str = ""
    incidentOutcome: str = ""
    majorIncident: bool = False
