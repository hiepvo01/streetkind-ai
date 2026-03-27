"""
Pydantic models matching the SKSSIR clients/{id} schema.
This is the most complex form - 50+ fields across 5 sections.
Reserved for Phase 2 implementation with Claude Sonnet.
"""

from pydantic import BaseModel
from typing import Optional


# --- Section 1: Client Info & Risk Assessment ---

class IntoxicationSigns(BaseModel):
    speech: bool = False
    balance: bool = False
    coordination: bool = False
    behaviour: bool = False
    notVisible: bool = False


class ObservedVisibleDisclosed(BaseModel):
    observed: bool = False
    visibleSigns: bool = False
    disclosed: bool = False
    notVisible: bool = False


class SuicidalSigns(BaseModel):
    ideationObserved: bool = False
    ideationDisclosed: bool = False
    attemptObserved: bool = False
    attemptDisclosed: bool = False
    notVisible: bool = False


class OffensiveConduct(BaseModel):
    offensiveBehaviour: bool = False
    offensiveLanguage: bool = False
    obstruction: bool = False
    publicDrinking: bool = False
    notVisible: bool = False


class SelfHarmSigns(BaseModel):
    visibleSigns: bool = False
    disclosed: bool = False
    notVisible: bool = False


# --- Section 2: Basic Support ---

class Reconnection(BaseModel):
    telephone: bool = False
    person: bool = False
    socialNetwork: bool = False


class Directions(BaseModel):
    venue: bool = False
    accommodation: bool = False
    other: bool = False


class TransportInformation(BaseModel):
    bus: bool = False
    train: bool = False
    taxi: bool = False
    uber: bool = False
    other: bool = False


class EscortedTo(BaseModel):
    accommodation: bool = False
    transport: bool = False
    friends: bool = False
    other: bool = False


class SafeSpace(BaseModel):
    escortedTo: bool = False
    soberedUp: bool = False


# --- Section 3: Health Support ---

class BasicAid(BaseModel):
    vomitBag: bool = False
    water: bool = False
    footwear: bool = False
    lollipop: bool = False


class AdditionalAid(BaseModel):
    firstAid: bool = False
    mentalHealthAid: bool = False


class EmergencyServicesCalled(BaseModel):
    ambulanceServiceCalled: bool = False
    policeServiceCalled: bool = False
    fireServiceCalled: bool = False


# --- Section 4: Risk Minimization ---

class Injury(BaseModel):
    roadRelated: bool = False
    other: bool = False


# --- Section 5: Services Referred ---

class ClientServiceReferrals(BaseModel):
    alcoholDrugInfoService: bool = False
    beyondBlue: bool = False
    childProtectionServices: bool = False
    dvLine: bool = False
    hospital: bool = False
    lifeline: bool = False
    link2home: bool = False
    salvosStreetLevel: bool = False
    streetbeatBus: bool = False
    traffickingSlaveryAFP: bool = False


class ServiceInformation(BaseModel):
    contactedService: bool = False
    infoProvided: bool = False


class OtherSupport(BaseModel):
    welfareCheck: bool = False
    homelessSupport: bool = False


# --- Full Client Schema ---

class ClientFormSchema(BaseModel):
    """Matches the SKSSIR clients node structure. 50+ fields across 5 sections."""

    # Section 1: Client Info
    firstName: str = ""
    lastName: str = ""
    gender: str = ""  # male, female, nonBinary
    ageGroup: str = ""  # lessThan18, 18to25, 26to39, over40
    email: str = ""
    contactNumber: str = ""
    suburb: str = ""
    alone: bool = False

    # Section 1: Risk Assessment
    intoxicationSigns: IntoxicationSigns = IntoxicationSigns()
    drugUseSigns: ObservedVisibleDisclosed = ObservedVisibleDisclosed()
    offensiveConduct: OffensiveConduct = OffensiveConduct()
    selfHarmSigns: SelfHarmSigns = SelfHarmSigns()
    suicidalSigns: SuicidalSigns = SuicidalSigns()
    sexualAssault: ObservedVisibleDisclosed = ObservedVisibleDisclosed()
    physicalAssault: ObservedVisibleDisclosed = ObservedVisibleDisclosed()
    domesticViolence: ObservedVisibleDisclosed = ObservedVisibleDisclosed()

    # Section 2: Basic Support
    reconnection: Reconnection = Reconnection()
    directions: Directions = Directions()
    transportInformation: TransportInformation = TransportInformation()
    escortedTo: EscortedTo = EscortedTo()
    safeSpace: SafeSpace = SafeSpace()

    # Section 3: Health Support
    basicAid: BasicAid = BasicAid()
    additionalAid: AdditionalAid = AdditionalAid()
    emergencyServicesCalled: EmergencyServicesCalled = EmergencyServicesCalled()

    # Section 4: Risk Minimization
    physicalAssaultRisk: int = 0
    sexualAssaultRisk: int = 0
    clientConsciousness: int = 0  # 0=conscious, 1=unconscious, 2=asleep, 3=passed out
    clientValuablesVisibility: int = 0  # 0=visible, 1=not visible
    clientLostProperty: int = 0  # 0=no lost property, 1=lost and found, 2=lost
    injury: Injury = Injury()

    # Section 5: Services Referred
    clientServiceReferrals: ClientServiceReferrals = ClientServiceReferrals()
    serviceInformation: ServiceInformation = ServiceInformation()
    otherSupport: OtherSupport = OtherSupport()
