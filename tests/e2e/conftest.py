"""
Shared fixtures and helpers for Playwright E2E tests.

Requires both servers running:
  - Backend  (FastAPI)  on http://localhost:5000
  - Frontend (React)    on http://localhost:3000
"""

import pytest
import firebase_admin
from firebase_admin import credentials, db as firebase_db_module

CRED_PATH = "streetkind-app-dev-firebase-adminsdk-fbsvc-e556e5bb1c.json"
DB_URL = "https://streetkind-app-dev-default-rtdb.firebaseio.com"
BASE_URL = "http://localhost:3000"

DEMO_VOLUNTEER = {"email": "volunteer@streetkind.demo", "password": "streetkind123"}
DEMO_ADMIN = {"email": "admin@streetkind.demo", "password": "streetkind123"}
DEMO_LEADER = {"email": "leader@streetkind.demo", "password": "streetkind123"}


# ---------------------------------------------------------------------------
# Firebase fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def firebase_app():
    """Initialise the Firebase Admin SDK once per test session."""
    cred = credentials.Certificate(CRED_PATH)
    app = firebase_admin.initialize_app(cred, {"databaseURL": DB_URL})
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
