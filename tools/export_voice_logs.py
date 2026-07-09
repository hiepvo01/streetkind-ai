#!/usr/bin/env python3
"""
Export every voice transcript in the dev database alongside the incident
report form it produced, for assessing voice-pipeline test coverage or
building evaluation fixtures. Reads streetkind-app-dev (this app's own dev
database), NOT tk-foundation.

Usage:
    export STREETKIND_DEV_CRED=/path/to/streetkind-app-dev-firebase-adminsdk-*.json
    export STREETKIND_DEV_DB_URL=https://streetkind-app-dev-default-rtdb.firebaseio.com
    python3 tools/export_voice_logs.py [output.json]
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _firebase import connect_streetkind_dev, ref  # noqa: E402

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "voice_log_export.json"


def fmt_date(ts):
    if not ts:
        return None
    dt = datetime.fromtimestamp(ts / 1000) if ts > 1e11 else datetime.fromtimestamp(ts)
    return dt.isoformat()


def main():
    app = connect_streetkind_dev()

    transcripts = ref("transcripts", app).get() or {}
    incidents = ref("incidentForms", app).get() or {}
    clients = ref("clients", app).get() or {}

    rows = []
    for tid, t in transcripts.items():
        if not isinstance(t, dict):
            continue
        incident_id = t.get("incidentId", "")
        incident = incidents.get(incident_id) if incident_id else None

        client_records = []
        if isinstance(incident, dict):
            for cid in incident.get("clientList") or []:
                c = clients.get(cid)
                if isinstance(c, dict):
                    client_records.append(c)

        rows.append({
            "transcriptId": tid,
            "date": fmt_date(t.get("createdDate")),
            "transcript_text": t.get("text", ""),
            "has_audio": bool(t.get("audioPath")),
            "audioDurationMs": t.get("audioDurationMs", 0),
            "extractionMeta": t.get("extractionMeta", {}),
            "incidentId": incident_id,
            "incident_form": incident,       # full recorded form, None if missing/orphaned
            "client_records": client_records,
        })

    rows.sort(key=lambda r: r["date"] or "")

    with open(OUT_PATH, "w") as f:
        json.dump(rows, f, indent=2, default=str)

    print(f"Wrote {len(rows)} voice-log rows to {OUT_PATH}")
    orphaned = [r for r in rows if r["incident_form"] is None]
    if orphaned:
        print(f"WARNING: {len(orphaned)} transcripts have no matching incidentForms record:")
        for r in orphaned:
            print(f"  transcriptId={r['transcriptId']} incidentId={r['incidentId']!r}")


if __name__ == "__main__":
    main()
