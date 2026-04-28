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


class TestRealisticTranscripts:
    """
    Stress the prompt with natural Aussie volunteer phrasing and assert the
    AI populates the right structured booleans. These would have caught the
    'drunk → no intoxication signs' bug in our first prompt version.
    """

    def _extract(self, transcript: str, form_type: str = "incident", site: str = "townHall") -> dict:
        r = requests.post(
            f"{API_BASE_URL}/api/extract",
            json={"transcript": transcript, "form_type": form_type, "site": site},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_drunk_alone_implies_intoxication_behaviour(self):
        d = self._extract(
            "Helped a 22 year old woman who was drunk alone near Town Hall. Gave her water and called her an Uber home."
        )
        c = d["clients"][0]
        assert c["gender"] == "female"
        assert c["ageGroup"] == "18to25"
        assert c["alone"] is True
        # "drunk" must produce at least one intoxication sub-flag (behaviour at minimum)
        intox = c["intoxicationSigns"]
        assert any(intox.get(k) for k in ("speech", "balance", "coordination", "behaviour")), (
            f"'drunk' should set at least one intoxication sub-flag, got {intox}"
        )
        assert c["transportInformation"]["uber"] is True
        assert c["basicAid"]["water"] is True

    def test_specific_symptoms_set_specific_subfields(self):
        d = self._extract(
            "Found a young guy slurring his words and stumbling, couldn't stand up properly. Sat with him until ambulance arrived."
        )
        c = d["clients"][0]
        intox = c["intoxicationSigns"]
        # "slurring" -> speech, "stumbling/couldn't stand" -> balance/coordination
        assert intox["speech"] is True, f"'slurring' should set speech, got {intox}"
        assert intox["balance"] is True or intox["coordination"] is True, (
            f"'stumbling' should set balance or coordination, got {intox}"
        )
        # "ambulance arrived" -> emergency services
        es = c["emergencyServicesCalled"]
        assert es.get("ambulanceServiceCalled") is True

    def test_no_intoxication_mention_sets_notVisible(self):
        d = self._extract(
            "Helped someone find their way to Central station after they got lost. Just needed directions."
        )
        c = d["clients"][0]
        # No drug/alcohol mentioned -> notVisible should be true on both
        assert c["intoxicationSigns"]["notVisible"] is True
        assert c["drugUseSigns"]["notVisible"] is True
        # "lost ... needed directions" -> directions support
        directions = c["directions"]
        assert any(directions.get(k) for k in ("venue", "accommodation", "other"))

    def test_drugs_disclosure_sets_drug_signs_disclosed(self):
        d = self._extract(
            "Spoke with a 30yo woman who told me she had taken some pills earlier and wasn't feeling right. Got her to hospital."
        )
        c = d["clients"][0]
        # Disclosed drug use
        drug = c["drugUseSigns"]
        assert drug["disclosed"] is True, f"disclosed drug use missing: {drug}"
        # Hospital service referral
        refs = c["clientServiceReferrals"]
        assert refs["hospital"] is True

    def test_water_and_vomit_bag_basicaid(self):
        d = self._extract(
            "Bloke threw up on the ground, gave him a vomit bag and a bottle of water."
        )
        c = d["clients"][0]
        assert c["basicAid"]["water"] is True
        assert c["basicAid"]["vomitBag"] is True

    def test_volunteer_narrating_does_not_set_self(self):
        """'self' encounteredBy means client referred themselves. The volunteer
        narrating should not flip self=true just by being the speaker."""
        d = self._extract(
            "I noticed a man sitting alone on the bench looking unwell. Walked over and asked if he needed help."
        )
        # Either generalPublic, skAmbassador, or empty; self should NOT be true.
        encountered = d["incident"]["encounteredBy"]
        assert encountered.get("self") is not True, (
            f"encounteredBy.self should not be true for volunteer-found cases: {encountered}"
        )
