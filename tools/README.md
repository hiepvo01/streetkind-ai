# tools/

Ad hoc analysis scripts written while investigating the voice-to-form
evaluation and the StreetKind paper's descriptive statistics. Read-only
against Firebase - none of them write to any database.

## Setup

**Never commit credentials.** Every script reads its Firebase service-account
key path and database URL from environment variables - nothing is hardcoded.
Set the ones you need before running anything here:

```bash
# Legacy/production database - real historical incident data. Treat with
# care: this includes sensitive fields (sexual assault, DV, self-harm,
# suicidal ideation disclosures). Don't paste raw output into shared docs
# without the redaction/thresholding these scripts already apply.
export TK_FOUNDATION_CRED=/path/to/tk-foundation-firebase-adminsdk-*.json
export TK_FOUNDATION_DB_URL=https://tk-foundation.firebaseio.com

# This app's own dev database
export STREETKIND_DEV_CRED=/path/to/streetkind-app-dev-firebase-adminsdk-*.json
export STREETKIND_DEV_DB_URL=https://streetkind-app-dev-default-rtdb.firebaseio.com
```

```bash
pip install -r tools/requirements.txt
```

## Scripts

| Script | Database | What it does |
|---|---|---|
| `mine_field_vocab.py` | tk-foundation | Mines historical `incidentDescription`/`incidentOutcome` text for the real phrases team leaders use when a given structured field is true. Grounded `config/prompts/incident.txt`'s phrase-binding rules in this. |
| `incident_patterns.py` | tk-foundation | Risk-indicator co-occurrence, per-client/per-incident "complexity" distribution, referral patterns - for designing realistic evaluation scenarios. |
| `export_voice_logs.py` | streetkind-app-dev | Exports every voice transcript + the incident form/client records it produced, for checking pipeline test coverage. |
| `build_voice_report.py` | none (post-processing) | Turns `export_voice_logs.py`'s output into a compact summary (non-default field highlights + coverage stats) for an HTML review dashboard. |
| `verify_incident_types.py` | tk-foundation | Independently re-checks incident-type presence claims (e.g. "intoxication is present in every incident") at both client and incident level. Use this before any such claim goes in a report. |
| `snapshot_production_stats.py` | tk-foundation | Frozen incident-report-only snapshot for citing in reports, plus a reconciliation against the live StreetKind dashboard's cached numbers (which were found to drift from a fresh direct count - see "Known data-quality findings" below). |

## Known data-quality findings (as of 2026-07)

Worth knowing before trusting any number that touches these:

- **`client_schema_enhanced.py`** (in `app/schemas/`) has a `notVisible`-exclusivity
  validator that the live pipeline never uses - `CombinedIncidentSchema` imports
  the plain `client_schema.py`, which has no such check. The model can and does
  emit contradictory states (e.g. `notVisible=true` alongside a real signal).
- **`sexualAssaultRisk`/`physicalAssaultRisk`** (the 0-3 Risk Minimisation scale)
  and **`sexualAssault.*`/`physicalAssault.*`** (disclosed/observed/visible-signs)
  are separate schema fields with similar-sounding names and very different
  counts - don't conflate them.
- **The StreetKind dashboard's cached numbers don't match a fresh direct count**
  of the same raw data - every incident/safe-base-derived tile ran ~15-20%
  higher live than recomputing the identical formula fresh. Volunteer stats
  (simple running counters) matched exactly. Likely cause: `dailyData/` is
  built by a nightly cron job *and* separately patched by real-time increment
  triggers, and at least one confirmed formula mismatch exists between the two
  paths. Don't cite the dashboard cache directly - use `snapshot_production_stats.py`.
- **"People Assisted"** on the dashboard combines `safeSpaceForms` headcounts
  with incident-report client counts *and* adds one unit per Safe Base
  assistance action rendered on top of the visitor's own headcount entry -
  i.e. it's inflated by design, not just cache drift. See the script's report
  section for both the as-displayed and corrected numbers.
- Some legacy field names used by earlier one-off scripts no longer exist in
  the current schema (e.g. `violentAssault`, `firstAid.additionalFirstAid`) -
  `verify_incident_types.py`/`snapshot_production_stats.py` use the current
  field names; older ad hoc scripts elsewhere may not.
