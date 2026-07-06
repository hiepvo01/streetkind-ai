#!/usr/bin/env python3
"""
Turn export_voice_logs.py's output into a compact summary payload (field
highlights instead of full nested JSON, plus coverage stats) suitable for
embedding in an HTML review dashboard. Pure post-processing - no Firebase
credentials needed, just the export_voice_logs.py output file.

Usage:
    python3 tools/build_voice_report.py voice_log_export.json [output.json]
"""

import json
import sys

IN_PATH = sys.argv[1] if len(sys.argv) > 1 else "voice_log_export.json"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "voice_report_payload.json"

RISK_CATEGORIES = [
    "intoxicationSigns", "drugUseSigns", "offensiveConduct", "selfHarmSigns",
    "suicidalSigns", "sexualAssault", "physicalAssault", "domesticViolence",
]


def truthy_leaves(d, prefix=""):
    """Dotted paths of every leaf that's a non-default signal: True, nonzero int, nonempty string."""
    out = []
    if not isinstance(d, dict):
        return out
    for k, v in d.items():
        if k in ("firstName", "lastName", "email", "contactNumber", "createdBy", "editedBy",
                  "createdDate", "editedDate", "schemaVersion", "schemaName", "incidentId",
                  "clientList", "transcriptIds", "clientId"):
            continue
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            out.extend(truthy_leaves(v, path + "."))
        elif isinstance(v, bool):
            if v:
                out.append(path)
        elif isinstance(v, (int, float)):
            if v != 0:
                out.append(f"{path}={v}")
        elif isinstance(v, str):
            if v.strip():
                out.append(f'{path}="{v}"')
    return out


def main():
    rows = json.load(open(IN_PATH))

    incident_ids_seen = set()
    audio_count = 0
    category_coverage = {c: 0 for c in RISK_CATEGORIES}
    counted_incidents = set()  # dedupe: an incident's clients are identical across all its transcripts

    report_rows = []
    for r in rows:
        incident_ids_seen.add(r["incidentId"])
        if r["has_audio"]:
            audio_count += 1

        form = r["incident_form"] or {}
        clients = r["client_records"] or []

        incident_highlights = truthy_leaves(
            {k: v for k, v in form.items() if k not in ("clientList", "transcriptIds")}
        )

        client_highlights = []
        for c in clients:
            hl = truthy_leaves(c)
            client_highlights.append(hl)
            if r["incidentId"] not in counted_incidents:
                for cat in RISK_CATEGORIES:
                    # a "real" signal, not just the notVisible default being toggled
                    if any(h.startswith(cat + ".") and not h.endswith(".notVisible") for h in hl):
                        category_coverage[cat] += 1
        counted_incidents.add(r["incidentId"])

        report_rows.append({
            "transcriptId": r["transcriptId"],
            "incidentId": r["incidentId"],
            "date": r["date"],
            "text": r["transcript_text"],
            "hasAudio": r["has_audio"],
            "audioDurationMs": r["audioDurationMs"],
            "incidentHighlights": incident_highlights,
            "clientHighlights": client_highlights,
            "nClients": len(clients),
        })

    summary = {
        "totalLogs": len(rows),
        "distinctIncidents": len(incident_ids_seen),
        "audioCount": audio_count,
        "textOnlyCount": len(rows) - audio_count,
        "dateRangeStart": rows[0]["date"] if rows else None,
        "dateRangeEnd": rows[-1]["date"] if rows else None,
        "riskCategoryCoverageBasis": "distinct incidents (not transcripts)",
        "riskCategoryCoverage": category_coverage,
    }

    payload = {"summary": summary, "rows": report_rows}

    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
