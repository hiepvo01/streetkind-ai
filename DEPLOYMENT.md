# Deployment

A running log of how `streetkind-ai` got to production, what's live, what's temporary, and how to redo each step. Keep this current when you change any piece of the stack.

## What's live

| Piece | URL / host | Notes |
|---|---|---|
| Frontend | https://streetkind-app-dev.web.app | Firebase Hosting, `streetkind-app-dev` project |
| Backend API | https://46-62-215-38.sslip.io | FastAPI in Docker on Coolify (Hetzner 46.62.215.38), Let's Encrypt cert |
| Realtime DB | `streetkind-app-dev-default-rtdb.firebaseio.com` | Locked down, Admin SDK only |
| Firebase Storage | `streetkind-app-dev.firebasestorage.app` | Blaze plan, Admin SDK only |
| Auth | Firebase Auth on `streetkind-app-dev` | 3 demo accounts (see `demo-accounts.txt`) |
| Git source for Coolify | `git@github.com:hiepvo01/streetkind-ai.git` | GitHub mirror of UTS GitLab |
| Canonical git source | `code.research.uts.edu.au/Rapido/streetkind/streetkind-ai` | Developers push here; also push to `github` remote for Coolify |

## Known temporary / placeholder pieces

- **sslip.io domain for the backend.** Works but Let's Encrypt rate-limits sslip.io subdomains — a future cert renewal could fail. Replace with a real domain (~$1-10/yr at Cloudflare Registrar or Namecheap) before anything external depends on this.
- **GitHub mirror of the repo.** Coolify can't reach UTS GitLab (port 22 firewalled), so the GitHub repo is the deploy source. Developers need to push to both remotes (`origin` UTS, `github` GitHub) until this is automated. Options: set up a GitLab → GitHub mirror via GitLab settings, or consolidate onto one remote.
- **`FIREBASE_SERVICE_ACCOUNT_PATH` uses a file mount.** Works fine, but if you want simpler secret management, we can add a 4-line change to accept `FIREBASE_SERVICE_ACCOUNT_JSON` as an env var directly.

## Frontend (Firebase Hosting)

**What's deployed:** the React build from `frontend/build/`, baked with build-time env vars:
- `REACT_APP_API_BASE_URL=https://46-62-215-38.sslip.io`
- `REACT_APP_ENABLE_AUDIO=1`

**Config files at repo root:**
- `firebase.json` — hosting rules + rewrites + cache headers + pointers to `database.rules.json` and `storage.rules`
- `.firebaserc` — default project `streetkind-app-dev`

**Redeploy steps (do this after any frontend change or base-URL change):**

```bash
cd frontend
REACT_APP_API_BASE_URL=https://46-62-215-38.sslip.io REACT_APP_ENABLE_AUDIO=1 npm run build
cd ..
npx firebase-tools deploy --only hosting --project streetkind-app-dev
```

**To redeploy database / storage rules:**
```bash
npx firebase-tools deploy --only database --project streetkind-app-dev
npx firebase-tools deploy --only storage --project streetkind-app-dev
```

**Firebase CLI login (once per machine):**
```bash
npx firebase-tools login
```

## Backend (Coolify → Hetzner)

**Coolify app:** `streetkind-backend` in project `streetkind` / environment `production` on the `localhost` server.

**App configuration (Coolify UI → your app → Configuration):**

| Section | Setting | Value |
|---|---|---|
| General | Build Pack | Dockerfile |
| General | Dockerfile Location | `/Dockerfile` |
| General | Ports Exposes | `8000` |
| Domains | Domain | `https://46-62-215-38.sslip.io` |
| Git Source | Repository | `git@github.com:hiepvo01/streetkind-ai.git` |
| Git Source | Branch | `main` |
| Git Source | Deploy Key | `github-hiepvo01-streetkind` (Coolify-generated, public half added to GitHub Deploy Keys) |

**Environment variables (Coolify UI → Environment Variables):**

| Var | Value | Required? |
|---|---|---|
| `ANTHROPIC_FOUNDRY_API_KEY` | Foundry key | yes |
| `ANTHROPIC_FOUNDRY_BASE_URL` | Foundry endpoint, ends in `/anthropic/` | yes (or `ANTHROPIC_FOUNDRY_RESOURCE`) |
| `FIREBASE_DATABASE_URL` | `https://streetkind-app-dev-default-rtdb.firebaseio.com` | yes |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | `/app/firebase-service-account.json` | yes |
| `FIREBASE_STORAGE_BUCKET` | `streetkind-app-dev.firebasestorage.app` | yes (audio uploads return 503 if unset) |
| `CORS_ORIGINS` | `https://streetkind-app-dev.web.app,https://streetkind-app-dev.firebaseapp.com` | yes |
| `OPENAI_API_KEY` | `sk-proj-...` from platform.openai.com | recommended (enables Whisper-quality re-transcription; falls back to Web Speech text if unset) |
| `WHISPER_MODEL` | `whisper-1` (default) | optional override |
| `AUDIO_SIGNED_URL_TTL_SECONDS` | `3600` (default) | optional - signed URL lifetime in seconds |
| `MAX_AUDIO_BYTES` | `20971520` (default 20 MB) | optional |
| `MAX_TRANSCRIPT_LENGTH` | `5000` (default chars) | optional |
| `USERS_CACHE_TTL_SECONDS` | `30` (default) | optional; set `0` to disable hierarchy cache |
| `AI_MODEL` | (reads `config/app.json` default - currently `claude-sonnet-4-6`) | optional override for the Foundry deployment name |

**Persistent storage:** file mount at `/app/firebase-service-account.json` with the contents of the Firebase service-account JSON. Rotate this file in-place in Coolify whenever you rotate the key in Firebase Console.

**Redeploy flow:**

```bash
# 1. Push commits to both remotes (Coolify watches the GitHub one)
git push origin main           # UTS GitLab (canonical)
git push github main           # GitHub mirror (Coolify)

# 2. Coolify auto-deploys on push to main (if the webhook is configured),
#    otherwise click "Redeploy" in the Coolify UI.
```

**Dockerfile notes:**
- Strips `openai-whisper` / `playwright` / `pytest` from `requirements.txt` before `pip install` to keep the image small
- Runs `uvicorn run:app --host 0.0.0.0 --port 8000`
- `.dockerignore` excludes frontend, tests, docs, and any `*firebase-adminsdk*.json` (secrets are injected via persistent storage)

## Firebase project

- **Project ID:** `streetkind-app-dev`
- **Plan:** Blaze (pay-as-you-go). Free tier covers 5 GB Storage + 1 GB/day egress; set a budget alert in GCP if you want hard caps
- **Services in use:** Realtime Database, Storage, Auth, Hosting
- **Rules:**
  - `database.rules.json` — all reads/writes denied to clients; Admin SDK bypasses. `.indexOn` for `createdBy` on `incidentForms` and `safeSpaceForms`, plus `incidentId` / `createdBy` on `transcripts`
  - `storage.rules` — all reads/writes denied to clients. Audio blobs stay **private**; the backend issues short-lived v4 signed URLs on read (see Security model below)

## Security model

- **Auth:** clients send a Firebase ID token (`Authorization: Bearer ...`) on every protected request. The backend verifies via `firebase_admin.auth.verify_id_token` and uses the resulting `uid` as `createdBy` on all writes — clients never set it directly.
- **Access control:** incident-scoped endpoints run through `_check_incident_access` in `app/routes.py`, which calls `is_ancestor(caller_uid, owner_uid)` to check that the caller either owns the record or is an ancestor in the `users/{uid}/createdBy` hierarchy (cached 30s by default).
- **Push-ID validation:** `form_id` and `transcript_id` path params are checked against `^-[A-Za-z0-9_-]{19}$` at the route layer. `upload_audio()` re-validates the same regex inside the service layer as defense-in-depth.
- **Audio storage (private + signed URLs):**
  - `upload_audio()` writes a private blob at `audio/{incidentId}/{transcriptId}.<ext>`. No `make_public()` anywhere in the codebase.
  - `transcripts/{id}/audioPath` stores the blob path. **Never** a persistent URL.
  - `signed_audio_url()` mints v4 signed URLs with TTL `AUDIO_SIGNED_URL_TTL_SECONDS` (default 1 hour). The upload route returns one for immediate playback; the list route mints a fresh one on every request.
  - A leaked signed URL expires and becomes useless. Fresh audio access requires authenticated hierarchy-scoped access to the incident.
- **Content-type + magic byte validation:** audio uploads must have an `audio/*` MIME from `_ALLOWED_AUDIO_TYPES` **and** the first bytes must match a known container (WebM EBML, MP4 `ftyp`, Ogg, MP3 ID3/MPEG). Prevents the endpoint from being a generic file-upload backdoor.
- **Cleanup ordering:** `delete_transcripts_for_incident` deletes Storage blobs **first** (so RTDB `transcriptIds` pointers remain valid for retry if Storage fails), then RTDB records. Failures are logged with `incident_id` and aggregated into a returned summary dict — never silently swallowed.
- **Compensation on partial writes:** if `upload_audio` succeeds but the subsequent `audioPath` RTDB write fails, the route calls `delete_audio_blob` to remove the blob before raising 500, preventing orphaned private blobs.

## DNS / TLS

- The sslip.io subdomain resolves `46-62-215-38.sslip.io` → `46.62.215.38` automatically (no DNS management needed)
- Let's Encrypt issues certs via Coolify's Traefik proxy using HTTP-01 challenge on port 80
- **Known issue from setup:** DuckDNS's nameservers returned `SERVFAIL` during LE validation, which blocked cert issuance. We pivoted to sslip.io. Original DuckDNS record `streetkind-api.duckdns.org` still exists but is unused

## Git remotes

```bash
git remote -v
# origin  https://code.research.uts.edu.au/Rapido/streetkind/streetkind-ai.git   (canonical, UTS)
# github  https://github.com/hiepvo01/streetkind-ai.git                          (mirror for Coolify)
```

Push to both on each deploy. To automate: set up GitLab → GitHub push mirror in UTS GitLab project settings (Settings → Repository → Mirroring repositories).

## Local development

A working `.env` for local dev:

```
ANTHROPIC_FOUNDRY_API_KEY=<Foundry key>
ANTHROPIC_FOUNDRY_BASE_URL=<Foundry endpoint ending in /anthropic/>
FIREBASE_SERVICE_ACCOUNT_PATH=../streetkind-app-dev-firebase-adminsdk-fbsvc-<your-id>.json
FIREBASE_DATABASE_URL=https://streetkind-app-dev-default-rtdb.firebaseio.com
FIREBASE_STORAGE_BUCKET=streetkind-app-dev.firebasestorage.app
CORS_ORIGINS=http://localhost:3000
```

Run:
```bash
# Backend
python run.py                                  # http://localhost:8000

# Frontend (separate terminal)
cd frontend && npm start                       # http://localhost:3000
```

The CRA dev server proxies `/api/*` to `localhost:8000` (see `"proxy"` in `frontend/package.json`), so you don't need to set `REACT_APP_API_BASE_URL` locally.

## E2E tests

```bash
# Local backend + frontend must be running.
# FIREBASE_STORAGE_BUCKET must be set for the audio roundtrip test to hit 200
# (otherwise it cleanly skips with an explicit message).
FIREBASE_SERVICE_ACCOUNT_PATH=<path> \
FIREBASE_STORAGE_BUCKET=streetkind-app-dev.firebasestorage.app \
python -m pytest tests/e2e -v --browser chromium
```

**Suite as of commit `c3b25fb`: 36 collected → 32 passed, 4 skipped (AI-gated).**

Breakdown:
- `test_login.py` (5) — valid/invalid creds, logout, admin login, unauthenticated redirect
- `test_dashboard.py` (2) — 11 stat labels, non-zero live values
- `test_incident_form.py` (2) — UI render + API submit + Firebase verification + cleanup
- `test_safebase_form.py` (2) — UI switching + API submit + cleanup
- `test_incident_crud.py` (4) — full submit/fetch/update/delete cycle + access control + invalid-ID rejection
- `test_transcripts.py` (8) — transcript create/fetch/delete, audio roundtrip (signed URLs + public-URL denial + blob cleanup), 4 security tests (cross-user upload, cross-incident transcript reuse, invalid transcript_id, non-audio payload rejection), 1 concurrency test
- `test_responsive.py` (9) — 3 viewports × 3 checks
- `test_ai_extract.py` (4) — Foundry-backed extraction; **skipped by default**, set `RUN_AI_TESTS=1` to run (costs real tokens)

All tests auto-clean their Firebase records. Override the target API with `API_BASE_URL=https://46-62-215-38.sslip.io` to run against prod.

## Security notes

- **Firebase service account key** has been rotated. If it leaks again, rotate at https://console.firebase.google.com/u/1/project/streetkind-app-dev/settings/serviceaccounts/adminsdk and update:
  1. Local: replace the JSON file referenced by `FIREBASE_SERVICE_ACCOUNT_PATH` in `.env`
  2. Coolify: paste new contents into the persistent storage file mount, redeploy
- The service-account JSON is gitignored (`*firebase-adminsdk*.json` in `.gitignore`). Never commit it
- IDE auto-selection of secret files is a real leak path — keep them closed when working with AI/copilot tools

## Still to do

- [ ] Move from sslip.io to a proper domain (`api.streetkind.xxx`) to eliminate the LE rate-limit risk
- [ ] Automate UTS GitLab → GitHub mirroring so there's one push, not two
- [ ] Migrate the 66 original SKSSIR users from `tk-foundation` Firebase Auth to `streetkind-app-dev` (currently only 3 demo accounts can log in)
- [ ] Set a Blaze budget alert in GCP Billing to cap spend
- [ ] Consider adding health-check & restart policy to the Coolify container (already running, but worth configuring)
- [ ] Write a GitHub Actions workflow (or Coolify cron) to redeploy frontend automatically after `main` pushes, matching the backend's auto-deploy
- [ ] Run the skipped `test_ai_extract.py` suite before releases (`RUN_AI_TESTS=1`) so Foundry contract breaks are caught
- [ ] Add front-end audio UX: show a mic-permission-denied warning so volunteers know why their audio isn't being captured

## Recent audit

A full security + correctness audit of the audio/transcript pipeline ran on 2026-04-25 (commit `c3b25fb`). Findings and remediation:

| ID | Finding | Status |
|---|---|---|
| C1 | Silent Storage errors hid orphan blobs on delete | Fixed — logs + delete-ordering + summary dict |
| C2 | `upload_audio` trusted route-layer ID validation only | Fixed — `_assert_push_id` re-validates at service layer |
| C3 | Audio blobs world-readable via `make_public()` | Fixed — private blobs + v4 signed URLs |
| C4 | Orphan blob if `audioPath` RTDB write failed | Fixed — compensating blob delete |
| C5 | Frontend silently swallowed transcript save failures | Fixed — surfaces warnings in FormPreview |
| I6 | No magic-byte check on uploads | Fixed — WebM/MP4/Ogg/MP3 container detection |
| T1-T5, T8 | Security/concurrency test gaps | Fixed — 5 new tests added |

Remaining Important/Minor findings (I1-I7 excluding I6, M1-M8, T3-T9 excluding added) are tracked informally; none are currently exploitable given the above fixes.
