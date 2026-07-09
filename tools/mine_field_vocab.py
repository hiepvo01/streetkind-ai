#!/usr/bin/env python3
"""
Mine historical incidentForms/clients data to find what words/phrases team
leaders actually use in incidentDescription/incidentOutcome when a given
structured field is set true.

Read-only against the tk-foundation Firebase RTDB. Does NOT print or persist
firstName/lastName/email/contactNumber/suburb - only aggregated word/phrase
statistics keyed by field path, thresholded so a phrase must appear across
multiple distinct incidents before it's reported (avoids leaking one
person's idiosyncratic story). Even so, treat the output as containing real
(if anonymised) incident narratives - see README.md before sharing results.

Used to ground config/prompts/incident.txt's phrase-binding rules in real
team-leader vocabulary rather than invented examples.

Usage:
    export TK_FOUNDATION_CRED=/path/to/tk-foundation-firebase-adminsdk-*.json
    export TK_FOUNDATION_DB_URL=https://tk-foundation.firebaseio.com
    python3 tools/mine_field_vocab.py [output.json]
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _firebase import connect_tk_foundation, ref  # noqa: E402

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else "field_vocab.json"

# Official program launch - excludes pre-launch/test entries from an earlier
# schema/branding (see README.md for why this cutoff matters).
CUTOFF_DATE = datetime(2022, 12, 3)

MIN_DISTINCT_INCIDENTS_FOR_WORD = 3  # word must recur across >=N incidents to be reported
MIN_FIELD_SAMPLE_SIZE = 5            # skip fields with fewer than N true examples entirely

STOPWORDS = set("""
a an the and or but if then so to of in on at for with without by from into onto
is are was were be been being do does did doing have has had having
he she they them his her their him it its we us our you your i me my
this that these those there here as up down out over under again further
not no nor very s t can will just don should now then than
went was went got get take took helped help helping walked walk called call
gave give asked ask said say told tell one two three
""".split())

WORD_RE = re.compile(r"[a-z']+")


def flatten_true_bools(d, prefix=""):
    """Yield dotted paths of every boolean leaf that is True."""
    if not isinstance(d, dict):
        return
    for k, v in d.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            yield from flatten_true_bools(v, path + ".")
        elif v is True:
            yield path


def tokenize(text):
    return [w for w in WORD_RE.findall(text.lower()) if len(w) >= 3 and w not in STOPWORDS]


def bigrams(tokens):
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def incident_datetime(incident):
    ts = incident.get("createdDate")
    if not ts:
        return None
    return datetime.fromtimestamp(ts / 1000) if ts > 1e11 else datetime.fromtimestamp(ts)


def main():
    app = connect_tk_foundation()

    print("Fetching incidentForms and clients (read-only)...")
    incidents = ref("incidentForms", app).get() or {}
    clients = ref("clients", app).get() or {}
    print(f"  {len(incidents)} incidents, {len(clients)} clients")

    field_texts = defaultdict(list)
    background_texts = []

    skipped_pre_launch = 0
    for incident_id, incident in incidents.items():
        if not isinstance(incident, dict):
            continue
        dt = incident_datetime(incident)
        if dt is None or dt < CUTOFF_DATE:
            skipped_pre_launch += 1
            continue
        narrative = " ".join(
            str(incident.get(k, "")) for k in ("incidentDescription", "incidentOutcome")
        ).strip()
        if not narrative:
            continue
        background_texts.append(narrative)

        client_ids = incident.get("clientList") or []
        if not isinstance(client_ids, list):
            continue

        seen_fields_this_incident = set()
        for cid in client_ids:
            client = clients.get(cid)
            if not isinstance(client, dict):
                continue
            safe_client = {
                k: v for k, v in client.items()
                if k not in ("firstName", "lastName", "email", "contactNumber", "suburb", "incidentId")
            }
            for field_path in flatten_true_bools(safe_client):
                seen_fields_this_incident.add(field_path)

        for field_path in seen_fields_this_incident:
            field_texts[field_path].append(narrative)

    print(f"  skipped {skipped_pre_launch} incidents dated before {CUTOFF_DATE.date()} (pre-launch/no date)")
    print(f"  {len(background_texts)} incidents in scope after cutoff")
    print(f"  {len(field_texts)} distinct field paths observed as true at least once")

    bg_counter = Counter()
    bg_bigram_counter = Counter()
    for text in background_texts:
        toks = tokenize(text)
        bg_counter.update(set(toks))
        bg_bigram_counter.update(set(bigrams(toks)))
    n_bg = max(len(background_texts), 1)

    results = {}
    for field_path, texts in field_texts.items():
        if len(texts) < MIN_FIELD_SAMPLE_SIZE:
            continue

        word_incident_counts = Counter()
        bigram_incident_counts = Counter()
        for text in texts:
            toks = tokenize(text)
            word_incident_counts.update(set(toks))
            bigram_incident_counts.update(set(bigrams(toks)))

        n_field = len(texts)

        def score_terms(counter, bg_counter, min_count):
            scored = []
            for term, c in counter.items():
                if c < min_count:
                    continue
                fg_rate = c / n_field
                bg_rate = (bg_counter.get(term, 0) + 1) / (n_bg + 1)
                lift = fg_rate / bg_rate
                scored.append((term, c, round(lift, 2)))
            scored.sort(key=lambda x: (-x[2], -x[1]))
            return scored[:15]

        results[field_path] = {
            "sample_size": n_field,
            "top_words": score_terms(word_incident_counts, bg_counter, MIN_DISTINCT_INCIDENTS_FOR_WORD),
            "top_phrases": score_terms(bigram_incident_counts, bg_bigram_counter, MIN_DISTINCT_INCIDENTS_FOR_WORD),
        }

    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote vocab stats for {len(results)} fields to {OUT_PATH}")


if __name__ == "__main__":
    main()
