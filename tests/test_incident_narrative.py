"""Unit tests for Magic incident narrative (mocked LLM)."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.services.ai_extractor import generate_incident_narrative


def _minimal_valid_form_data():
    return {
        "incident": {
            "teamLeaderName": "TL",
            "site": "townHall",
            "location": {"address": "Town Hall steps"},
            "encounteredBy": {
                "generalPublic": True,
                    "skAmbassador": False,
                "cctv": False,
                "self": False,
                "friend": False,
                "venueSecurity": False,
                "transportStaff": False,
                "police": False,
                "fireRescue": False,
                "rangers": False,
                "ambulance": False,
                "other": "",
            },
            "otherServicesInvolved": {
                "police": False,
                "ambulance": False,
                "fireRescue": False,
                "cctv": False,
                "rangers": False,
                "venueSecurity": False,
                "others": "",
            },
            "quickNote": "Member of public flagged us down.",
            "incidentDescription": "",
            "incidentOutcome": "",
            "majorIncident": False,
        },
        "clients": [],
    }


def test_generate_incident_narrative_returns_drafts():
    block = MagicMock()
    block.type = "tool_use"
    block.input = {
        "incidentDescription": "A member of the public reported an incident.",
        "incidentOutcome": "Volunteers attended and documented the matter.",
    }
    response = MagicMock()
    response.content = [block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = response

    with patch("app.services.ai_extractor._get_client", return_value=mock_client):
        out = generate_incident_narrative(_minimal_valid_form_data())

    assert out["incidentDescription"] == block.input["incidentDescription"]
    assert out["incidentOutcome"] == block.input["incidentOutcome"]
    mock_client.messages.create.assert_called_once()


def test_generate_incident_narrative_invalid_form_raises():
    mock_client = MagicMock()
    with patch("app.services.ai_extractor._get_client", return_value=mock_client):
        with pytest.raises(ValidationError):
            generate_incident_narrative({"incident": "not-an-object", "clients": []})
    mock_client.messages.create.assert_not_called()
