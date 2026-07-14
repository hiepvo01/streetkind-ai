"""
Unit tests for the server-side completeness checker used to enforce required
fields on a COMPLETED incident submission (drafts bypass this).
"""

from app.schemas.combined_incident_schema import CombinedIncidentSchema
from app.services.incident_completeness import check_incident_complete, SIGN_GROUPS


def _valid_client() -> dict:
    """A fully-answered client: demographics set, every sign group resolved."""
    client = {"gender": "male", "ageGroup": "18to25", "alone": False}
    # Resolve each of the 8 sign groups with notVisible (a valid single choice).
    for attr, _others in SIGN_GROUPS:
        client[attr] = {"notVisible": True}
    return client


def _valid_incident() -> dict:
    return {
        "teamLeaderName": "Sam",
        "site": "townHall",
        "startTime": 1000,
        "endTime": 2000,
        "incidentDescription": "Found an intoxicated man.",
        "incidentOutcome": "Escorted to safe space.",
    }


def _combined(incident: dict, clients: list) -> CombinedIncidentSchema:
    return CombinedIncidentSchema(incident=incident, clients=clients)


def test_empty_incident_reports_all_required():
    errors = check_incident_complete(CombinedIncidentSchema())
    # 6 incident-level required fields; no clients present -> no client errors.
    assert len(errors) == 6
    joined = " ".join(errors)
    for field in [
        "teamLeaderName", "site", "startTime", "endTime",
        "incidentDescription", "incidentOutcome",
    ]:
        assert field in joined


def test_fully_complete_incident_passes():
    combined = _combined(_valid_incident(), [_valid_client()])
    assert check_incident_complete(combined) == []


def test_end_before_start_flagged():
    incident = _valid_incident()
    incident["startTime"] = 5000
    incident["endTime"] = 4000
    errors = check_incident_complete(_combined(incident, [_valid_client()]))
    assert any("End time must be after start time" in e for e in errors)


def test_alone_unanswered_flagged():
    client = _valid_client()
    client["alone"] = None
    errors = check_incident_complete(_combined(_valid_incident(), [client]))
    assert any("alone: Required" in e for e in errors)


def test_gender_and_agegroup_required():
    client = _valid_client()
    client["gender"] = ""
    client["ageGroup"] = ""
    errors = check_incident_complete(_combined(_valid_incident(), [client]))
    assert any("gender: Required" in e for e in errors)
    assert any("ageGroup: Required" in e for e in errors)


def test_sign_group_blank_is_required():
    client = _valid_client()
    client["drugUseSigns"] = {}  # nothing ticked
    errors = check_incident_complete(_combined(_valid_incident(), [client]))
    assert any("drugUseSigns: Required" in e for e in errors)


def test_sign_group_conflict_flagged():
    client = _valid_client()
    client["intoxicationSigns"] = {"notVisible": True, "behaviour": True}
    errors = check_incident_complete(_combined(_valid_incident(), [client]))
    assert any(
        "intoxicationSigns: Tick either 'Not Visible' or the others." in e
        for e in errors
    )


def test_valid_single_positive_choice_passes():
    client = _valid_client()
    client["intoxicationSigns"] = {"behaviour": True}  # positive, no notVisible
    errors = check_incident_complete(_combined(_valid_incident(), [client]))
    assert errors == []
