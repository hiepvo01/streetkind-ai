#!/usr/bin/env python3
"""
Aggregate statistics on risk-indicator combinations, complexity, and referral
patterns across historical incidentForms/clients - for designing realistic
evaluation scenarios or sanity-checking prompt/schema assumptions. Read-only.
Outputs ONLY counts/frequencies - no narrative text, no names, no dates, no
identifying fields are read.

Usage:
    export TK_FOUNDATION_CRED=/path/to/tk-foundation-firebase-adminsdk-*.json
    export TK_FOUNDATION_DB_URL=https://tk-foundation.firebaseio.com
    python3 tools/incident_patterns.py [output.json]
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _firebase import connect_tk_foundation, ref  # noqa: E402

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "incident_patterns.json"

CUTOFF_DATE = datetime(2022, 12, 3)  # official launch

RISK_CATEGORIES = [
    "intoxicationSigns",
    "drugUseSigns",
    "offensiveConduct",
    "selfHarmSigns",
    "suicidalSigns",
    "sexualAssault",
    "physicalAssault",
    "domesticViolence",
]

REFERRAL_FIELDS = [
    "alcoholDrugInfoService", "beyondBlue", "childProtectionServices", "dvLine",
    "hospital", "lifeline", "link2home", "salvosStreetLevel", "streetbeatBus",
    "traffickingSlaveryAFP",
]


def incident_datetime(incident):
    ts = incident.get("createdDate")
    if not ts:
        return None
    return datetime.fromtimestamp(ts / 1000) if ts > 1e11 else datetime.fromtimestamp(ts)


def leaf_true_fields(group_dict):
    """Boolean leaves that are True within a single field-group dict, excluding notVisible."""
    if not isinstance(group_dict, dict):
        return set()
    return {k for k, v in group_dict.items() if v is True and k != "notVisible"}


def category_active(client, category):
    return len(leaf_true_fields(client.get(category, {}))) > 0


def main():
    app = connect_tk_foundation()

    print("Fetching incidentForms and clients (read-only, structured fields only)...")
    incidents = ref("incidentForms", app).get() or {}
    clients = ref("clients", app).get() or {}

    in_scope_clients = []
    incident_client_map = defaultdict(list)

    n_incidents_in_scope = 0
    for incident_id, incident in incidents.items():
        if not isinstance(incident, dict):
            continue
        dt = incident_datetime(incident)
        if dt is None or dt < CUTOFF_DATE:
            continue
        n_incidents_in_scope += 1
        client_ids = incident.get("clientList") or []
        if not isinstance(client_ids, list):
            continue
        for cid in client_ids:
            c = clients.get(cid)
            if isinstance(c, dict):
                in_scope_clients.append(c)
                incident_client_map[incident_id].append(c)

    n_clients = len(in_scope_clients)
    print(f"  {n_incidents_in_scope} incidents in scope, {n_clients} client records")

    # ---- 1. Leaf-field frequency within each risk-category group ----
    leaf_freq = defaultdict(Counter)
    for c in in_scope_clients:
        for cat in RISK_CATEGORIES:
            for leaf in leaf_true_fields(c.get(cat, {})):
                leaf_freq[cat][leaf] += 1

    # ---- 2. Category-level activation frequency + pairwise co-occurrence ----
    cat_active_freq = Counter()
    pair_cooccurrence = Counter()
    complexity_per_client = []

    for c in in_scope_clients:
        active = [cat for cat in RISK_CATEGORIES if category_active(c, cat)]
        for cat in active:
            cat_active_freq[cat] += 1
        for a, b in combinations(sorted(active), 2):
            pair_cooccurrence[(a, b)] += 1
        complexity_per_client.append(len(active))

    complexity_buckets_client = Counter()
    for n in complexity_per_client:
        bucket = "0" if n == 0 else ("1-2" if n <= 2 else "3+")
        complexity_buckets_client[bucket] += 1

    complexity_per_incident = []
    for incident_id, cl in incident_client_map.items():
        active_union = set()
        for c in cl:
            active_union.update(cat for cat in RISK_CATEGORIES if category_active(c, cat))
        complexity_per_incident.append(len(active_union))

    complexity_buckets_incident = Counter()
    for n in complexity_per_incident:
        bucket = "0" if n == 0 else ("1-2" if n <= 2 else "3+")
        complexity_buckets_incident[bucket] += 1

    # ---- 3. "Hard" risk pairs specifically called out ----
    hard_pairs_of_interest = [
        ("sexualAssault", "domesticViolence"),
        ("suicidalSigns", "selfHarmSigns"),
        ("physicalAssault", "domesticViolence"),
        ("sexualAssault", "physicalAssault"),
        ("drugUseSigns", "suicidalSigns"),
        ("drugUseSigns", "selfHarmSigns"),
        ("intoxicationSigns", "physicalAssault"),
        ("intoxicationSigns", "offensiveConduct"),
    ]
    hard_pairs_result = {}
    for a, b in hard_pairs_of_interest:
        key = tuple(sorted((a, b)))
        hard_pairs_result[f"{a}+{b}"] = pair_cooccurrence.get(key, 0)

    # ---- 4. Referral patterns ----
    referral_freq = Counter()
    referral_pair_cooccurrence = Counter()
    other_support_freq = Counter()
    service_info_freq = Counter()

    for c in in_scope_clients:
        refs = c.get("clientServiceReferrals", {})
        active_refs = [f for f in REFERRAL_FIELDS if isinstance(refs, dict) and refs.get(f) is True]
        for f in active_refs:
            referral_freq[f] += 1
        for a, b in combinations(sorted(active_refs), 2):
            referral_pair_cooccurrence[(a, b)] += 1

        other = c.get("otherSupport", {})
        if isinstance(other, dict):
            for f in ("welfareCheck", "homelessSupport"):
                if other.get(f) is True:
                    other_support_freq[f] += 1

        svc_info = c.get("serviceInformation", {})
        if isinstance(svc_info, dict):
            for f in ("contactedService", "infoProvided"):
                if svc_info.get(f) is True:
                    service_info_freq[f] += 1

    n_clients_with_any_referral = sum(
        1 for c in in_scope_clients
        if isinstance(c.get("clientServiceReferrals"), dict)
        and any(c["clientServiceReferrals"].get(f) is True for f in REFERRAL_FIELDS)
    )

    result = {
        "scope": {
            "cutoff_date": CUTOFF_DATE.isoformat(),
            "n_incidents": n_incidents_in_scope,
            "n_clients": n_clients,
        },
        "leaf_field_frequency": {cat: dict(leaf_freq[cat].most_common()) for cat in RISK_CATEGORIES},
        "category_activation_frequency": dict(cat_active_freq.most_common()),
        "top_category_pairs": {f"{a}+{b}": n for (a, b), n in pair_cooccurrence.most_common(20)},
        "hard_pairs_of_interest": hard_pairs_result,
        "complexity_per_client_buckets": dict(complexity_buckets_client),
        "complexity_per_incident_buckets": dict(complexity_buckets_incident),
        "referral_frequency": dict(referral_freq.most_common()),
        "top_referral_pairs": {f"{a}+{b}": n for (a, b), n in referral_pair_cooccurrence.most_common(10)},
        "n_clients_with_any_referral": n_clients_with_any_referral,
        "other_support_frequency": dict(other_support_freq),
        "service_information_frequency": dict(service_info_freq),
    }

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nWrote aggregate stats to {OUT_PATH}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
