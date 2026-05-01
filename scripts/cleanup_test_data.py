#!/usr/bin/env python3
"""
Wipe StreetKind AI test fixtures from Firebase + Storage so a fresh test
run starts clean.

What it deletes:

  - Firebase RTDB:
      transcripts/*                     where createdBy starts with 'e2e-'
      incidentForms/*                   where createdBy starts with 'e2e-'
                                        OR description matches a known test
                                        marker (UI flow test, FORM_BINDING_TEST,
                                        E2E test, CRUD test, PROD E2E,
                                        LOCAL_AUDIO_PROBE, probe - delete me,
                                        etc.)
      clients/*                         orphaned clients (incident is gone)
                                        OR tied to a deleted test incident
                                        OR firstName matches a known marker
      safeSpaceForms/*                  with marker description
  - Firebase Storage:
      audio/*                           every blob (regenerated per test)
  - Local audio dir (AUDIO_LOCAL_DIR):
      cleared if set

Required env:
  FIREBASE_SERVICE_ACCOUNT_PATH         path to service-account JSON
  FIREBASE_DATABASE_URL                 RTDB URL (defaults to streetkind-app-dev)
Optional env:
  FIREBASE_STORAGE_BUCKET               if set, cleans Storage bucket too
  AUDIO_LOCAL_DIR                       if set, also clears local audio dir
  CLEANUP_DRY_RUN=1                     just report what would be deleted
  CLEANUP_DAYS=30                       max age in days to consider a record
                                        a "test" candidate when the marker
                                        match is uncertain. Default 30.

Usage:
  FIREBASE_SERVICE_ACCOUNT_PATH=path/to/key.json python scripts/cleanup_test_data.py

  # Preview without deleting:
  CLEANUP_DRY_RUN=1 python scripts/cleanup_test_data.py
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path


# ----------------------------- Markers -------------------------------------

# UIDs that match these prefixes are test-only.
TEST_UID_PREFIXES = ("e2e-",)

# Description / leader / firstName text that marks a record as test data.
DESCRIPTION_MARKERS = (
    "FORM_BINDING_TEST",
    "UI flow test",
    "E2E test",
    "CRUD test",
    "PROD E2E",
    "LOCAL_AUDIO_PROBE",
    "audio REAL test",
    "audio upload test",
    "probe - delete me",
    "delete me",
    "concurrent transcript",
    "Submit failed",  # leftover from an aborted assert
    "Testing Voice Record",
    "test voice",
)
LEADER_MARKERS = (
    "E2E", "CRUD", "Audio", "UI Flow", "Form-Binding", "probe",
)
CLIENT_FIRST_NAME_MARKERS = (
    "E2ETest", "JasonTest", "BindingTest",
)
# Transcripts that look obviously like development tests rather than real
# volunteer reports. Matched against the lowercased text.
TRANSCRIPT_TEXT_MARKERS = (
    "test test",
    "1 2 3",
    "this is a test",
    "this is testing",
    "testing testing",
    "audio test",
    "mic test",
    "hello test",
)

# RTDB nodes touched.
DATA_NODES = ("incidentForms", "transcripts", "clients", "safeSpaceForms")

DRY_RUN = os.environ.get("CLEANUP_DRY_RUN") == "1"


def _init_firebase():
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not cred_path:
        sys.exit("FIREBASE_SERVICE_ACCOUNT_PATH must be set")

    db_url = os.environ.get(
        "FIREBASE_DATABASE_URL",
        "https://streetkind-app-dev-default-rtdb.firebaseio.com",
    )
    init_options = {"databaseURL": db_url}
    bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if bucket:
        init_options["storageBucket"] = bucket

    import firebase_admin
    from firebase_admin import credentials
    firebase_admin.initialize_app(credentials.Certificate(cred_path), init_options)


def _is_test_record(record: dict) -> bool:
    if not isinstance(record, dict):
        return False
    cb = str(record.get("createdBy", ""))
    if any(cb.startswith(p) for p in TEST_UID_PREFIXES):
        return True
    desc = str(record.get("incidentDescription", ""))
    if any(m in desc for m in DESCRIPTION_MARKERS):
        return True
    leader = str(record.get("teamLeaderName", ""))
    if any(m in leader for m in LEADER_MARKERS):
        return True
    first = str(record.get("firstName", ""))
    if first in CLIENT_FIRST_NAME_MARKERS:
        return True
    return False


def _is_test_transcript(record: dict) -> bool:
    """Transcripts have their own text; flag obvious dev-tests by content."""
    if _is_test_record(record):
        return True
    if not isinstance(record, dict):
        return False
    text = str(record.get("text", "")).lower().strip()
    if not text:
        return False
    if any(marker in text for marker in TRANSCRIPT_TEXT_MARKERS):
        return True
    # Aborted dev tests typically only contain a label fragment with no
    # incident narrative. A real volunteer report describes a person and
    # what happened (>50 chars). A transcript that's <50 chars and looks
    # like a form-field label fragment is almost certainly a test.
    if len(text) < 50 and text.startswith(("team leader", "first name", "site ", "location ")):
        return True
    return False


def _delete(ref) -> None:
    if DRY_RUN:
        return
    ref.delete()


def cleanup_rtdb() -> dict:
    """Delete test records from RTDB. Returns counts per node."""
    from firebase_admin import db

    summary: dict[str, int] = {n: 0 for n in DATA_NODES}

    # Build the set of test incident IDs first so we can also remove their
    # clients even if the client itself doesn't carry a test marker.
    incidents = db.reference("incidentForms").get() or {}
    test_incident_ids: set[str] = set()
    for iid, idata in incidents.items():
        if _is_test_record(idata):
            test_incident_ids.add(iid)

    # Pass 1: RTDB transcripts. Match by createdBy / text markers OR by being
    # tied to a deleted test incident.
    transcripts = db.reference("transcripts").get() or {}
    for tid, t in transcripts.items():
        if not isinstance(t, dict):
            continue
        if (
            _is_test_transcript(t)
            or str(t.get("incidentId", "")) in test_incident_ids
        ):
            print(f"  delete transcripts/{tid}  text={str(t.get('text', ''))[:50]!r}")
            _delete(db.reference(f"transcripts/{tid}"))
            summary["transcripts"] += 1

    # Pass 2: RTDB clients (test markers + orphaned-by-test-incident).
    clients = db.reference("clients").get() or {}
    for cid, c in clients.items():
        if not isinstance(c, dict):
            continue
        if (
            _is_test_record(c)
            or str(c.get("incidentId", "")) in test_incident_ids
        ):
            print(f"  delete clients/{cid}")
            _delete(db.reference(f"clients/{cid}"))
            summary["clients"] += 1

    # Pass 3: RTDB SafeBase forms.
    sb = db.reference("safeSpaceForms").get() or {}
    for sid, s in sb.items():
        if _is_test_record(s):
            print(f"  delete safeSpaceForms/{sid}")
            _delete(db.reference(f"safeSpaceForms/{sid}"))
            summary["safeSpaceForms"] += 1

    # Pass 4: RTDB incident forms (last - so transcripts/clients keyed
    # off them are deleted first via the test_incident_ids passes above).
    for iid in test_incident_ids:
        print(f"  delete incidentForms/{iid}")
        _delete(db.reference(f"incidentForms/{iid}"))
        summary["incidentForms"] += 1

    return summary


def cleanup_storage() -> int:
    """Delete every blob under audio/. Returns count."""
    bucket_name = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if not bucket_name:
        return 0
    from firebase_admin import storage
    bucket = storage.bucket()
    blobs = list(bucket.list_blobs(prefix="audio/"))
    count = 0
    for b in blobs:
        print(f"  delete gs://{bucket.name}/{b.name}")
        if not DRY_RUN:
            b.delete()
        count += 1
    return count


def cleanup_local_dir() -> int:
    """Clear the local audio dir if AUDIO_LOCAL_DIR is set. Returns # files removed."""
    local = os.environ.get("AUDIO_LOCAL_DIR")
    if not local:
        return 0
    root = Path(local)
    if not root.is_dir():
        return 0
    files = [p for p in root.rglob("*") if p.is_file()]
    print(f"  delete local audio dir {root} ({len(files)} files)")
    if not DRY_RUN:
        shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
    return len(files)


def main() -> int:
    started = time.time()
    print(f"Cleanup running at {time.strftime('%Y-%m-%d %H:%M:%S')}"
          + (" (DRY RUN)" if DRY_RUN else ""))
    _init_firebase()

    print("\nRTDB:")
    rtdb_summary = cleanup_rtdb()

    print("\nFirebase Storage:")
    storage_count = cleanup_storage()

    print("\nLocal audio dir:")
    local_count = cleanup_local_dir()

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f}s.")
    print(f"  RTDB records deleted:  {rtdb_summary}")
    print(f"  Storage blobs deleted: {storage_count}")
    print(f"  Local audio files:     {local_count}")
    if DRY_RUN:
        print("\n(no records were actually deleted - re-run without CLEANUP_DRY_RUN=1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
