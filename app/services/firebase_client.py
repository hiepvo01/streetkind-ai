"""
Firebase Realtime Database client.
Writes extracted form data to the existing SKSSIR database.
Database paths and schema metadata are read from config/ files.
"""

import logging
import os
import re
import time
import firebase_admin
from firebase_admin import credentials, db, storage
from ..config import get_form_type_config

logger = logging.getLogger(__name__)

# Push IDs are URL-safe base64: exactly 20 chars starting with '-'.
# Re-validated here (in addition to the route layer) as defense in depth:
# any caller of upload_audio / delete_transcripts_for_incident gets the same guarantee.
_PUSH_ID_RE = re.compile(r"^-[A-Za-z0-9_-]{19}$")


def _assert_push_id(value: str, name: str) -> None:
    if not isinstance(value, str) or not _PUSH_ID_RE.match(value):
        raise ValueError(f"Invalid {name}: {value!r}")


_app = None
_users_cache_data: dict[str, dict] | None = None
_users_cache_fetched_at: float | None = None


def _init_firebase():
    global _app
    if _app is not None:
        return

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    db_url = os.getenv("FIREBASE_DATABASE_URL")

    if not cred_path or not db_url:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_PATH and FIREBASE_DATABASE_URL must be set"
        )

    cred = credentials.Certificate(cred_path)
    init_options = {"databaseURL": db_url}
    bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
    if bucket:
        init_options["storageBucket"] = bucket
    _app = firebase_admin.initialize_app(cred, init_options)


def _push_form(form_type_key: str, data: dict, user_uid: str) -> str:
    """Generic push: looks up firebase_path + schema metadata from config."""
    _init_firebase()

    ft = get_form_type_config(form_type_key)
    if ft is None:
        raise ValueError(f"Unknown form type: {form_type_key}")

    now = int(time.time() * 1000)
    data.update({
        "createdBy": user_uid,
        "createdDate": now,
        "startTime": data.get("startTime") or now,
        "schemaName": ft["schema_name"],
        "schemaVersion": ft["schema_version"],
        "editedBy": "",
        "editedDate": "",
    })

    if ft.get("default_status"):
        data.setdefault("status", ft["default_status"])

    # Incident-specific defaults
    if form_type_key == "incident":
        data.setdefault("endTime", now)
        data.setdefault("clientList", [])
        data.setdefault("teamMembersInvolved", [])

    # SafeBase-specific defaults
    if form_type_key == "safebase":
        data["editedDate"] = 0

    ref = db.reference(ft["firebase_path"]).push(data)
    return ref.key


def push_incident_form(data: dict, user_uid: str, status: str = "completed") -> str:
    """Push incident + clients to Firebase matching SKSSIR flow."""
    _init_firebase()

    incident_data = data.get("incident", data)
    clients_data = data.get("clients", [])

    ft = get_form_type_config("incident")
    now = int(time.time() * 1000)

    # Write incident
    incident_data.update({
        "createdBy": user_uid,
        "createdDate": now,
        "startTime": incident_data.get("startTime", now),
        "endTime": incident_data.get("endTime", now),
        "schemaName": ft["schema_name"],
        "schemaVersion": ft["schema_version"],
        "status": status,
        "editedBy": "",
        "editedDate": "",
        "clientList": [],
        "teamMembersInvolved": [],
    })

    incident_ref = db.reference(ft["firebase_path"]).push(incident_data)
    incident_id = incident_ref.key

    # Write each client
    client_ids = []
    for client_data in clients_data:
        client_data.update({
            "createdBy": user_uid,
            "createdDate": now,
            "incidentId": incident_id,
            "site": incident_data.get("site", ""),
            "schemaName": "client",
            "schemaVersion": 1,
            "editedBy": "",
            "editedDate": "",
        })
        client_ref = db.reference("clients").push(client_data)
        client_ids.append(client_ref.key)

    # Update incident's clientList
    if client_ids:
        db.reference(f"{ft['firebase_path']}/{incident_id}/clientList").set(client_ids)

    return incident_id


def push_safebase_form(data: dict, user_uid: str) -> str:
    return _push_form("safebase", data, user_uid)


def get_user_profile(uid: str) -> dict | None:
    """Fetch user profile from users/{uid}."""
    _init_firebase()
    return db.reference(f"users/{uid}").get()


def get_dashboard_stats() -> dict:
    """Fetch cached dashboard statistics from Firebase."""
    _init_firebase()
    ref = db.reference("dashboardInfoStats")
    data = ref.get()
    return data or {}


# ── Form queries ─────────────────────────────────────────────────────


def get_forms_by_user(uid: str) -> dict:
    """
    Return incidentForms and safeSpaceForms created by the given user.
    Uses orderByChild("createdBy") so RTDB .indexOn is recommended.
    """
    _init_firebase()

    incidents_raw = (
        db.reference("incidentForms")
        .order_by_child("createdBy")
        .equal_to(uid)
        .get()
    ) or {}

    safebase_raw = (
        db.reference("safeSpaceForms")
        .order_by_child("createdBy")
        .equal_to(uid)
        .get()
    ) or {}

    def _summarise_incident(form_id: str, d: dict) -> dict:
        return {
            "id": form_id,
            "site": d.get("site", ""),
            "incidentDescription": d.get("incidentDescription", ""),
            "status": d.get("status", ""),
            "createdDate": d.get("createdDate"),
            "teamLeaderName": d.get("teamLeaderName", ""),
        }

    def _summarise_safebase(form_id: str, d: dict) -> dict:
        return {
            "id": form_id,
            "site": d.get("site", ""),
            "createdDate": d.get("createdDate"),
            "startTime": d.get("startTime"),
        }

    return {
        "incidents": [
            _summarise_incident(fid, data) for fid, data in incidents_raw.items()
        ],
        # RTDB uses legacy node name "safeSpaceForms"; API uses "safebaseForms"
        # to align with the app's form_type key ("safebase") and UI wording.
        "safebaseForms": [
            _summarise_safebase(fid, data) for fid, data in safebase_raw.items()
        ],
    }


def get_safebase_full(form_id: str) -> dict | None:
    """Fetch a single SafeBase form from Firebase."""
    _init_firebase()
    safebase = db.reference(f"safeSpaceForms/{form_id}").get()
    if safebase is None:
        return None
    return safebase


# ── Single-incident CRUD ──────────────────────────────────────────────


def _normalise_tk_to_sk(incident: dict) -> dict:
    """
    Legacy incidents may have encounteredBy.tkAmbassador. Translate to
    skAmbassador so the frontend (which only knows the new key) displays
    the value correctly and round-trips it safely on save.
    """
    encountered = incident.get("encounteredBy")
    if isinstance(encountered, dict) and "tkAmbassador" in encountered:
        # Only migrate when the new key is absent to avoid clobbering an
        # already-migrated value.
        if "skAmbassador" not in encountered:
            encountered["skAmbassador"] = encountered.pop("tkAmbassador")
        else:
            # Both present - prefer the new key and drop the legacy one.
            encountered.pop("tkAmbassador", None)
        incident["encounteredBy"] = encountered
    return incident


def _normalise_legacy_client(client: dict) -> dict:
    """
    Legacy client records may have:
    - `safeBase` blob (lower-case b) instead of `safeSpace` - 67 records
      observed in production. Fold into safeSpace where missing.

    Mutates and returns the dict.
    """
    if not isinstance(client, dict):
        return client

    legacy_safebase = client.get("safeBase")
    safe_space = client.get("safeSpace")
    if isinstance(legacy_safebase, dict):
        if not isinstance(safe_space, dict) or not any(safe_space.values()):
            # Lift legacy blob into the modern field
            client["safeSpace"] = legacy_safebase
        client.pop("safeBase", None)
    return client


def get_incident_full(form_id: str) -> dict | None:
    """Fetch a single incident and its associated clients from Firebase."""
    _init_firebase()
    incident = db.reference(f"incidentForms/{form_id}").get()
    if incident is None:
        return None

    incident = _normalise_tk_to_sk(incident)

    client_ids = incident.get("clientList", [])
    clients = []
    for cid in client_ids:
        if isinstance(cid, str):
            client_data = db.reference(f"clients/{cid}").get()
            if client_data:
                clients.append(_normalise_legacy_client(client_data))

    return {"incident": incident, "clients": clients}


def update_incident(form_id: str, data: dict, editor_uid: str, status: str = "completed") -> None:
    """
    Update an existing incident and replace its clients in Firebase.

    Concurrency note: this is a non-atomic read → delete → write flow. If two
    updates happen concurrently, they can interleave and temporarily delete or
    orphan client records. The last write to incidentForms/{form_id} wins.
    """
    _init_firebase()

    incident_data = data.get("incident", data)
    clients_data = data.get("clients", [])
    now = int(time.time() * 1000)

    incident_data["editedBy"] = editor_uid
    incident_data["editedDate"] = now
    incident_data["status"] = status

    # Delete old clients
    old_incident = db.reference(f"incidentForms/{form_id}").get() or {}
    for old_cid in old_incident.get("clientList", []):
        if isinstance(old_cid, str):
            db.reference(f"clients/{old_cid}").delete()

    # Write new clients
    client_ids = []
    for client in clients_data:
        client.update({
            "createdBy": incident_data.get("createdBy", editor_uid),
            "incidentId": form_id,
            "site": incident_data.get("site", ""),
            "schemaName": "client",
            "schemaVersion": 1,
            "editedBy": editor_uid,
            "editedDate": now,
        })
        client_ref = db.reference("clients").push(client)
        client_ids.append(client_ref.key)

    incident_data["clientList"] = client_ids
    db.reference(f"incidentForms/{form_id}").update(incident_data)


def delete_incident(form_id: str) -> None:
    """Delete an incident and its associated clients + transcripts from Firebase."""
    _init_firebase()

    incident = db.reference(f"incidentForms/{form_id}").get()
    if incident:
        for cid in incident.get("clientList", []):
            if isinstance(cid, str):
                db.reference(f"clients/{cid}").delete()

    delete_transcripts_for_incident(form_id)
    db.reference(f"incidentForms/{form_id}").delete()


# ── Hierarchy helpers ────────────────────────────────────────────────


def get_all_users() -> dict[str, dict]:
    """
    Return every user node as {uid: profile_dict}.

    Cached for a short TTL to avoid downloading the full users tree on every
    hierarchy-protected request.
    """
    _init_firebase()
    global _users_cache_data, _users_cache_fetched_at

    ttl_s = int(os.getenv("USERS_CACHE_TTL_SECONDS", "30"))
    if ttl_s > 0 and _users_cache_data is not None and _users_cache_fetched_at is not None:
        if (time.time() - _users_cache_fetched_at) < ttl_s:
            return _users_cache_data

    data = db.reference("users").get() or {}

    if ttl_s > 0:
        _users_cache_data = data
        _users_cache_fetched_at = time.time()

    return data


def get_direct_reports(uid: str, all_users: dict[str, dict] | None = None) -> list[dict]:
    """
    Return users whose createdBy == uid (i.e. the people this user created).
    Each item includes the subordinate's uid for convenience.
    """
    if all_users is None:
        all_users = get_all_users()

    reports = []
    for user_uid, profile in all_users.items():
        if profile.get("createdBy") == uid:
            reports.append({"uid": user_uid, **profile})
    return reports


def is_ancestor(caller_uid: str, target_uid: str, all_users: dict[str, dict] | None = None) -> bool:
    """
    Walk the createdBy chain upward from target_uid.
    Returns True if caller_uid is found in the chain (direct parent,
    grandparent, etc.), meaning the caller has access to target's data.
    Also returns True if caller_uid == target_uid (viewing own data).
    """
    if caller_uid == target_uid:
        return True

    if all_users is None:
        all_users = get_all_users()

    visited = set()
    current = target_uid
    while current in all_users:
        if current in visited:
            break
        visited.add(current)
        parent = all_users[current].get("createdBy")
        if not parent:
            break
        if parent == caller_uid:
            return True
        current = parent

    return False


# ── Transcripts + audio ──────────────────────────────────────────────


def push_transcript(
    incident_id: str,
    transcript_data: dict,
    user_uid: str,
) -> str:
    """
    Store a transcript under transcripts/{id} and append its id to the incident's
    transcriptIds array. Called after the incident has been submitted so we can
    link by incidentId.
    """
    _init_firebase()

    now = int(time.time() * 1000)
    transcript_data = {
        **transcript_data,
        "incidentId": incident_id,
        "createdBy": user_uid,
        "createdDate": now,
    }

    ref = db.reference("transcripts").push(transcript_data)
    transcript_id = ref.key

    # Append to incident's transcriptIds. Use a transaction to avoid clobbering
    # concurrent appends.
    def _append(current):
        current = current or []
        if transcript_id not in current:
            current.append(transcript_id)
        return current

    db.reference(f"incidentForms/{incident_id}/transcriptIds").transaction(_append)

    return transcript_id


def get_transcripts_for_incident(incident_id: str) -> list[dict]:
    """
    Fetch all transcripts linked to the given incident, ordered by createdDate.

    For each transcript with an `audioPath`, attach a freshly-signed `audioUrl`
    so the frontend can play it back. Existing legacy records that already have
    an `audioUrl` stored (from the old public-URL scheme) are returned as-is.
    """
    _init_firebase()

    incident = db.reference(f"incidentForms/{incident_id}").get() or {}
    transcript_ids = incident.get("transcriptIds", []) or []

    transcripts = []
    for tid in transcript_ids:
        if not isinstance(tid, str):
            continue
        t = db.reference(f"transcripts/{tid}").get()
        if not t:
            continue

        # Decorate with a fresh signed URL if this is a new-style record.
        audio_path = t.get("audioPath")
        if audio_path:
            t = {**t, "audioUrl": signed_audio_url(audio_path) or ""}

        transcripts.append({"id": tid, **t})

    transcripts.sort(key=lambda t: t.get("createdDate", 0))
    return transcripts


_EXT_BY_CONTENT_TYPE = [
    ("webm", "webm"),
    ("mp4", "m4a"),
    ("m4a", "m4a"),
    ("aac", "m4a"),
    ("ogg", "ogg"),
    ("mpeg", "mp3"),
    ("mp3", "mp3"),
]


def _audio_ext_for(content_type: str) -> str:
    ct = (content_type or "").lower()
    for needle, ext in _EXT_BY_CONTENT_TYPE:
        if needle in ct:
            return ext
    return "bin"


def _local_audio_root() -> str | None:
    """Return the local filesystem dir for audio storage, or None if disabled.
    When AUDIO_LOCAL_DIR is set we keep blobs on local disk instead of going
    to Firebase Storage. Useful for offline / dev work where the team doesn't
    want test recordings polluting the shared bucket.
    """
    return os.getenv("AUDIO_LOCAL_DIR")


def upload_audio(incident_id: str, transcript_id: str, audio_bytes: bytes, content_type: str) -> str:
    """
    Upload an audio blob and return its location key. The key has the shape
    `audio/{incidentId}/{transcriptId}.{ext}` regardless of the storage backend
    so the rest of the pipeline (signed_audio_url, delete cascade) is uniform.

    Backend selection:
    - If AUDIO_LOCAL_DIR is set, write to {AUDIO_LOCAL_DIR}/audio/{i}/{t}.ext
      on local disk. No Firebase Storage call.
    - Otherwise, upload to Firebase Storage at the same relative path,
      private (no make_public). Playback goes via short-lived signed URLs
      generated at read time by signed_audio_url().

    IDs are re-validated against the push-ID regex even though the route layer
    already checks them - defense in depth so future callers can't accidentally
    introduce a path-traversal hole.
    """
    _assert_push_id(incident_id, "incident_id")
    _assert_push_id(transcript_id, "transcript_id")

    ext = _audio_ext_for(content_type)
    blob_path = f"audio/{incident_id}/{transcript_id}.{ext}"

    local_root = _local_audio_root()
    if local_root:
        from pathlib import Path
        target = Path(local_root) / blob_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(audio_bytes)
        logger.info("Wrote local audio %s (%d bytes)", target, len(audio_bytes))
        return blob_path

    _init_firebase()
    bucket = storage.bucket()
    blob = bucket.blob(blob_path)
    blob.upload_from_string(audio_bytes, content_type=content_type)
    # No make_public() - audio is private, served via signed URLs on read.
    return blob_path


AUDIO_SIGNED_URL_TTL_SECONDS = int(os.getenv("AUDIO_SIGNED_URL_TTL_SECONDS", "3600"))


def signed_audio_url(blob_path: str, ttl_seconds: int | None = None) -> str | None:
    """
    Return a URL the frontend can use to play back a stored audio blob.

    - In Firebase Storage mode: a short-lived v4 signed URL.
    - In local-disk mode (AUDIO_LOCAL_DIR set): a same-origin path served by
      the FastAPI app's static-files mount at /local-audio/...

    Returns None if the blob is missing / Storage is unreachable.
    Callers must already have authorised access to the containing incident -
    this function enforces NOTHING; it only signs / formats URLs.
    """
    if not blob_path or not isinstance(blob_path, str):
        return None
    # Defence in depth: blob_path should always start with 'audio/' and
    # contain only characters we'd expect (no ../, no absolute paths).
    if not blob_path.startswith("audio/") or ".." in blob_path:
        logger.warning("Refusing to sign suspicious blob_path: %r", blob_path)
        return None

    local_root = _local_audio_root()
    if local_root:
        from pathlib import Path
        if (Path(local_root) / blob_path).is_file():
            # Browser will hit FastAPI's StaticFiles mount; same-origin in
            # local dev so no auth header / CORS issues.
            return f"/local-audio/{blob_path}"
        return None

    try:
        _init_firebase()
        from datetime import timedelta
        bucket = storage.bucket()
        blob = bucket.blob(blob_path)
        ttl = ttl_seconds if ttl_seconds is not None else AUDIO_SIGNED_URL_TTL_SECONDS
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=ttl),
            method="GET",
        )
    except Exception as e:
        logger.warning("Failed to sign URL for %s: %s", blob_path, e)
        return None


def delete_audio_blob(incident_id: str, transcript_id: str) -> bool:
    """
    Best-effort deletion of the audio blob(s) for a single transcript across
    whichever backend is active.
    Returns True when the operation succeeded (or no blob existed), False on error.
    Used for compensation when an audio upload partially fails.
    """
    try:
        _assert_push_id(incident_id, "incident_id")
        _assert_push_id(transcript_id, "transcript_id")

        local_root = _local_audio_root()
        if local_root:
            from pathlib import Path
            target_dir = Path(local_root) / "audio" / incident_id
            if target_dir.is_dir():
                for f in target_dir.iterdir():
                    if f.is_file() and f.stem == transcript_id:
                        f.unlink()
            return True

        bucket = storage.bucket()
        # The extension is content-type dependent, so delete anything matching
        # the transcript-id prefix under this incident.
        for blob in bucket.list_blobs(prefix=f"audio/{incident_id}/"):
            if blob.name.startswith(f"audio/{incident_id}/{transcript_id}."):
                blob.delete()
        return True
    except Exception as e:
        logger.warning(
            "Failed to delete audio blob for transcript=%s incident=%s: %s",
            transcript_id, incident_id, e,
        )
        return False


def delete_transcripts_for_incident(incident_id: str) -> dict:
    """
    Remove all transcripts + audio blobs linked to an incident.

    Order: Storage first, then RTDB. This way the RTDB transcriptIds index is
    still valid while we enumerate Storage, and RTDB pointers survive a Storage
    failure so the blobs can be retried rather than orphaned.

    Returns a summary dict so callers (and tests) can see whether cleanup was
    complete. Does not raise - individual failures are logged and aggregated.
    """
    _init_firebase()

    summary = {
        "storage_blobs_deleted": 0,
        "storage_blobs_failed": 0,
        "transcripts_deleted": 0,
        "transcripts_failed": 0,
        "storage_list_error": None,
    }

    incident = db.reference(f"incidentForms/{incident_id}").get() or {}
    transcript_ids = [t for t in (incident.get("transcriptIds") or []) if isinstance(t, str)]

    # 1. Storage cleanup first, while RTDB still has the pointers for recovery.
    local_root = _local_audio_root()
    if local_root:
        try:
            from pathlib import Path
            import shutil
            target_dir = Path(local_root) / "audio" / incident_id
            if target_dir.is_dir():
                file_count = sum(1 for f in target_dir.iterdir() if f.is_file())
                shutil.rmtree(target_dir)
                summary["storage_blobs_deleted"] = file_count
        except Exception as e:
            summary["storage_list_error"] = f"local: {e}"
            logger.warning("Local audio cleanup failed for incident=%s: %s", incident_id, e)
    else:
        try:
            bucket = storage.bucket()
            # List once, track what we tried to delete.
            blobs = list(bucket.list_blobs(prefix=f"audio/{incident_id}/"))
            for blob in blobs:
                try:
                    blob.delete()
                    summary["storage_blobs_deleted"] += 1
                except Exception as e:
                    summary["storage_blobs_failed"] += 1
                    logger.warning(
                        "Failed to delete storage blob %s for incident=%s: %s",
                        blob.name, incident_id, e,
                    )
        except Exception as e:
            # No storageBucket configured, or the enumeration itself failed.
            # Record it so callers / audits can see the gap. Don't abort RTDB cleanup.
            summary["storage_list_error"] = str(e)
            logger.info(
                "Storage cleanup skipped for incident=%s: %s", incident_id, e,
            )

    # 2. RTDB transcript records.
    for tid in transcript_ids:
        try:
            db.reference(f"transcripts/{tid}").delete()
            summary["transcripts_deleted"] += 1
        except Exception as e:
            summary["transcripts_failed"] += 1
            logger.warning(
                "Failed to delete transcripts/%s for incident=%s: %s",
                tid, incident_id, e,
            )

    if summary["storage_blobs_failed"] or summary["transcripts_failed"]:
        logger.error(
            "Partial cleanup for incident=%s: %s", incident_id, summary,
        )

    return summary
