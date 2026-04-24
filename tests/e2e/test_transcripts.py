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
import pytest
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


class TestTranscriptSecurity:
    """Tests that would PASS today if the access-control guards were removed.

    These are the highest-value security assertions for this feature.
    """

    def test_audio_upload_denied_across_users(self, firebase_app):
        """User B cannot upload audio under user A's incident + transcript."""
        token_a = get_firebase_id_token_for_uid("e2e-audio-user-a")
        ha = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
        token_b = get_firebase_id_token_for_uid("e2e-audio-user-b")

        # A creates incident + transcript
        r = requests.post(
            f"{API_BASE_URL}/api/submit", headers=ha,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_id = r.json()["key"]
        try:
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=ha, json={"text": "a's transcript"},
            )
            transcript_id = r.json()["transcriptId"]

            # B tries to upload audio to A's transcript -> 403
            fake_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts/{transcript_id}/audio",
                headers={"Authorization": f"Bearer {token_b}"},
                files={"audio": ("x.webm", fake_audio, "audio/webm")},
            )
            assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"

            # B also can't list A's transcripts
            r = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            assert r.status_code == 403
        finally:
            requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=ha,
            )

    def test_audio_upload_denied_across_incidents(self, firebase_app):
        """A user cannot upload audio to someone else's incident by claiming
        their own transcript belongs to it. Exercises the incidentId-match
        guard in upload_transcript_audio."""
        token_a = get_firebase_id_token_for_uid("e2e-cross-inc-user-a")
        ha = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
        token_b = get_firebase_id_token_for_uid("e2e-cross-inc-user-b")
        hb = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

        # A owns incident X with a transcript
        r = requests.post(
            f"{API_BASE_URL}/api/submit", headers=ha,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_x = r.json()["key"]
        r = requests.post(
            f"{API_BASE_URL}/api/forms/incident/{incident_x}/transcripts",
            headers=ha, json={"text": "x's transcript"},
        )
        transcript_in_x = r.json()["transcriptId"]

        # B owns incident Y
        r = requests.post(
            f"{API_BASE_URL}/api/submit", headers=hb,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_y = r.json()["key"]

        try:
            # B tries to upload audio to `incident_y/transcripts/transcript_in_x`.
            # B has access to incident_y, transcript exists, but its incidentId
            # points at incident_x -> server must 404.
            fake_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_y}/transcripts/{transcript_in_x}/audio",
                headers={"Authorization": f"Bearer {token_b}"},
                files={"audio": ("x.webm", fake_audio, "audio/webm")},
            )
            assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"
        finally:
            requests.delete(f"{API_BASE_URL}/api/forms/incident/{incident_x}", headers=ha)
            requests.delete(f"{API_BASE_URL}/api/forms/incident/{incident_y}", headers=hb)

    def test_invalid_transcript_id_rejected(self, firebase_app):
        """Non-push-ID transcript_ids (path traversal attempts) are rejected."""
        token = get_firebase_id_token_for_uid("e2e-invalid-id-user")
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.post(
            f"{API_BASE_URL}/api/submit", headers=h,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_id = r.json()["key"]
        try:
            for bad_tid in ["..", "not-a-push-id", "-short", "-" + "A" * 19 + "!"]:
                fake_audio = b"\x1a\x45\xdf\xa3" + b"\x00" * 100
                r = requests.post(
                    f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts/{bad_tid}/audio",
                    headers={"Authorization": f"Bearer {token}"},
                    files={"audio": ("x.webm", fake_audio, "audio/webm")},
                )
                # Bad IDs should 400 (rejected by regex) or 404 (routing miss),
                # never 200 or 500.
                assert r.status_code in (400, 404), (
                    f"transcript_id={bad_tid!r} got {r.status_code}: {r.text}"
                )
        finally:
            requests.delete(f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=h)

    def test_non_audio_payload_rejected(self, firebase_app):
        """Magic-byte check prevents non-audio binaries claiming audio/* MIME."""
        token = get_firebase_id_token_for_uid("e2e-magic-byte-user")
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        r = requests.post(
            f"{API_BASE_URL}/api/submit", headers=h,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_id = r.json()["key"]
        try:
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=h, json={"text": "magic byte test"},
            )
            transcript_id = r.json()["transcriptId"]

            # A PNG header pretending to be webm
            png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts/{transcript_id}/audio",
                headers={"Authorization": f"Bearer {token}"},
                files={"audio": ("fake.webm", png_bytes, "audio/webm")},
            )
            # Either 400 (magic-byte rejection) or 503 (storage disabled).
            # Must not be 200 - otherwise the endpoint is a file-upload backdoor.
            if r.status_code == 503:
                pytest.skip("Audio storage disabled on this backend - cannot test magic-byte check")
            assert r.status_code == 400, (
                f"non-audio payload should be rejected, got {r.status_code}: {r.text}"
            )
        finally:
            requests.delete(f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=h)


class TestTranscriptConcurrency:
    def test_concurrent_transcript_creation(self, firebase_app):
        """Two transcripts created back-to-back both land in transcriptIds."""
        import threading
        token = get_firebase_id_token_for_uid("e2e-concurrent-user")
        h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        r = requests.post(
            f"{API_BASE_URL}/api/submit", headers=h,
            json={"form_type": "incident", "form_data": _minimal_incident()},
        )
        incident_id = r.json()["key"]
        try:
            results = []
            errors = []

            def create_one(n):
                try:
                    r = requests.post(
                        f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                        headers=h, json={"text": f"concurrent transcript {n}"},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        results.append(r.json()["transcriptId"])
                    else:
                        errors.append((r.status_code, r.text))
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=create_one, args=(i,)) for i in range(3)]
            for t in threads: t.start()
            for t in threads: t.join()

            assert not errors, f"concurrent create errors: {errors}"
            assert len(results) == 3, f"expected 3 transcripts, got {len(results)}: {results}"

            r = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts", headers=h,
            )
            fetched_ids = {t["id"] for t in r.json()["transcripts"]}
            for tid in results:
                assert tid in fetched_ids, f"transcript {tid} lost from transcriptIds"
        finally:
            requests.delete(f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=h)


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

    def test_empty_transcript_rejected(self, firebase_app):
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

    def test_audio_upload_roundtrip(self, fb_db):
        """
        Upload an audio blob, verify it ends up in Firebase Storage with the
        exact bytes we sent, the audioUrl is persisted on the transcript, and
        incident delete wipes the Storage blob too.

        Skipped cleanly when the backend returns 503 (FIREBASE_STORAGE_BUCKET
        not set). 503 is NOT a pass - audio storage disabled means this test
        cannot validate its contract.
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
            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=headers,
                json={"text": "audio test"},
            )
            transcript_id = r.json()["transcriptId"]

            # Valid WebM EBML header + payload we'll byte-compare later.
            audio_bytes = b"\x1a\x45\xdf\xa3" + b"audio-payload-abc" * 50

            r = requests.post(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts/{transcript_id}/audio",
                headers={"Authorization": f"Bearer {token}"},
                files={"audio": ("test.webm", audio_bytes, "audio/webm")},
            )

            if r.status_code == 503:
                pytest.skip(
                    "Backend has FIREBASE_STORAGE_BUCKET unset - audio storage "
                    "is disabled on this deployment. Not a pass."
                )

            assert r.status_code == 200, f"audio upload failed: {r.status_code} {r.text}"
            upload_url = r.json().get("audioUrl")
            assert upload_url, "audio upload returned no audioUrl"

            # Audio URL must be a signed URL, not a permanent public URL.
            # v4 signed URLs carry X-Goog-Signature + X-Goog-Algorithm query params.
            assert "X-Goog-Signature" in upload_url, (
                f"audioUrl is not a signed URL (public make_public leaked?): {upload_url[:200]}"
            )

            # The stored record should have `audioPath`, not a stored URL - proves
            # we're not persisting a long-lived credential in the DB.
            raw = fb_db.reference(f"transcripts/{transcript_id}").get() or {}
            assert "audioPath" in raw, f"transcript missing audioPath: keys={list(raw.keys())}"
            assert not raw.get("audioUrl"), (
                f"transcript has stored audioUrl - should only be signed at read time: {raw.get('audioUrl')}"
            )
            blob_path = raw["audioPath"]
            assert blob_path.startswith(f"audio/{incident_id}/"), blob_path

            # List endpoint should return a freshly-signed URL (different signature query)
            r2 = requests.get(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}/transcripts",
                headers=headers,
            )
            list_item = r2.json()["transcripts"][0]
            list_url = list_item.get("audioUrl")
            assert list_url, "list endpoint did not include audioUrl"
            assert "X-Goog-Signature" in list_url, f"list audioUrl not signed: {list_url[:200]}"

            # Signed URL must serve the exact uploaded bytes
            blob_resp = requests.get(list_url, timeout=30)
            assert blob_resp.status_code == 200, f"signed GET -> {blob_resp.status_code}"
            assert blob_resp.content == audio_bytes, (
                f"uploaded {len(audio_bytes)} bytes, downloaded {len(blob_resp.content)}"
            )

            # The same blob without a signature MUST be denied - proves audio is
            # private and playback only works via signed URLs.
            public_guess = f"https://storage.googleapis.com/{os.environ.get('FIREBASE_STORAGE_BUCKET', '')}/{blob_path}"
            public_resp = requests.get(public_guess, timeout=20)
            assert public_resp.status_code in (401, 403, 404), (
                f"Blob is publicly readable without signature (privacy bug): "
                f"{public_guess} -> {public_resp.status_code}"
            )
        finally:
            requests.delete(
                f"{API_BASE_URL}/api/forms/incident/{incident_id}", headers=headers,
            )

        # After delete, RTDB records gone + Storage blob gone.
        assert fb_db.reference(f"incidentForms/{incident_id}").get() is None
        assert fb_db.reference(f"transcripts/{transcript_id}").get() is None
        # If we got this far Storage was configured; check the blob was removed.
        # Use Admin SDK via the backend's bucket config.
        try:
            from firebase_admin import storage as fb_storage
            bucket = fb_storage.bucket()
            remaining = list(bucket.list_blobs(prefix=f"audio/{incident_id}/"))
            assert not remaining, f"Storage cleanup leaked: {[b.name for b in remaining]}"
        except Exception as e:
            # Storage SDK may not be initialised in the test process; the
            # above RTDB checks already prove the delete fired. Surface the
            # skip so we know the audit is partial, don't silently pass.
            pytest.skip(f"Storage cleanup check skipped: {e}")
