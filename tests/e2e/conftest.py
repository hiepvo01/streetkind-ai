"""
Shared fixtures and helpers for Playwright E2E tests.

Requires both servers running:
  - Backend  (FastAPI)  on http://localhost:8000
  - Frontend (React)    on http://localhost:3000
"""

import os

import pytest
import requests
import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, db as firebase_db_module

DEFAULT_CRED_PATH = "firebase-service-account.json"
CRED_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", DEFAULT_CRED_PATH)
DB_URL = "https://streetkind-app-dev-default-rtdb.firebaseio.com"
BASE_URL = "http://localhost:3000"
# API base URL - override with API_BASE_URL env var to run tests against prod
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

DEMO_VOLUNTEER = {"email": "volunteer@streetkind.demo", "password": "streetkind123"}
DEMO_ADMIN = {"email": "admin@streetkind.demo", "password": "streetkind123"}
DEMO_LEADER = {"email": "leader@streetkind.demo", "password": "streetkind123"}

# Firebase Web API key - PUBLIC project identifier, not a secret.
# See https://firebase.google.com/docs/projects/api-keys.
FIREBASE_WEB_API_KEY = os.environ.get(
    "FIREBASE_WEB_API_KEY", "AIzaSyD6q7A5-g26ma7Dv2w8PLa4e0FdM_D3eVQ",
)
# Backwards-compat alias (older tests imported this name).
_DEFAULT_FIREBASE_WEB_API_KEY = FIREBASE_WEB_API_KEY


def get_firebase_id_token_for_uid(uid: str = "e2e-test-user") -> str:
    """
    Mint a Firebase ID token for protected API tests.

    Uses Admin SDK custom token + Identity Toolkit signInWithCustomToken.
    Requires firebase_app to be initialised (use fb_db / firebase_app fixture).
    """
    custom = firebase_auth.create_custom_token(uid)
    token_str = custom.decode("utf-8") if isinstance(custom, bytes) else custom
    api_key = os.environ.get("FIREBASE_WEB_API_KEY", _DEFAULT_FIREBASE_WEB_API_KEY)
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
    resp = requests.post(
        url,
        json={"token": token_str, "returnSecureToken": True},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["idToken"]


# ---------------------------------------------------------------------------
# Firebase fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def firebase_app():
    """Initialise the Firebase Admin SDK once per test session."""
    cred = credentials.Certificate(CRED_PATH)
    init_options = {"databaseURL": DB_URL}
    bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if bucket:
        init_options["storageBucket"] = bucket
    app = firebase_admin.initialize_app(cred, init_options)
    yield app
    firebase_admin.delete_app(app)


@pytest.fixture
def fb_db(firebase_app):
    """Return the firebase_admin.db module (already initialised)."""
    return firebase_db_module


@pytest.fixture
def cleanup_keys(firebase_app):
    """
    Collect (path, key) tuples during a test.
    All collected keys are deleted from Firebase during teardown.
    """
    keys: list[tuple[str, str]] = []
    yield keys
    for path, key in keys:
        firebase_db_module.reference(f"{path}/{key}").delete()


# ---------------------------------------------------------------------------
# URL fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


# ---------------------------------------------------------------------------
# Login helper (not a fixture – call explicitly)
# ---------------------------------------------------------------------------

def do_login(page, email=None, password=None, base_url=BASE_URL):
    """
    Navigate to the app and log in via the UI.

    Semantic UI Form.Input renders <input> inside a <div class="field">.
    We target by placeholder text since there is no explicit name attribute.
    """
    page.goto(base_url)
    page.wait_for_selector('input[placeholder="Email Address"]', timeout=10000)
    page.fill('input[placeholder="Email Address"]', email or DEMO_VOLUNTEER["email"])
    page.fill('input[placeholder="Password"]', password or DEMO_VOLUNTEER["password"])
    page.click('button:has-text("Login")')
    # After successful login the voice input screen appears
    page.wait_for_selector('text=Tap to start speaking', timeout=15000)
