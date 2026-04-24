"""
Firebase Realtime Database client.
Writes extracted form data to the existing SKSSIR database.
Database paths and schema metadata are read from config/ files.
"""

import os
import time
import firebase_admin
from firebase_admin import credentials, db, storage
from ..config import get_form_type_config


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
        "startTime": data.get("startTime", now),
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
                clients.append(client_data)

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
    """Fetch all transcripts linked to the given incident, ordered by createdDate."""
    _init_firebase()

    incident = db.reference(f"incidentForms/{incident_id}").get() or {}
    transcript_ids = incident.get("transcriptIds", []) or []

    transcripts = []
    for tid in transcript_ids:
        if not isinstance(tid, str):
            continue
        t = db.reference(f"transcripts/{tid}").get()
        if t:
            transcripts.append({"id": tid, **t})

    transcripts.sort(key=lambda t: t.get("createdDate", 0))
    return transcripts


def upload_audio(incident_id: str, transcript_id: str, audio_bytes: bytes, content_type: str) -> str:
    """
    Upload an audio blob to Storage at audio/{incidentId}/{transcriptId}.webm
    and return a long-lived signed URL so the frontend can play it back.
    """
    _init_firebase()

    bucket = storage.bucket()
    ext = "webm" if "webm" in content_type else ("m4a" if "mp4" in content_type else "bin")
    blob = bucket.blob(f"audio/{incident_id}/{transcript_id}.{ext}")
    blob.upload_from_string(audio_bytes, content_type=content_type)
    blob.make_public()
    return blob.public_url


def delete_transcripts_for_incident(incident_id: str) -> None:
    """Remove all transcripts + audio blobs linked to an incident. Used on incident delete."""
    _init_firebase()

    incident = db.reference(f"incidentForms/{incident_id}").get() or {}
    transcript_ids = incident.get("transcriptIds", []) or []

    for tid in transcript_ids:
        if not isinstance(tid, str):
            continue
        db.reference(f"transcripts/{tid}").delete()

    # Best-effort storage cleanup. Don't fail the delete if storage is
    # misconfigured - the DB records are what matters for the audit trail.
    try:
        bucket = storage.bucket()
        for blob in bucket.list_blobs(prefix=f"audio/{incident_id}/"):
            blob.delete()
    except Exception:
        pass
