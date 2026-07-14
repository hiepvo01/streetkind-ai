"""
E2E tests for the full incident CRUD flow:
submit -> fetch -> update -> delete, plus access-control.

Auto-cleans any leftover test records after each test.
"""

import requests
from .conftest import API_BASE_URL, get_firebase_id_token_for_uid


BASE_INCIDENT = {
    "incident": {
        "teamLeaderName": "CRUD Test Leader",
        "site": "townHall",
        "location": {"address": "CRUD test address", "latitude": None, "longitude": None},
        "startTime": 1752000000000,
        "endTime": 1752003600000,
        "incidentDescription": "CRUD test - delete me",
        "incidentOutcome": "CRUD test outcome",
        "encounteredBy": {"generalPublic": True, "skAmbassador": False},
        "otherServicesInvolved": {},
        "majorIncident": False,
    },
    "clients": [],
}


class TestIncidentCrud:
    def test_submit_fetch_update_delete(self, fb_db):
        token = get_firebase_id_token_for_uid("e2e-crud-user")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Submit
        r = requests.post(
            f"{API_BASE_URL}/api/submit",
            headers=headers,
            json={"form_type": "incident", "form_data": BASE_INCIDENT, "status": "draft"},
        )
        assert r.status_code == 200, r.text
        form_id = r.json()["key"]

        try:
            # Fetch
            r = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{form_id}", headers=headers,
            )
            assert r.status_code == 200
            full = r.json()
            assert full["incident"]["teamLeaderName"] == "CRUD Test Leader"
            assert full["incident"]["status"] == "draft"

            # Update - flip to completed, change description
            updated = {
                **BASE_INCIDENT,
                "incident": {
                    **BASE_INCIDENT["incident"],
                    "incidentDescription": "updated description",
                },
            }
            r = requests.put(
                f"{API_BASE_URL}/api/forms/incident/{form_id}",
                headers=headers,
                json={"form_data": updated, "status": "completed"},
            )
            assert r.status_code == 200, r.text

            # Verify update
            r = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{form_id}", headers=headers,
            )
            assert r.status_code == 200
            full = r.json()
            assert full["incident"]["incidentDescription"] == "updated description"
            assert full["incident"]["status"] == "completed"
            assert full["incident"].get("editedDate")  # update sets editedDate

        finally:
            # Delete
            r = requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{form_id}", headers=headers,
            )
            assert r.status_code == 200

        # Confirm gone
        assert fb_db.reference(f"incidentForms/{form_id}").get() is None

    def test_fetch_unknown_returns_404(self):
        token = get_firebase_id_token_for_uid("e2e-crud-user")
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            f"{API_BASE_URL}/api/forms/incident/-AAAAAAAAAAAAAAAAAAA",
            headers=headers,
        )
        assert r.status_code == 404

    def test_invalid_form_id_rejected(self):
        token = get_firebase_id_token_for_uid("e2e-crud-user")
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            f"{API_BASE_URL}/api/forms/incident/../../etc/passwd",
            headers=headers,
        )
        # Route pattern may reject first (404) or the validator (400) - both fine
        assert r.status_code in (400, 404)

    def test_access_control_outside_hierarchy(self, fb_db):
        """A different user can't read/edit/delete someone else's incident."""
        token_a = get_firebase_id_token_for_uid("e2e-crud-user-a")
        headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
        token_b = get_firebase_id_token_for_uid("e2e-crud-user-b")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # A creates an incident
        r = requests.post(
            f"{API_BASE_URL}/api/submit",
            headers=headers_a,
            json={"form_type": "incident", "form_data": BASE_INCIDENT},
        )
        form_id = r.json()["key"]

        try:
            # B tries to fetch -> 403
            r = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{form_id}", headers=headers_b,
            )
            assert r.status_code == 403, r.text

            # B tries to delete -> 403
            r = requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{form_id}", headers=headers_b,
            )
            assert r.status_code == 403
        finally:
            requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{form_id}", headers=headers_a,
            )
