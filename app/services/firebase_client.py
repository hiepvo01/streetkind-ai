"""
Firebase Realtime Database client.
Writes extracted form data to the existing SKSSIR database.
Database paths and schema metadata are read from config/ files.
"""

import os
import time
import firebase_admin
from firebase_admin import credentials, db
from ..config import get_form_type_config


_app = None


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
    _app = firebase_admin.initialize_app(cred, {"databaseURL": db_url})


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
        "safebaseForms": [
            _summarise_safebase(fid, data) for fid, data in safebase_raw.items()
        ],
    }


# ── Hierarchy helpers ────────────────────────────────────────────────


def get_all_users() -> dict[str, dict]:
    """Return every user node as {uid: profile_dict}."""
    _init_firebase()
    data = db.reference("users").get()
    return data or {}


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
