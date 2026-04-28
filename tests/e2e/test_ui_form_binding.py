"""
The test that would have caught the original age_group / emergencyServicesCalled
silent-binding bugs.

Seeds an incident with a known payload that exercises every form section
(radios + checkboxes), opens the IncidentEditModal, and asserts the actual
DOM input states match what was stored. If a tab reads `data.<typo>`, those
inputs render unchecked and this test fails.

These are PROD-targeted by default (use API_BASE_URL=http://localhost:8000
to retarget local).
"""

import os
import requests
from playwright.sync_api import Page, expect

from .conftest import (
    BASE_URL,
    DEMO_VOLUNTEER,
    API_BASE_URL,
)


def _demo_token() -> str:
    web_api_key = os.environ.get(
        "FIREBASE_WEB_API_KEY", "AIzaSyD6q7A5-g26ma7Dv2w8PLa4e0FdM_D3eVQ",
    )
    sign_in = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={web_api_key}",
        json={
            "email": DEMO_VOLUNTEER["email"],
            "password": DEMO_VOLUNTEER["password"],
            "returnSecureToken": True,
        },
        timeout=20,
    )
    sign_in.raise_for_status()
    return sign_in.json()["idToken"]


def _seed_full_client_incident(token: str) -> str:
    """
    Submit an incident with EVERY radio + checkbox set to a known value so
    we can read each one back through the UI. Returns the incident_id.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "incident": {
            "teamLeaderName": "Form-Binding Test",
            "site": "townHall",
            "location": {"address": "Form-binding test address",
                         "latitude": None, "longitude": None},
            "encounteredBy": {"generalPublic": True},
            "incidentDescription": "FORM_BINDING_TEST - delete me",
            "incidentOutcome": "ok",
            "majorIncident": False,
        },
        "clients": [{
            "firstName": "BindingTest",
            "gender": "male",
            "ageGroup": "18to25",  # Critical: must match config/fields/shared.json key
            "alone": False,
            # Every nested-checkbox section gets at least one true value so
            # we can prove each tab reads the right schema field.
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
            "sexualAssault": {"observed": False, "visibleSigns": False,
                              "disclosed": False, "notVisible": True},
            "physicalAssault": {"observed": False, "visibleSigns": False,
                                "disclosed": False, "notVisible": True},
            "domesticViolence": {"observed": False, "visibleSigns": False,
                                 "disclosed": False, "notVisible": True},
            "transportInformation": {
                "bus": False, "train": False, "taxi": True, "uber": False, "other": False,
            },
            "escortedTo": {"accommodation": True, "transport": False,
                           "friends": False, "other": False},
            "safeSpace": {"escortedTo": True, "soberedUp": False},
            "basicAid": {"vomitBag": False, "water": True,
                         "footwear": False, "lollipop": False},
            "additionalAid": {"firstAid": False, "mentalHealthAid": False},
            "emergencyServicesCalled": {  # Was the typo'd field
                "ambulanceServiceCalled": True,
                "policeServiceCalled": False,
                "fireServiceCalled": False,
            },
            "physicalAssaultRisk": 2,
            "sexualAssaultRisk": 0,
            "clientConsciousness": 1,         # Was nested under data.theftRisk
            "clientValuablesVisibility": 0,   # Was nested under data.theftRisk
            "clientLostProperty": 2,          # Was nested under data.theftRisk
            "injury": {"roadRelated": True, "other": False},
            "clientServiceReferrals": {  # Was the typo'd field
                "alcoholDrugInfoService": False, "beyondBlue": False,
                "childProtectionServices": False, "dvLine": False,
                "hospital": True, "lifeline": False, "link2home": False,
                "salvosStreetLevel": False, "streetbeatBus": False,
                "traffickingSlaveryAFP": False,
            },
            "serviceInformation": {"contactedService": True, "infoProvided": False},
            "otherSupport": {"welfareCheck": True, "homelessSupport": False},
        }],
    }

    r = requests.post(
        f"{API_BASE_URL}/api/submit",
        headers=headers,
        json={"form_type": "incident", "form_data": payload, "status": "completed"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["key"]


def _real_login(page: Page) -> None:
    page.goto(BASE_URL)
    page.wait_for_selector('input[placeholder="Email Address"]', timeout=10000)
    page.fill('input[placeholder="Email Address"]', DEMO_VOLUNTEER["email"])
    page.fill('input[placeholder="Password"]', DEMO_VOLUNTEER["password"])
    page.click('button:has-text("Login")')
    page.wait_for_selector('text=Tap to start speaking', timeout=15000)


def _open_incident_modal(page: Page, description_text: str) -> None:
    page.locator('i.sidebar.icon').first.click(timeout=5000)
    page.click('text=My Incidents', timeout=5000)
    page.wait_for_selector(f'text={description_text}', timeout=10000)
    row = page.locator(f'tr:has-text("{description_text}")').first
    row.locator('button[title="Edit"]').first.click(timeout=5000)
    page.wait_for_selector('text=Incident Details', timeout=10000)


def _checkbox_in_section(page: Page, section_label: str, item_label: str):
    """Get the <input type=checkbox> inside the labelled section that matches item_label."""
    # Each CheckboxGroup renders the section label as <label> followed by a flex
    # container of <Checkbox label="...">. Target the underlying input.
    return page.locator(
        f'div.field:has(label:text-is("{section_label}")) >> '
        f'div.checkbox:has(label:text-is("{item_label}")) input'
    )


def _radio_in_section(page: Page, section_label: str, item_label: str):
    return page.locator(
        f'div.field:has(label:text-is("{section_label}")) >> '
        f'div.radio:has(label:text-is("{item_label}")) input'
    )


# ---------------------------------------------------------------------------
# The actual test
# ---------------------------------------------------------------------------


class TestUIRendersStoredFieldValues:
    def test_all_client_form_sections_bind_to_schema(self, page: Page):
        """
        Single test that opens the modal for a known-payload incident and
        verifies every radio + checkbox renders the stored value. This is
        what would have caught age_group / emergencyServicesCalled /
        clientServiceReferrals / theftRisk-namespace / injury bugs.
        """
        token = _demo_token()
        incident_id = _seed_full_client_incident(token)

        try:
            _real_login(page)
            _open_incident_modal(page, "FORM_BINDING_TEST - delete me")

            # The Client form opens on the Client Info tab by default.

            # ---- Tab 1: Client Information ----
            expect(_radio_in_section(page, "Gender", "Male")).to_be_checked()
            expect(_radio_in_section(page, "Age Group", "18 to 25")).to_be_checked()
            expect(_radio_in_section(page, "Alone", "No")).to_be_checked()
            expect(_checkbox_in_section(page, "Intoxication Signs", "Speech")).to_be_checked()
            expect(_checkbox_in_section(page, "Intoxication Signs", "Balance")).to_be_checked()
            expect(_checkbox_in_section(page, "Intoxication Signs", "Co-ordination")).not_to_be_checked()
            expect(_checkbox_in_section(page, "Drug Use Signs", "Not Visible")).to_be_checked()

            # ---- Tab 2: Basic Support ----
            page.locator('a:has-text("Basic Support"), .item:has-text("Basic Support")').first.click()
            expect(_checkbox_in_section(page, "Transport Information", "Taxi")).to_be_checked()
            expect(_checkbox_in_section(page, "Transport Information", "Uber")).not_to_be_checked()
            expect(_checkbox_in_section(page, "Escort", "Accommodation")).to_be_checked()
            expect(_checkbox_in_section(page, "Safe Space", "Escorted to Safe Base")).to_be_checked()

            # ---- Tab 3: Health Support ----
            page.locator('a:has-text("Health Support"), .item:has-text("Health Support")').first.click()
            expect(_checkbox_in_section(page, "Basic Aid", "Water")).to_be_checked()
            expect(_checkbox_in_section(page, "Basic Aid", "Vomit Bag")).not_to_be_checked()
            # The bug: this used to read `data.emergencyServices` (typo) and
            # render as unchecked even when `emergencyServicesCalled.ambulanceServiceCalled=true`.
            expect(_checkbox_in_section(page, "Emergency Services", "Ambulance")).to_be_checked()
            expect(_checkbox_in_section(page, "Emergency Services", "Police")).not_to_be_checked()

            # ---- Tab 4: Risk Minimisation ----
            page.locator(
                'a:has-text("Risk Minimisation"), .item:has-text("Risk Minimisation")'
            ).first.click()
            # Flat int radios. The bug: these used to live under data.theftRisk.*.
            expect(_radio_in_section(page, "Physical Assault Risk", "Minor Conflict De-escalated")).to_be_checked()
            expect(_radio_in_section(page, "Sexual Assault Risk", "No Risk")).to_be_checked()
            expect(_radio_in_section(page, "Client Consciousness", "Unconscious")).to_be_checked()
            expect(_radio_in_section(page, "Valuables Visibility", "Not Visible")).to_be_checked()
            expect(_radio_in_section(page, "Lost Property", "Valuables Lost")).to_be_checked()
            # The bug: this used to read `data.injuryRisk` (typo). Schema is `injury`.
            expect(_checkbox_in_section(page, "Injury Risk", "Road Related")).to_be_checked()
            expect(_checkbox_in_section(page, "Injury Risk", "Other")).not_to_be_checked()

            # ---- Tab 5: Services Referred ----
            page.locator(
                'a:has-text("Services Referred"), .item:has-text("Services Referred")'
            ).first.click()
            # The bug: this used to read `data.serviceReferrals` (typo). Schema is `clientServiceReferrals`.
            expect(_checkbox_in_section(page, "Client Service Referrals", "Hospital")).to_be_checked()
            expect(_checkbox_in_section(page, "Client Service Referrals", "Lifeline")).not_to_be_checked()
            expect(_checkbox_in_section(page, "Service Information", "Contacted Service")).to_be_checked()
            expect(_checkbox_in_section(page, "Other Support", "Welfare Check")).to_be_checked()
        finally:
            requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
