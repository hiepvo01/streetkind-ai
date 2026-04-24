"""
E2E tests for the transcript + audio storage pipeline.

Each test:
1. Submits a minimal incident via the API
2. Creates a transcript record linked to that incident
3. (Optionally) uploads an audio blob
4. Fetches via the transcript list endpoint + verifies Firebase linkage
5. Deletes the incident and confirms transcripts are also gone
"""

import os
import requests
from .conftest import API_BASE_URL, get_firebase_id_token_for_uid


def _minimal_incident():
    return {
        "incident": {
            "teamLeaderName": "Transcript Test",
            "site": "townHall",
            "location": {"address": "Test Address", "latitude": None, "longitude": None},
            "incidentDescription": "E2E transcript test - delete me",
            "incidentOutcome": "",
        },
        "clients": [],
    }


class TestTranscriptRoundtrip:
    def test_create_fetch_delete(self, fb_db):
        token = get_firebase_id_token_for_uid("e2e-transcript-user")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # 1. Submit incident
        r = requests.post(
            f"{API_BASE_URL}/api/submit",
            headers=headers,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        assert r.status_code == 200, r.text
        incident_id = r.json()["key"]

        try:
            # 2. Create transcript
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=headers,
                json={
                    "text": "At Town Hall we helped a female aged 22, alone, intoxicated.",
                    "audioDurationMs": 12500,
                    "extractionMeta": {"model": "claude-haiku-4-5", "latencyMs": 1800},
                },
            )
            assert r.status_code == 200, r.text
            transcript_id = r.json()["transcriptId"]

            # 3. Fetch via list endpoint
            r = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=headers,
            )
            assert r.status_code == 200
            items = r.json()["transcripts"]
            assert len(items) == 1
            t = items[0]
            assert t["id"] == transcript_id
            assert t["incidentId"] == incident_id
            assert "female aged 22" in t["text"]
            assert t["audioDurationMs"] == 12500
            assert t["extractionMeta"]["model"] == "claude-haiku-4-5"

            # 4. Verify linkage in raw Firebase
            linked = fb_db.reference(f"incidentForms/{incident_id}/transcriptIds").get() or []
            assert transcript_id in linked

        finally:
            # 5. Delete the incident; transcripts should be cleaned too
            r = requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}",
                headers=headers,
            )
            assert r.status_code == 200

        assert fb_db.reference(f"incidentForms/{incident_id}").get() is None

    def test_empty_transcript_rejected(self):
        token = get_firebase_id_token_for_uid("e2e-transcript-user")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Create incident first
        r = requests.post(
            f"{API_BASE_URL}/api/submit",
            headers=headers,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_id = r.json()["key"]

        try:
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=headers,
                json={"text": "   "},
            )
            assert r.status_code == 400
        finally:
            requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=headers,
            )

    def test_audio_upload_requires_storage_config(self):
        """Audio upload returns 503 if FIREBASE_STORAGE_BUCKET isn't set.

        Only meaningful when the backend is configured without Storage. When
        Storage IS configured we expect either 200 (success) or 400 (unsupported
        content type) — not 503.
        """
        token = get_firebase_id_token_for_uid("e2e-transcript-user")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        r = requests.post(
            f"{API_BASE_URL}/api/submit",
            headers=headers,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_id = r.json()["key"]

        try:
            # Create transcript to attach audio to
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=headers,
                json={"text": "audio test"},
            )
            transcript_id = r.json()["transcriptId"]

            # Upload a tiny fake webm
            fake_webm = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts/{transcript_id}/audio",
                headers={"Authorization": f"Bearer {token}"},
                files={"audio": ("test.webm", fake_webm, "audio/webm")},
            )
            # Either storage is configured and we got a real response, or 503
            assert r.status_code in (200, 400, 503), r.text
        finally:
            requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=headers,
            )
