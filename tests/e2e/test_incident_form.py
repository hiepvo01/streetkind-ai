"""
E2E tests for incident form submission.

Uses the backend API directly (no Claude extraction) to avoid API costs,
then verifies the data landed correctly in Firebase.
"""

import requests
from playwright.sync_api import Page, expect
from .conftest import do_login, BASE_URL, DEMO_VOLUNTEER, API_BASE_URL, get_firebase_id_token_for_uid

SAMPLE_INCIDENT_DATA = {
    "incident": {
        "teamLeaderName": "E2E Test Leader",
        "site": "townHall",
        "location": {"address": "E2E Test Location", "latitude": None, "longitude": None},
        "encounteredBy": {
            "generalPublic": True, "skAmbassador": False, "cctv": False,
            "self": False, "friend": False, "venueSecurity": False,
            "transportStaff": False, "police": False, "fireRescue": False,
            "rangers": False, "ambulance": False, "other": "",
        },
        "otherServicesInvolved": {
            "police": True, "ambulance": False, "fireRescue": False,
            "cctv": False, "rangers": False, "venueSecurity": False, "others": "",
        },
        "incidentDescription": "E2E test incident - should be deleted after test",
        "incidentOutcome": "E2E test outcome",
        "majorIncident": False,
    },
    "clients": [{
        "gender": "male",
        "ageGroup": "18to25",
        "alone": True,
        "firstName": "E2ETest",
        "lastName": "",
        "suburb": "",
        "email": "",
        "contactNumber": "",
        "intoxicationSigns": {
            "speech": True, "balance": True, "coordination": False,
            "behaviour": False, "notVisible": False,
        },
        "drugUseSigns": {
            "observed": False, "visibleSigns": False,
            "disclosed": False, "notVisible": True,
        },
        "offensiveConduct": {
            "offensiveBehaviour": False, "offensiveLanguage": False,
            "obstruction": False, "publicDrinking": False, "notVisible": True,
        },
        "selfHarmSigns": {
            "visibleSigns": False, "disclosed": False, "notVisible": True,
        },
        "suicidalSigns": {
            "ideationObserved": False, "ideationDisclosed": False,
            "attemptObserved": False, "attemptDisclosed": False, "notVisible": True,
        },
        "sexualAssault": {
            "observed": False, "visibleSigns": False,
            "disclosed": False, "notVisible": True,
        },
        "physicalAssault": {
            "observed": False, "visibleSigns": False,
            "disclosed": False, "notVisible": True,
        },
        "domesticViolence": {
            "observed": False, "visibleSigns": False,
            "disclosed": False, "notVisible": True,
        },
        "reconnection": {"telephone": False, "person": False, "socialNetwork": False},
        "directions": {"venue": False, "accommodation": False, "other": False},
        "transportInformation": {
            "bus": False, "train": False, "taxi": True, "uber": False, "other": False,
        },
        "escortedTo": {
            "accommodation": False, "transport": False,
            "friends": False, "other": False,
        },
        "safeSpace": {"escortedTo": False, "soberedUp": False},
        "basicAid": {
            "vomitBag": False, "water": True, "footwear": False, "lollipop": False,
        },
        "additionalAid": {"firstAid": False, "mentalHealthAid": False},
        "emergencyServicesCalled": {
            "ambulanceServiceCalled": False,
            "policeServiceCalled": False,
            "fireServiceCalled": False,
        },
        "physicalAssaultRisk": 0,
        "sexualAssaultRisk": 0,
        "clientConsciousness": 0,
        "clientValuablesVisibility": 0,
        "clientLostProperty": 0,
        "injury": {"roadRelated": False, "other": False},
        "clientServiceReferrals": {
            "alcoholDrugInfoService": False, "beyondBlue": False,
            "childProtectionServices": False, "dvLine": False,
            "hospital": False, "lifeline": False, "link2home": False,
            "salvosStreetLevel": False, "streetbeatBus": False,
            "traffickingSlaveryAFP": False,
        },
        "serviceInformation": {"contactedService": False, "infoProvided": False},
        "otherSupport": {"welfareCheck": False, "homelessSupport": False},
    }],
}


class TestIncidentSubmission:
    def test_submit_incident_writes_to_firebase(self, fb_db, cleanup_keys):
        """Submit an incident via the API, verify it in Firebase, then clean up."""
        id_token = get_firebase_id_token_for_uid("e2e-test-user")
        resp = requests.post(
            f"{API_BASE_URL}/api/submit",
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            json={
                "form_type": "incident",
                "form_data": SAMPLE_INCIDENT_DATA,
            },
        )
        assert resp.status_code == 200, f"Submit failed: {resp.text}"
        key = resp.json()["key"]

        # Verify incident was created
        incident = fb_db.reference(f"incidentForms/{key}").get()
        assert incident is not None, "Incident not found in Firebase"
        assert incident["incidentDescription"] == "E2E test incident - should be deleted after test"
        assert incident["status"] == "completed"
        assert incident.get("createdBy") == "e2e-test-user"
        cleanup_keys.append(("incidentForms", key))

        # Verify the client was created and linked
        client_list = incident.get("clientList", [])
        assert len(client_list) == 1, f"Expected 1 client, got {len(client_list)}"
        client = fb_db.reference(f"clients/{client_list[0]}").get()
        assert client is not None, "Client not found in Firebase"
        assert client["gender"] == "male"
        assert client["basicAid"]["water"] is True
        cleanup_keys.append(("clients", client_list[0]))

    def test_incident_form_ui_renders_after_login(self, page: Page):
        """After login the form selector shows Incident Report and SafeBase Form."""
        do_login(page)
        expect(page.locator('button:has-text("Incident Report")')).to_be_visible()
        expect(page.locator('button:has-text("SafeBase Form")')).to_be_visible()
        expect(page.locator('text=Tap to start speaking')).to_be_visible()
