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


def push_incident_form(data: dict, user_uid: str) -> str:
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
        "status": "completed",
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
