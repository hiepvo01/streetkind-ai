"""
Tests for AI extraction service.
Run with: pytest tests/test_extraction.py -v
Requires ANTHROPIC_API_KEY in environment.
"""

import os
import pytest

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


from app.services.ai_extractor import extract_incident, extract_safebase


class TestIncidentExtraction:
    def test_basic_incident(self):
        transcript = (
            "We found a young man near the Town Hall steps, he was stumbling "
            "and slurring his words. A member of the public flagged us down. "
            "We gave him some water and helped him call a taxi. He left safely."
        )
        result = extract_incident(transcript, site="townHall")

        assert result["site"] == "townHall"
        assert result["encounteredBy"]["generalPublic"] is True
        assert result["incidentDescription"] != ""
        assert result["incidentOutcome"] != ""
        # Intoxication signs should be mentioned in description context
        assert result["majorIncident"] is False

    def test_police_involvement(self):
        transcript = (
            "Police called us over to help with a woman at Darling Harbour "
            "who was upset and crying. We provided mental health first aid "
            "and connected her with Beyond Blue. Ambulance was also on scene."
        )
        result = extract_incident(transcript, site="darlingHarbour")

        assert result["site"] == "darlingHarbour"
        assert result["encounteredBy"]["police"] is True
        assert result["otherServicesInvolved"]["ambulance"] is True

    def test_empty_transcript_returns_defaults(self):
        result = extract_incident("Nothing happened tonight.", site="townHall")
        assert result["majorIncident"] is False


class TestSafeBaseExtraction:
    def test_basic_headcount(self):
        transcript = (
            "Tonight at Kings Cross we had 5 young men come in, looked about "
            "18 to 25. Also 3 women in their 30s. We gave directions to 4 "
            "people and helped 2 charge their phones."
        )
        result = extract_safebase(transcript, site="kingsCross")

        assert result["site"] == "kingsCross"
        assert result["male"]["from18to25"] == 5
        assert result["female"]["from26to39"] == 3
        assert result["assistanceRendered"]["directions"] == 4
        assert result["assistanceRendered"]["deviceCharge"] == 2

    def test_mixed_ages(self):
        transcript = (
            "We had 2 teenage boys, about 16, and an older gentleman around 50 "
            "at Town Hall safe base. Gave the older man train info."
        )
        result = extract_safebase(transcript, site="townHall")

        assert result["male"]["lessThan18"] == 2
        assert result["male"]["over40"] == 1
        assert result["assistanceRendered"]["train"] == 1
