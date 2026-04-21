"""
E2E tests for SafeBase form submission.

Submits via the backend API (no Claude extraction) and verifies in Firebase.
"""

import requests
from playwright.sync_api import Page, expect
from .conftest import do_login, BASE_URL, get_firebase_id_token_for_uid

SAMPLE_SAFEBASE_DATA = {
    "site": "townHall",
    "male": {"lessThan18": 0, "from18to25": 3, "from26to39": 0, "over40": 0},
    "female": {"lessThan18": 0, "from18to25": 0, "from26to39": 2, "over40": 0},
    "nonBinary": {"lessThan18": 0, "from18to25": 0, "from26to39": 0, "over40": 0},
    "assistanceRendered": {
        "directions": 2, "bus": 0, "train": 1,
        "taxi": 0, "deviceCharge": 0, "familyReconnect": 0,
    },
}


class TestSafeBaseSubmission:
    def test_submit_safebase_writes_to_firebase(self, fb_db, cleanup_keys):
        """Submit a SafeBase form via the API and verify it in Firebase."""
        id_token = get_firebase_id_token_for_uid("e2e-test-user")
        resp = requests.post(
            "http://localhost:8000/api/submit",
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            json={
                "form_type": "safebase",
                "form_data": SAMPLE_SAFEBASE_DATA,
            },
        )
        assert resp.status_code == 200, f"Submit failed: {resp.text}"
        key = resp.json()["key"]

        form = fb_db.reference(f"safeSpaceForms/{key}").get()
        assert form is not None, "SafeBase form not found in Firebase"
        assert form["male"]["from18to25"] == 3
        assert form["female"]["from26to39"] == 2
        assert form["assistanceRendered"]["directions"] == 2
        assert form.get("createdBy") == "e2e-test-user"
        cleanup_keys.append(("safeSpaceForms", key))

    def test_safebase_form_ui_switch(self, page: Page):
        """Clicking 'SafeBase Form' button switches the active form type."""
        do_login(page)
        page.click('button:has-text("SafeBase Form")')
        safebase_btn = page.locator('button:has-text("SafeBase Form")')
        expect(safebase_btn).to_be_visible()
        # The active button gets the 'blue' colour class
        import re
        expect(safebase_btn).to_have_class(re.compile(r"active"))
