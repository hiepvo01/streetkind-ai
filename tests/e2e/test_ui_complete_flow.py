"""
Comprehensive UI flow E2E test with screenshots at every step.

Why this exists: contract-level API tests pass even when the UI is broken
(extract returns valid JSON but the form doesn't bind it; audio uploads but
the player doesn't render; transcripts save but the list panel ignores them).
This test exercises the actual screens a volunteer touches and saves a
screenshot after every meaningful state change so regressions are visible.

Why this doesn't drive the real microphone:
- Headless Chromium can't grant a real mic permission for SpeechRecognition
  (it depends on Google's STT service over a real audio stream).
- Audio capture (MediaRecorder) we mock by uploading a synthetic WebM blob
  through the same /api/.../audio endpoint the frontend would call.
- Speech-to-text we sidestep by submitting the form via the API and then
  exercising the UI display path (the part that's actually fragile).
"""

from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, expect

from .conftest import (
    do_login,
    BASE_URL,
    DEMO_VOLUNTEER,
    DEMO_ADMIN,
    API_BASE_URL,
    FIREBASE_WEB_API_KEY,
    get_firebase_id_token_for_uid,
)

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


def _shot(page: Page, name: str) -> None:
    """Take a screenshot named with a numeric prefix so they sort in order."""
    page.screenshot(path=str(SCREENSHOT_DIR / f"{name}.png"), full_page=True)


def _real_login(page: Page, account: dict) -> None:
    """Log in via the real Firebase Auth flow (not a custom token)."""
    page.goto(BASE_URL)
    page.wait_for_selector('input[placeholder="Email Address"]', timeout=10000)
    page.fill('input[placeholder="Email Address"]', account["email"])
    page.fill('input[placeholder="Password"]', account["password"])
    page.click('button:has-text("Login")')
    page.wait_for_selector('text=Tap to start speaking', timeout=15000)


def _build_minimal_incident_via_api(uid_token: str, *, with_audio: bool = False) -> dict:
    """
    Submit a realistic incident through the API as the logged-in user, and
    optionally attach a transcript + audio blob. Returns {incident_id,
    transcript_id?}.
    """
    headers = {"Authorization": f"Bearer {uid_token}", "Content-Type": "application/json"}

    incident_payload = {
        "incident": {
            "teamLeaderName": "UI Flow Test",
            "site": "townHall",
            "location": {"address": "Town Hall steps", "latitude": None, "longitude": None},
            "encounteredBy": {"generalPublic": True},
            "incidentDescription": "UI flow test - drunk 19yo male with friends, taxi to hotel, water provided",
            "incidentOutcome": "Escorted to taxi, water given",
            "majorIncident": False,
        },
        "clients": [{
            "firstName": "JasonTest",
            "gender": "male",
            "ageGroup": "18to25",
            "alone": False,
            "intoxicationSigns": {"behaviour": True, "speech": False, "balance": False,
                                  "coordination": False, "notVisible": False},
            "drugUseSigns": {"notVisible": True, "observed": False, "visibleSigns": False, "disclosed": False},
            "transportInformation": {"taxi": True, "bus": False, "train": False, "uber": False, "other": False},
            "basicAid": {"water": True, "vomitBag": False, "footwear": False, "lollipop": False},
            "escortedTo": {"accommodation": True, "transport": False, "friends": False, "other": False},
            "safeSpace": {"escortedTo": True, "soberedUp": False},
        }],
    }

    r = requests.post(
        f"{API_BASE_URL}/api/submit",
        headers=headers,
        json={"form_type": "incident", "form_data": incident_payload, "status": "completed"},
        timeout=30,
    )
    assert r.status_code == 200, f"submit failed: {r.status_code} {r.text}"
    incident_id = r.json()["key"]
    result = {"incident_id": incident_id}

    if with_audio:
        # Create transcript text record
        r = requests.post(
            f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
            headers=headers,
            json={
                "text": "I am helping Jason 19 years old he is drunk with his friends and we caught a taxi to his hotel and gave him a water bottle",
                "audioDurationMs": 8500,
                "extractionMeta": {"model": "claude-haiku-4-5", "latencyMs": 1850},
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        transcript_id = r.json()["transcriptId"]
        result["transcript_id"] = transcript_id

        # Upload a synthetic WebM blob (valid EBML header so the magic-byte
        # check passes). Encodes nothing meaningful but the player will load.
        webm_bytes = b"\x1a\x45\xdf\xa3" + b"ui-flow-test-payload" * 80
        r = requests.post(
            f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts/{transcript_id}/audio",
            headers={"Authorization": f"Bearer {uid_token}"},
            files={"audio": ("test.webm", webm_bytes, "audio/webm")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        result["audio_url"] = r.json()["audioUrl"]

    return result


def _delete_incident_via_api(uid_token: str, incident_id: str) -> None:
    requests.delete(
        f"{API_BASE_URL}/api/forms/incident/{incident_id}",
        headers={"Authorization": f"Bearer {uid_token}"},
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCompleteUIFlow:
    def test_login_and_form_selector_render(self, page: Page):
        """Login screen -> credentials -> form selector. Screenshots: 01-03."""
        page.goto(BASE_URL)
        _shot(page, "01_login_page")

        page.fill('input[placeholder="Email Address"]', DEMO_VOLUNTEER["email"])
        page.fill('input[placeholder="Password"]', DEMO_VOLUNTEER["password"])
        _shot(page, "02_login_credentials_filled")

        page.click('button:has-text("Login")')
        page.wait_for_selector('text=Tap to start speaking', timeout=15000)
        expect(page.locator('button:has-text("Incident Report")')).to_be_visible()
        expect(page.locator('button:has-text("SafeBase Form")')).to_be_visible()
        _shot(page, "03_form_selector_after_login")

    def test_voice_input_screen_components(self, page: Page):
        """Verify the voice input screen has the mic, transcript area, etc.

        This documents the on-screen elements; mic is not actually invoked
        because headless can't satisfy the speech recognition stack.
        """
        _real_login(page, DEMO_VOLUNTEER)
        _shot(page, "04_voice_input_idle")

        mic = page.locator('button.mic-button, .mic-button')
        expect(mic.first).to_be_visible()
        expect(page.locator('text=Tap to start speaking')).to_be_visible()
        # Form data section should also be visible (it's not gated on transcript)
        expect(page.locator('text=Form data')).to_be_visible()
        _shot(page, "05_voice_input_full_view")

    def test_dashboard_loads_with_stats(self, page: Page):
        """Dashboard view shows the 11 stat cards."""
        _real_login(page, DEMO_VOLUNTEER)
        page.locator('i.sidebar.icon').first.click(timeout=5000)
        page.click('text=Dashboard', timeout=5000)
        page.wait_for_selector('text=People Assisted', timeout=10000)
        _shot(page, "06_dashboard")

        # Pick a couple of stats and verify they're present
        for stat in ("People Assisted", "Volunteer Hours", "Welfare Checks"):
            expect(page.locator(f"text={stat}")).to_be_visible()

    def test_my_incidents_shows_submitted_incident_via_api(self, page: Page, fb_db):
        """
        Submit an incident through the API as the demo volunteer, then
        navigate through the UI to verify it appears in My Incidents.
        """
        # Sign in via the public Identity Toolkit so the seed incident is
        # owned by the same user we'll log in as in the browser.
        sign_in = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
            json={
                "email": DEMO_VOLUNTEER["email"],
                "password": DEMO_VOLUNTEER["password"],
                "returnSecureToken": True,
            },
            timeout=20,
        )
        sign_in.raise_for_status()
        demo_token = sign_in.json()["idToken"]

        seed = _build_minimal_incident_via_api(demo_token)

        try:
            _real_login(page, DEMO_VOLUNTEER)
            _shot(page, "07_logged_in_homepage")

            # Navigate to My Incidents
            page.locator('i.sidebar.icon').first.click(timeout=5000)
            page.click('text=My Incidents', timeout=5000)
            page.wait_for_selector('text=My Incidents', timeout=5000)
            _shot(page, "08_my_incidents_list")

            # The incident should be visible (description text is searchable)
            expect(page.locator('text=UI flow test - drunk 19yo male')).to_be_visible(timeout=10000)
        finally:
            _delete_incident_via_api(demo_token, seed["incident_id"])

    def test_audio_player_renders_in_incident_modal(self, page: Page, fb_db):
        """
        Submit an incident WITH a transcript + synthetic audio blob via API,
        log in, open My Incidents, click the incident, and verify the
        IncidentEditModal renders an <audio controls> element with a
        signed URL.
        """
        # Sign in as demo volunteer to get their token + uid for seeding
        sign_in = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}",
            json={
                "email": DEMO_VOLUNTEER["email"],
                "password": DEMO_VOLUNTEER["password"],
                "returnSecureToken": True,
            },
            timeout=20,
        )
        sign_in.raise_for_status()
        demo_token = sign_in.json()["idToken"]

        seed = _build_minimal_incident_via_api(demo_token, with_audio=True)
        if "transcript_id" not in seed:
            pytest.skip("Audio storage disabled on backend - cannot exercise audio modal")

        try:
            _real_login(page, DEMO_VOLUNTEER)

            # Open the sidebar -> My Incidents
            page.locator('i.sidebar.icon').first.click(timeout=5000)
            page.click('text=My Incidents', timeout=5000)
            page.wait_for_selector('text=UI flow test - drunk 19yo male', timeout=10000)
            _shot(page, "09_my_incidents_with_audio_record")

            # Open the edit modal for our incident. Each row in the FormList
            # table has an icon-only Edit button (title='Edit'). Find the row
            # containing our description and click its Edit button.
            row = page.locator('tr:has-text("UI flow test - drunk 19yo male")').first
            row.locator('button[title="Edit"]').first.click(timeout=5000)

            # Modal should open with the transcript panel at the top
            page.wait_for_selector('text=Voice Transcripts', timeout=10000)
            _shot(page, "10_incident_modal_open_with_transcripts")

            # The transcript panel should contain an <audio> element with a
            # src that includes X-Goog-Signature (signed URL contract).
            audio_el = page.locator('audio')
            expect(audio_el).to_be_visible(timeout=5000)
            audio_src = audio_el.first.get_attribute('src')
            assert audio_src and "X-Goog-Signature" in audio_src, (
                f"audio src is not a signed URL: {audio_src!r}"
            )

            # The transcript text we seeded should be visible too.
            expect(page.locator('text=we caught a taxi to his hotel')).to_be_visible(timeout=5000)
            _shot(page, "11_incident_modal_audio_player_visible")

            # Confirm the signed URL actually serves bytes (small HEAD-style probe)
            probe = requests.get(audio_src, timeout=20)
            assert probe.status_code == 200, f"signed URL did not serve content: {probe.status_code}"
            assert len(probe.content) > 0
            _shot(page, "12_incident_modal_full")
        finally:
            # API delete cascades through clients + transcripts + Storage blobs
            _delete_incident_via_api(demo_token, seed["incident_id"])

    def test_logout_returns_to_login(self, page: Page):
        """Sanity: clicking logout brings the user back to the login screen."""
        _real_login(page, DEMO_VOLUNTEER)
        page.locator('i.sidebar.icon').first.click(timeout=5000)
        page.locator('text=Log out').first.click(timeout=5000)
        page.wait_for_selector('input[placeholder="Email Address"]', timeout=10000)
        _shot(page, "13_after_logout_login_screen")
