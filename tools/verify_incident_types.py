#!/usr/bin/env python3
"""
Independently re-verify incident-type presence claims (e.g. "drug and
intoxication encounters are present in every incident") against the live
tk-foundation database, using the same detection logic as the Publications
repo's generate_incident_types.py, computed at BOTH the client level and the
incident level (true if ANY client on that incident has the signal).

Grew out of checking a specific paper claim that turned out to be wrong
(88% of incidents, not literally "every incident") - keep this around to
re-check any similar claim before it goes in a paper/report.

Usage:
    export TK_FOUNDATION_CRED=/path/to/tk-foundation-firebase-adminsdk-*.json
    export TK_FOUNDATION_DB_URL=https://tk-foundation.firebaseio.com
    python3 tools/verify_incident_types.py [YYYY-MM-DD end-cutoff, default=today]
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _firebase import connect_tk_foundation, ref  # noqa: E402

CUTOFF_START = datetime(2022, 12, 3)  # official launch


def has_type(c, type_name):
    if not isinstance(c, dict):
        return False
    if type_name == "Drugs / Intoxicated":
        if c.get("drugs") is True:
            return True
        intox = c.get("intoxicationSigns", {})
        if isinstance(intox, dict) and (intox.get("balance") or intox.get("behaviour") or
                                         intox.get("coordination") or intox.get("speech")):
            return True
        drug_use = c.get("drugUseSigns", {})
        return isinstance(drug_use, dict) and (drug_use.get("observed") or drug_use.get("visibleSigns")
                                                or drug_use.get("disclosed"))
    if type_name == "Welfare Checks":
        return c.get("otherSupport", {}).get("welfareCheck") is True
    if type_name == "First Aid":
        aa = c.get("additionalAid", {})
        aid_given = isinstance(aa, dict) and (aa.get("firstAid") or aa.get("mentalHealthAid"))
        return bool(aid_given) or any((c.get("injury") or {}).values())
    if type_name == "Escorted to Safety":
        et = c.get("escortedTo", {})
        ss = c.get("safeSpace", {})
        escorted = isinstance(et, dict) and (et.get("accommodation") or et.get("transport") or
                                              et.get("friends") or et.get("other"))
        return bool(escorted) or (isinstance(ss, dict) and ss.get("escortedTo") is True)
    if type_name == "Reconnections":
        return any((c.get("reconnection") or {}).values())
    if type_name == "Found Alone":
        return c.get("alone") is True
    if type_name == "Sexual Assault Risk":
        return c.get("sexualAssaultRisk", 0) in (1, 2, 3)
    if type_name == "Violence Risk":
        return c.get("physicalAssaultRisk", 0) in (1, 2, 3)
    return False


TYPES = ["Drugs / Intoxicated", "Welfare Checks", "First Aid", "Escorted to Safety",
         "Reconnections", "Found Alone", "Sexual Assault Risk", "Violence Risk"]


def main():
    cutoff_end = datetime.strptime(sys.argv[1], "%Y-%m-%d") if len(sys.argv) > 1 else datetime.now()
    app = connect_tk_foundation()

    incidents = ref("incidentForms", app).get() or {}
    clients = ref("clients", app).get() or {}

    n_total = 0
    n_clients = 0
    counts_incident = {t: 0 for t in TYPES}
    counts_client = {t: 0 for t in TYPES}

    for iid, inc in incidents.items():
        if not isinstance(inc, dict):
            continue
        ts = inc.get("createdDate")
        if not ts:
            continue
        dt = datetime.fromtimestamp(ts / 1000) if ts > 1e11 else datetime.fromtimestamp(ts)
        if dt < CUTOFF_START or dt > cutoff_end:
            continue
        n_total += 1
        client_ids = inc.get("clientList") or []
        active = set()
        for cid in (client_ids if isinstance(client_ids, list) else []):
            c = clients.get(cid)
            n_clients += 1
            for t in TYPES:
                if has_type(c, t):
                    counts_client[t] += 1
                    active.add(t)
        for t in active:
            counts_incident[t] += 1

    print(f"Window: {CUTOFF_START.date()} -> {cutoff_end.date()}")
    print(f"Total incidents: {n_total}   Total client records: {n_clients}\n")
    print("Incident-level presence (>=1 client on the incident matches), sorted:")
    for t, n in sorted(counts_incident.items(), key=lambda x: -x[1]):
        print(f"  {t:22} {n:5d} / {n_total}  ({100*n/n_total:5.1f}%)")
    print("\nClient-level presence, sorted:")
    for t, n in sorted(counts_client.items(), key=lambda x: -x[1]):
        print(f"  {t:22} {n:5d} / {n_clients}  ({100*n/n_clients:5.1f}%)")


if __name__ == "__main__":
    main()
