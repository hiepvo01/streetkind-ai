#!/usr/bin/env python3
"""
Frozen incident-report-only snapshot for citing in reports/papers, plus a
reconciliation against the StreetKind dashboard's live cached numbers (the
dashboard reads a pre-aggregated `dashboardInfoStats` node that was found to
drift from a fresh direct count of the same raw data - see README.md).

Scope is deliberately incident reports only (incidentForms + clients) -
this does NOT blend in safeSpaceForms or volunteerHoursForm. Those are a
different data source; the dashboard's "People Assisted" metric combines
them (and has a double-counting bug - see README.md), which is exactly why
this script keeps them separate.

Usage:
    export TK_FOUNDATION_CRED=/path/to/tk-foundation-firebase-adminsdk-*.json
    export TK_FOUNDATION_DB_URL=https://tk-foundation.firebaseio.com
    python3 tools/snapshot_production_stats.py [YYYY-MM-DD snapshot end-cutoff, default 2026-06-30]
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _firebase import connect_tk_foundation, ref  # noqa: E402

CUTOFF_START = datetime(2022, 12, 3)  # official launch
DASHBOARD_START = datetime(2022, 12, 2)  # dashboard's own hardcoded start (1669899600000)


def dt(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts / 1000) if ts > 1e11 else datetime.fromtimestamp(ts)


def in_window(created_ts, start, end):
    d = dt(created_ts)
    return d is not None and start <= d <= end


def main():
    snapshot_end = (datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                     if len(sys.argv) > 1 else datetime(2026, 6, 30, 23, 59, 59))

    app = connect_tk_foundation()
    incidents = ref("incidentForms", app).get() or {}
    clients = ref("clients", app).get() or {}
    safebase = ref("safeSpaceForms", app).get() or {}
    vol_forms = ref("volunteerHoursForm", app).get() or {}

    def scope_incident_clients(start, end):
        in_scope_incidents = []
        in_scope_client_ids = set()
        for iid, inc in incidents.items():
            if not isinstance(inc, dict) or not in_window(inc.get("createdDate"), start, end):
                continue
            in_scope_incidents.append((iid, inc))
            for cid in (inc.get("clientList") or []):
                in_scope_client_ids.add(cid)
        return in_scope_incidents, in_scope_client_ids

    def scope_safebase(start, end):
        return [(sid, s) for sid, s in safebase.items()
                if isinstance(s, dict) and in_window(s.get("createdDate") or s.get("startTime"), start, end)]

    def instance_count(client_ids, path_list):
        """Sum of true sub-fields across all clients (matches the dashboard's counting method)."""
        total = 0
        for cid in client_ids:
            c = clients.get(cid) or {}
            for path in path_list:
                cur = c
                for part in path.split("."):
                    cur = cur.get(part, {}) if isinstance(cur, dict) else {}
                if cur is True:
                    total += 1
        return total

    def any_signal_count(client_ids, path_list):
        """Distinct-client count: 1 if ANY listed sub-field is true, else 0."""
        n = 0
        for cid in client_ids:
            c = clients.get(cid) or {}
            hit = False
            for path in path_list:
                cur = c
                for part in path.split("."):
                    cur = cur.get(part, {}) if isinstance(cur, dict) else {}
                if cur is True:
                    hit = True
            if hit:
                n += 1
        return n

    def report(label, start, end):
        print(f"\n{'='*70}\n{label}  [{start.date()} -> {end.date()}]\n{'='*70}")
        inc_list, client_ids = scope_incident_clients(start, end)
        sb_list = scope_safebase(start, end)
        n_inc, n_cli = len(inc_list), len(client_ids)
        print(f"incidentForms: {n_inc}   clients: {n_cli}   safeSpaceForms: {len(sb_list)}")

        drug_intox_paths = ["drugUseSigns.observed", "drugUseSigns.visibleSigns", "drugUseSigns.disclosed",
                             "intoxicationSigns.balance", "intoxicationSigns.behaviour",
                             "intoxicationSigns.coordination", "intoxicationSigns.speech"]
        print(f"\nDrugs/Intoxicated - dashboard-style instance count (sum of 7 sub-fields): "
              f"{instance_count(client_ids, drug_intox_paths)}")
        print(f"Drugs/Intoxicated - distinct clients w/ >=1 signal: "
              f"{any_signal_count(client_ids, drug_intox_paths)} / {n_cli}")

        n_alone = sum(1 for cid in client_ids if (clients.get(cid) or {}).get("alone") is True)
        print(f"\nAlone (client.alone=true): {n_alone}")

        def risk_scale_count(field):
            return sum(1 for cid in client_ids if (clients.get(cid) or {}).get(field, 0) in (1, 2, 3))
        print(f"\nsexualAssaultRisk in {{1,2,3}} ('Sexual Assault Risk' tile): {risk_scale_count('sexualAssaultRisk')}")
        print(f"physicalAssaultRisk in {{1,2,3}} ('De-escalated Violence'/'Violence Risk' tile): "
              f"{risk_scale_count('physicalAssaultRisk')}")
        print(f"  (contrast - NOT what the dashboard uses - sexualAssault.{{disclosed,observed,visibleSigns}}: "
              f"{any_signal_count(client_ids, ['sexualAssault.disclosed', 'sexualAssault.observed', 'sexualAssault.visibleSigns'])})")
        print(f"  (contrast - NOT what the dashboard uses - physicalAssault.{{disclosed,observed,visibleSigns}}: "
              f"{any_signal_count(client_ids, ['physicalAssault.disclosed', 'physicalAssault.observed', 'physicalAssault.visibleSigns'])})")

        n_welfare = sum(1 for cid in client_ids if (clients.get(cid) or {}).get("otherSupport", {}).get("welfareCheck") is True)
        print(f"\nWelfare Checks (otherSupport.welfareCheck): {n_welfare}")

        reconnect_paths = ["reconnection.telephone", "reconnection.person", "reconnection.socialNetwork"]
        print(f"Reconnections - dashboard-style instance count: {instance_count(client_ids, reconnect_paths)}")

        escort_paths = ["escortedTo.accommodation", "escortedTo.transport", "escortedTo.friends", "escortedTo.other"]
        print(f"Escorted - dashboard-style instance count (excludes safeSpace.escortedTo): "
              f"{instance_count(client_ids, escort_paths)}")

        firstaid_paths = ["additionalAid.firstAid", "additionalAid.mentalHealthAid"]
        print(f"First Aid - dashboard-style instance count (includes mental health aid): "
              f"{instance_count(client_ids, firstaid_paths)}")
        print(f"First Aid - firstAid-only: {instance_count(client_ids, ['additionalAid.firstAid'])}")

        safebase_headcount = 0
        safebase_assistance_instances = 0
        for sid, s in sb_list:
            for gender_key in ("male", "female", "nonBinary"):
                g = s.get(gender_key, {})
                if isinstance(g, dict):
                    safebase_headcount += sum(v for v in g.values() if isinstance(v, (int, float)))
            ar = s.get("assistanceRendered", {})
            if isinstance(ar, dict):
                safebase_assistance_instances += sum(v for v in ar.values() if isinstance(v, (int, float)))

        people_assisted_buggy = safebase_headcount + n_cli + safebase_assistance_instances
        people_assisted_corrected = safebase_headcount + n_cli
        print(f"\nPeople Assisted (NOT incident-report scope - included here only for dashboard reconciliation):")
        print(f"  safe base headcount: {safebase_headcount}, incident clients: {n_cli}, "
              f"safe base assistance-instance extra (double-count bug): {safebase_assistance_instances}")
        print(f"  DASHBOARD FORMULA (headcount + incident-clients + assistance-instances): {people_assisted_buggy}")
        print(f"  CORRECTED (headcount + incident-clients, no double-count): {people_assisted_corrected}")

    report("A) Reconstructing the LIVE dashboard's own formula (all-time since launch)",
           DASHBOARD_START, datetime.now())
    report("B) SNAPSHOT (report/paper cutoff)", CUTOFF_START, snapshot_end)

    print(f"\n{'='*70}\nVolunteer Hours / Shifts - from volunteerHoursForm (has real per-submission dates)\n{'='*70}")
    for label, start, end in [("All-time (dashboard style, no filter)", datetime(1970, 1, 1), datetime.now()),
                               ("Snapshot cutoff", CUTOFF_START, snapshot_end)]:
        hours = 0.0
        shifts_field_sum = 0
        n_submissions = 0
        for vid, v in vol_forms.items():
            if not isinstance(v, dict) or not in_window(v.get("createdDateTime"), start, end):
                continue
            hours += v.get("numberOfVolunteerHours", 0) or 0
            shifts_field_sum += v.get("numberOfVolunteers", 0) or 0
            n_submissions += 1
        print(f"{label} [{start.date()}->{end.date()}]: hours={hours:.2f}, "
              f"'numberOfVolunteers' field sum ('Volunteer Shifts')={shifts_field_sum}, "
              f"n_form_submissions={n_submissions}")

    vh = ref("volunteerHours", app).get() or {}
    live_hours = sum(v.get("totalNumberOfHours", 0) or 0 for v in vh.values() if isinstance(v, dict))
    live_vols = sum(v.get("totalNumberOfVolunteers", 0) or 0 for v in vh.values() if isinstance(v, dict))
    print(f"\nLive volunteerHours/ running-total node (what the dashboard tile actually reads): "
          f"hours={live_hours:.2f}, volunteers/shifts={live_vols}")


if __name__ == "__main__":
    main()
