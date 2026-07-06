"""
Shared read-only Firebase connection helper for the tools/ scripts.

Credentials are NEVER hardcoded or committed - every script in this
directory reads the service-account key path and database URL from
environment variables. Set these before running anything here:

    export TK_FOUNDATION_CRED=/path/to/tk-foundation-firebase-adminsdk-*.json
    export TK_FOUNDATION_DB_URL=https://tk-foundation.firebaseio.com

    export STREETKIND_DEV_CRED=/path/to/streetkind-app-dev-firebase-adminsdk-*.json
    export STREETKIND_DEV_DB_URL=https://streetkind-app-dev-default-rtdb.firebaseio.com

tk-foundation is the legacy/production SKSSIR database (real historical
incident data - handle with care, see README.md). streetkind-app-dev is
this app's own development database.
"""

import os
import sys

import firebase_admin
from firebase_admin import credentials, db

_initialized_apps = {}


def _connect(cred_env, url_env, app_name):
    if app_name in _initialized_apps:
        return _initialized_apps[app_name]

    cred_path = os.environ.get(cred_env)
    db_url = os.environ.get(url_env)
    if not cred_path or not db_url:
        sys.exit(
            f"ERROR: set {cred_env} and {url_env} before running this script.\n"
            f"See tools/README.md for setup."
        )
    if not os.path.isfile(cred_path):
        sys.exit(f"ERROR: {cred_env}={cred_path!r} does not exist.")

    cred = credentials.Certificate(cred_path)
    app = firebase_admin.initialize_app(cred, {"databaseURL": db_url}, name=app_name)
    _initialized_apps[app_name] = app
    return app


def connect_tk_foundation():
    """Legacy/production database (historical incidentForms/clients/safeSpaceForms)."""
    return _connect("TK_FOUNDATION_CRED", "TK_FOUNDATION_DB_URL", "tk_foundation")


def connect_streetkind_dev():
    """This app's own dev database (transcripts/incidentForms for the voice pipeline)."""
    return _connect("STREETKIND_DEV_CRED", "STREETKIND_DEV_DB_URL", "streetkind_dev")


def ref(path, app):
    return db.reference(path, app=app)
