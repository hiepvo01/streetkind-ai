"""
E2E tests for AI extraction (/api/extract).

These tests hit Foundry/Claude and cost real tokens, so they're skipped unless
RUN_AI_TESTS=1 is set in the environment. Run them before a release to verify
the extraction pipeline still produces structured output matching the schema.
"""

import os
import pytest
import requests
from .conftest import API_BASE_URL


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_AI_TESTS") != "1",
    reason="Set RUN_AI_TESTS=1 to run Foundry-backed extraction tests",
)


class TestAIExtraction:
    def test_incident_extraction_returns_valid_structure(self):
        transcript = (
            "At Town Hall tonight we helped a female aged about 22 who was alone "
            "and appeared very intoxicated - unsteady balance and slurred speech. "
            "She was referred to us by General Public. We gave her water and called "
            "her a taxi home. Low risk overall."
        )

        r = requests.post(
            f"{API_BASE_URL}/api/extract",
            json={"transcript": transcript, "form_type": "incident", "site": "townHall"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()

        # Top-level structure
        assert "incident" in data and "clients" in data
        inc = data["incident"]
        assert inc.get("site") == "townHall"
        # General Public flag should be set
        assert inc.get("encounteredBy", {}).get("generalPublic") is True
        # Description should be populated (AI generated)
        assert (inc.get("incidentDescription") or "").strip()

        # One client extracted
        clients = data["clients"]
        assert len(clients) == 1
        c = clients[0]
        assert c.get("gender") == "female"
        assert c.get("ageGroup") == "18to25"
        assert c.get("alone") is True
        # Intoxication signs from "balance" + "slurred speech"
        assert c.get("intoxicationSigns", {}).get("balance") is True
        assert c.get("intoxicationSigns", {}).get("speech") is True
        # Basic aid: water
        assert c.get("basicAid", {}).get("water") is True
        # Transport: taxi
        assert c.get("transportInformation", {}).get("taxi") is True

    def test_safebase_extraction(self):
        transcript = (
            "At Darling Harbour we had 3 male clients aged 18 to 25, 2 females under 18, "
            "and 1 non-binary client aged 26 to 39. We gave 4 sets of directions and "
            "charged 2 phones."
        )
        r = requests.post(
            f"{API_BASE_URL}/api/extract",
            json={"transcript": transcript, "form_type": "safebase", "site": "darlingHarbour"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("site") == "darlingHarbour"
        # People counts should be non-zero matching the transcript numbers
        people = data.get("people", {})
        # Structure allows either nested {male:{18to25: 3}} or flat - accept either
        assert people, "SafeBase extraction returned empty people counts"

    def test_extract_empty_transcript_rejected(self):
        r = requests.post(
            f"{API_BASE_URL}/api/extract",
            json={"transcript": "   ", "form_type": "incident"},
            timeout=20,
        )
        assert r.status_code == 400

    def test_extract_unknown_form_type_rejected(self):
        r = requests.post(
            f"{API_BASE_URL}/api/extract",
            json={"transcript": "hello", "form_type": "nonsense"},
            timeout=20,
        )
        assert r.status_code == 400
