# StreetKind AI - Voice-to-Form Assistant

A voice-powered assistant that lets StreetKind volunteers speak naturally about incidents and SafeBase activity, then automatically fills in the required forms using AI-structured output. Built to integrate with the existing SKSSIR system.

**Live:**
- Frontend: https://streetkind-app-dev.web.app
- Backend API: https://46-62-215-38.sslip.io

For the full deployment playbook (Coolify, Firebase Hosting, signed-URL audio, redeploy steps, audit history) see [DEPLOYMENT.md](DEPLOYMENT.md).

## How It Works

```
Volunteer speaks → Web Speech API transcribes → Claude AI extracts structured data
    → Form pre-filled (incident + clients or SafeBase) → Volunteer reviews → Submit to Firebase
    → Transcript + audio (signed URL) linked to the saved incident for audit + replay
```

## Features

- **Voice input**. Tap the microphone, describe what happened, AI fills the form. Web Speech API for real-time speech-to-text plus MediaRecorder for the audio blob.
- **Multi-segment recordings**. Volunteers can stop and start a new recording within the same incident. Each segment becomes its own transcript record with its own audio file and timestamp. The IncidentEditModal renders all segments side by side with playback. Each completed segment has a "Discard" button so accidental recordings can be cleared before submit.
- **Recording preview before submit**. After hitting stop, the volunteer sees a `<audio>` player for the just-recorded segment so they can verify it captured correctly *before* the form is saved.
- **Transcript text + audio playback in My Incidents and Monitor**. The IncidentEditModal shows every transcript that was attached to an incident (with its timestamp, duration, audio player, transcript text, and AI extraction metadata).
- **AI-driven structured form fill**. Claude (via Microsoft Foundry, tool_use) extracts gender, age group, intoxication signs, transport used, basic aid, etc. from natural Aussie volunteer phrasing. Inference is tuned by `config/prompts/incident.txt`.
- **Magic-generate narrative**. Click the wand on the Incident form to ask Claude to draft an `incidentDescription` and `incidentOutcome` from your structured data and quick note. Per-user rate limited.
- **Use-my-location**. Pre-fills the address from device GPS via a backend reverse-geocode proxy (cached + rate limited).
- **Incident Report form**. Matches SKSSIR exactly: 11 encountered-by checkboxes, 6 other services, embedded client forms, quick note, description, outcome, major-incident flag.
- **Client form (5-tab wizard)**. Client Info, Basic Support, Health Support, Risk Minimisation, Services Referred. 50+ fields matching SKSSIR.
- **SafeBase form**. Gender x age headcount grid + assistance counters + start time.
- **Dashboard**. 11 live impact statistics from Firebase RTDB.
- **My Incidents / Monitor**. Volunteers see their own reports; team leaders / admin see their hierarchy's reports, with edit + delete cascading to clients, transcripts, and audio blobs.
- **Firebase Auth**. Email/password, role-based access (Admin / Team Leader / Team Member). createdBy is always the verified token UID, never client-supplied.
- **Responsive**. Desktop (1920px), iPad (768px), Mobile (375px).
- **Config-driven**. Sites, prompts, field options, app name, default site editable via JSON files in `config/` with no code changes.

See [FEATURES.md](FEATURES.md) for the full feature list and [DATA_MODEL.md](DATA_MODEL.md) for how incidents, transcripts, and audio blobs relate.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python), Docker on Coolify |
| Frontend | React 18.2 + Semantic UI React 2.1.4, deployed to Firebase Hosting |
| AI | Claude via Microsoft Foundry (Anthropic Messages API, tool_use structured output) |
| Auth | Firebase Authentication (ID-token verified on backend) |
| Database | Firebase Realtime Database (existing SKSSIR) |
| Audio storage | Firebase Storage (private blobs + v4 signed URLs) |
| Speech | Web Speech API (Chrome/Edge) + MediaRecorder for audio capture |
| Testing | Playwright + pytest (36 E2E tests: 32 always-on + 4 AI-extraction gated) |

## Getting Started

### Prerequisites
- Conda (Anaconda or Miniconda)
- Node.js 18+
- Microsoft Foundry credentials for Claude ([Azure AI Foundry](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-claude)): API key plus base URL or resource name
- Firebase service account key (from `streetkind-app-dev` project)

### Installation

```bash
cd streetkind-ai

# Backend
conda env create -f environment.yml
conda activate streetkind-ai

# Configure
cp .env.example .env
# Edit .env: add ANTHROPIC_FOUNDRY_API_KEY and ANTHROPIC_FOUNDRY_BASE_URL
#   (or ANTHROPIC_FOUNDRY_RESOURCE), plus Firebase paths if using submit

# Frontend
cd frontend && npm install && cd ..
```

### Running

```bash
# Terminal 1: Backend (port 8000)
conda activate streetkind-ai
python run.py

# Terminal 2: Frontend (port 3000)
cd frontend && npm start
```

Open http://localhost:3000 in **Chrome** (required for Web Speech API).

FastAPI docs: http://localhost:8000/docs

### Demo Accounts

| Email | Password | Role |
|-------|----------|------|
| admin@streetkind.demo | streetkind123 | Administrator |
| leader@streetkind.demo | streetkind123 | Team Leader |
| volunteer@streetkind.demo | streetkind123 | Team Member |

### Running Tests

```bash
# Both servers must be running first
conda activate streetkind-ai

# Required env for Firebase-verified E2E tests:
#   FIREBASE_SERVICE_ACCOUNT_PATH   path to service account JSON
#   FIREBASE_STORAGE_BUCKET         e.g. streetkind-app-dev.firebasestorage.app
# Optional:
#   API_BASE_URL                    point at prod instead of localhost
#   RUN_AI_TESTS=1                  include Foundry-backed /api/extract tests

pytest tests/e2e/ -v              # headless
pytest tests/e2e/ -v --headed     # watch the browser
```

**Suite: 36 tests collected, 32 always-on pass + 4 AI-gated (skipped by default).** Covers login, full incident CRUD plus access control, SafeBase submit, dashboard, transcript lifecycle, audio upload + signed URLs + cleanup, security (cross-user and cross-incident denial, path-traversal rejection, magic-byte validation), concurrency, and responsive layouts. Test data auto-cleaned after each run.

There's also a static field-binding integrity test (`tests/test_field_binding_integrity.py`, 45 checks, no servers needed) and a UI form-binding Playwright test (`tests/e2e/test_ui_form_binding.py`) that catch the class of bug where the frontend reads a typo'd field name vs the schema.

### Wiping test data

```bash
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/service-account.json \
FIREBASE_STORAGE_BUCKET=streetkind-app-dev.firebasestorage.app \
python scripts/cleanup_test_data.py
```

Removes every record whose createdBy starts with `e2e-` or whose description / leader / first name matches a known test marker (FORM_BINDING_TEST, UI flow test, E2E test, CRUD test, PROD E2E, LOCAL_AUDIO_PROBE, etc), plus orphaned clients tied to deleted test incidents, plus all audio blobs in Firebase Storage and `AUDIO_LOCAL_DIR`. Use `CLEANUP_DRY_RUN=1` to preview without deleting.

## Project Structure

```
streetkind-ai/
  app/                              # FastAPI backend
    auth.py                         # Firebase ID token verification dependency
    config.py                       # Config loader (reads config/ folder)
    routes.py                       # API endpoints (config, extract, submit, forms CRUD, transcripts, audio, monitor)
    schemas/                        # Pydantic models (incident, client, safebase, combined, transcript)
    services/
      ai_extractor.py               # Claude tool_use structured output
      firebase_client.py            # Firebase RTDB read/write + Storage signed URLs
  config/                           # Editable by non-technical users
    app.json                        # App name, AI model, speech settings
    sites.json                      # Operating sites
    form_types.json                 # Form definitions
    prompts/                        # AI prompt templates
    fields/                         # Per-form field options (shared, incident, safebase, client)
  frontend/                         # React 18.2 + Semantic UI React
    src/
      firebase.js                   # Firebase client SDK config
      context/AuthContext.js         # Auth state provider
      components/
        Login/                      # Login page (matches SKSSIR design)
        Dashboard/                  # 11 impact stat cards
        MenuBar/                    # Top nav with logo + user name
        NavSidebar/                 # Push sidebar (My Incidents for all; Monitor for admin/team leader)
        MyIncidents/                # Own incident + SafeBase forms list
        Monitor/                    # Hierarchy drill-down + subordinate forms
        FormSelector/               # Form type + site selection
        VoiceInput/                 # Mic button + transcript + extract
        FormPreview/                # Routes to actual form views
        forms/
          shared/                   # CheckboxGroup, RadioGroup, NumberInput
          IncidentForm/             # Incident form + encountered by + other services
          ClientForm/               # 5-tab wizard (info, support, health, risk, services)
          SafeBaseForm/             # People count grid + assistance counters
  tests/
    e2e/                            # Playwright E2E tests (32 tests + 4 AI-gated)
    test_extraction.py              # AI extraction unit tests
  scripts/
    cleanup_test_data.py            # Wipe test fixtures from RTDB + Storage + AUDIO_LOCAL_DIR
  Dockerfile                        # Backend container (strips test deps for small image)
  .dockerignore                     # Excludes frontend, tests, service-account JSON
  firebase.json                     # Firebase Hosting + rules pointers
  .firebaserc                       # Default project: streetkind-app-dev
  database.rules.json               # RTDB security rules (Admin SDK only)
  storage.rules                     # Storage rules (deny all; signed URLs bypass)
  DEPLOYMENT.md                     # Deployment playbook
  DATA_MODEL.md                     # incident <-> transcript <-> audio relationships, keys, paths
```

## Configuration

All config in `config/` as plain JSON — no code changes needed:

| File | Controls |
|------|----------|
| `sites.json` | Add/remove operating sites |
| `form_types.json` | Form labels, icons, Firebase paths |
| `app.json` | App name, AI model, speech language |
| `prompts/*.txt` | How AI interprets voice descriptions |
| `fields/*.json` | Checkbox/radio options per form |

## Auth Migration Note

The database was migrated from the old `sk-foundation` Firebase project. The 66 original user records exist in the RTDB but their Firebase Auth credentials were **not migrated**. Currently only 3 demo accounts can login. To import the original users:

```bash
# Requires Firebase CLI access to the old project
firebase auth:export users.json --project sk-foundation
firebase auth:import users.json --project streetkind-app-dev
```

## API Endpoints

All protected endpoints require `Authorization: Bearer <Firebase ID token>`. `createdBy` is always set from the verified token UID — clients never send it.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/config` | GET | — | UI configuration (sites, form types, field options) |
| `/api/dashboard` | GET | — | 11 dashboard impact statistics |
| `/api/health` | GET | — | Health check |
| `/api/extract` | POST | — | Voice transcript -> AI structured form data |
| `/api/submit` | POST | required | Submit incident or SafeBase form |
| `/api/me` | GET | required | Authenticated user profile |
| `/api/team/{uid}` | GET | required + hierarchy | Direct reports grouped by role |
| `/api/monitor/{uid}/forms` | GET | required + hierarchy | Forms created by `{uid}` |
| `/api/forms/incident/{id}` | GET | required + hierarchy | Full incident + clients |
| `/api/forms/incident/{id}` | PUT | required + hierarchy | Update incident + replace clients |
| `/api/forms/incident/{id}` | DELETE | required + hierarchy | Delete incident, clients, transcripts, audio blobs |
| `/api/forms/incident/{id}/transcripts` | GET | required + hierarchy | List transcripts (each gets fresh signed `audioUrl`) |
| `/api/forms/incident/{id}/transcripts` | POST | required + hierarchy | Create transcript record |
| `/api/forms/incident/{id}/transcripts/{tid}/audio` | POST | required + hierarchy | Upload audio blob (multipart) |
| `/docs` | GET | — | Auto-generated OpenAPI docs |

"hierarchy" means `caller_uid == owner_uid`, or caller is an ancestor in the `users/{uid}.createdBy` chain.
