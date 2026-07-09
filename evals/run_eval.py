#!/usr/bin/env python3
"""
Eval runner: replay evals/<scenario>/script.txt transcripts through the
incident extractor under one or more prompt variants, diff the result against
evals/<scenario>/expected.json, and append a permanent record of every run to
evals/results/runs.jsonl (with the exact rendered prompt text snapshotted
content-addressed under evals/results/prompts/).

Usage:
    python run_eval.py                                   # old (git HEAD) vs new (working tree)
    python run_eval.py --new-ref HEAD --old-ref HEAD~3    # compare two commits
    python run_eval.py --labels new                       # just the working-tree prompt
    python run_eval.py --scenarios hard-1 hard-2           # subset of scenarios

Requires ANTHROPIC_FOUNDRY_API_KEY + ANTHROPIC_FOUNDRY_BASE_URL (or
ANTHROPIC_FOUNDRY_RESOURCE) in streetkind-ai/.env or the environment.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
AI_DIR = EVALS_DIR.parent  # evals/ lives inside streetkind-ai/
RESULTS_DIR = EVALS_DIR / "results"
PROMPTS_DIR = RESULTS_DIR / "prompts"
RUNS_LOG = RESULTS_DIR / "runs.jsonl"

sys.path.insert(0, str(AI_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(AI_DIR / ".env")

import app.config as cfg  # noqa: E402
from app.schemas.client_schema import ClientFormSchema  # noqa: E402
from app.schemas.incident_schema import IncidentFormSchema  # noqa: E402
from app.services.ai_extractor import extract_incident  # noqa: E402


def render_prompt(template_text: str) -> str:
    """Reproduce app.config.load_prompt's templating for an arbitrary template string."""
    app_conf = cfg.get_app_config()
    return template_text.format(
        organisation_name=app_conf["organisation_name"],
        site_keys=", ".join(cfg.get_site_keys()),
        encountered_by_keys=cfg._option_keys("incident", "encountered_by"),
        other_services_keys=cfg._option_keys("incident", "other_services"),
        client_risk_indicator_fields=cfg._client_risk_indicator_doc(),
    )


def prompt_for_ref(ref: str) -> str:
    """
    ref is 'worktree' for the live file on disk, 'snapshot:<hash>' for a
    previously-recorded rendered prompt (evals/results/prompts/<hash>.txt —
    the exact text that generated some prior run, whether or not it was ever
    committed to git), or a git rev for a committed version of the template.
    """
    if ref == "worktree":
        return cfg.get_incident_prompt()
    if ref.startswith("snapshot:"):
        digest = ref.split(":", 1)[1]
        path = PROMPTS_DIR / f"{digest}.txt"
        if not path.exists():
            raise FileNotFoundError(f"No saved prompt snapshot at {path}")
        return path.read_text(encoding="utf-8")
    template_text = subprocess.run(
        ["git", "show", f"{ref}:config/prompts/incident.txt"],
        cwd=AI_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return render_prompt(template_text)


def snapshot_prompt(text: str) -> str:
    """Write the rendered prompt to a content-addressed file, return its hash."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPTS_DIR / f"{digest}.txt"
    if not path.exists():
        path.write_text(text, encoding="utf-8")
    return digest


def discover_scenarios(names: list[str] | None) -> list[Path]:
    dirs = sorted(
        p for p in EVALS_DIR.iterdir()
        if p.is_dir() and p.name != "results" and (p / "script.txt").exists()
    )
    if names:
        wanted = set(names)
        dirs = [d for d in dirs if d.name in wanted]
    return dirs


def deep_merge_defaults(default: dict, sparse: dict) -> dict:
    """Overlay sparse (from expected.json, only non-default fields) onto a full default dict."""
    merged = dict(default)
    for k, v in sparse.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = deep_merge_defaults(merged[k], v)
        else:
            merged[k] = v
    return merged


SITE_LABELS = {s["key"]: s["label"] for s in cfg.get_sites()}
FREE_TEXT_FIELDS = {"incidentDescription", "incidentOutcome"}


def _normalize_address(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _address_matches(expected: str, actual: str) -> bool:
    """Lenient: a match if either normalized string contains the other (extra
    real context like ', Sydney' or a suburb shouldn't fail the address field)."""
    if not expected:
        return True
    exp_n, act_n = _normalize_address(expected), _normalize_address(actual)
    return exp_n in act_n or act_n in exp_n


def diff_dict(expected: dict, actual: dict, path: str = "") -> list[str]:
    mismatches = []
    for k, exp_v in expected.items():
        p = f"{path}.{k}" if path else k
        if k in FREE_TEXT_FIELDS:
            continue
        act_v = actual.get(k, "<missing>")
        if k == "site":
            act_label = SITE_LABELS.get(act_v, act_v)
            if exp_v not in (act_v, act_label):
                mismatches.append(f"{p}: expected {exp_v!r}, got {act_v!r}")
            continue
        if k == "address" and isinstance(exp_v, str) and isinstance(act_v, str):
            if not _address_matches(exp_v, act_v):
                mismatches.append(f"{p}: expected {exp_v!r}, got {act_v!r}")
            continue
        if isinstance(exp_v, dict) and isinstance(act_v, dict):
            mismatches.extend(diff_dict(exp_v, act_v, p))
        elif exp_v != act_v:
            mismatches.append(f"{p}: expected {exp_v!r}, got {act_v!r}")
    return mismatches


def compare(expected: dict, actual: dict) -> list[str]:
    default_incident = IncidentFormSchema().model_dump(by_alias=True)
    default_client = ClientFormSchema().model_dump(by_alias=True)

    mismatches = diff_dict(
        deep_merge_defaults(default_incident, expected.get("incident", {})),
        actual.get("incident", {}),
        "incident",
    )

    exp_clients = expected.get("clients", [])
    act_clients = actual.get("clients", [])
    if len(exp_clients) != len(act_clients):
        mismatches.append(f"clients: expected {len(exp_clients)} client(s), got {len(act_clients)}")
    for i, exp_c in enumerate(exp_clients):
        if i >= len(act_clients):
            break
        full_exp_c = deep_merge_defaults(default_client, exp_c)
        mismatches.extend(diff_dict(full_exp_c, act_clients[i], f"clients[{i}]"))
    return mismatches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-ref", default="HEAD", help="git ref for the 'old' prompt (default HEAD)")
    parser.add_argument("--new-ref", default="worktree", help="'worktree' or a git ref for the 'new' prompt")
    parser.add_argument("--labels", nargs="+", default=["old", "new"], choices=["old", "new"])
    parser.add_argument("--scenarios", nargs="+", default=None)
    args = parser.parse_args()

    refs = {"old": args.old_ref, "new": args.new_ref}
    prompts = {label: prompt_for_ref(refs[label]) for label in args.labels}
    hashes = {label: snapshot_prompt(text) for label, text in prompts.items()}
    for label in args.labels:
        print(f"[{label}] ref={refs[label]!r} hash={hashes[label]} ({len(prompts[label])} chars)")

    scenarios = discover_scenarios(args.scenarios)
    if not scenarios:
        print("No scenarios found.", file=sys.stderr)
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_batch_id = f"batch-{hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:8]}"
    summary = []

    with open(RUNS_LOG, "a", encoding="utf-8") as log_f:
        for scenario_dir in scenarios:
            name = scenario_dir.name
            transcript = (scenario_dir / "script.txt").read_text(encoding="utf-8").strip()
            expected = json.loads((scenario_dir / "expected.json").read_text(encoding="utf-8"))

            for label in args.labels:
                print(f"-- {name} [{label}] ...", end=" ", flush=True)
                try:
                    extracted, meta = extract_incident(transcript, site="", system_prompt=prompts[label])
                    error = None
                except Exception as e:
                    extracted, meta = None, {}
                    error = str(e)

                record = {
                    "run_id": f"{run_batch_id}-{name}-{label}",
                    "run_batch_id": run_batch_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "scenario": name,
                    "prompt_label": label,
                    "prompt_ref": refs[label],
                    "prompt_hash": hashes[label],
                    "model": meta.get("model"),
                    "claude_ms": meta.get("claudeMs"),
                    "tokens_input": meta.get("tokensInput"),
                    "tokens_output": meta.get("tokensOutput"),
                    "error": error,
                    "output": extracted,
                }
                log_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                log_f.flush()

                out_path = scenario_dir / f"actual_{label}.json"
                out_path.write_text(
                    json.dumps(extracted if extracted is not None else {"error": error}, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

                mismatches = compare(expected, extracted) if extracted is not None else [f"CALL FAILED: {error}"]
                summary.append({"scenario": name, "label": label, "mismatches": mismatches})
                print(f"{'PASS' if not mismatches else f'{len(mismatches)} mismatch(es)'}")

    print("\n=== Summary ===")
    for row in summary:
        status = "PASS" if not row["mismatches"] else f"FAIL ({len(row['mismatches'])})"
        print(f"{row['scenario']:12s} [{row['label']:4s}] {status}")
        for m in row["mismatches"]:
            print(f"    - {m}")

    summary_path = RESULTS_DIR / f"{run_batch_id}-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nRun batch: {run_batch_id}")
    print(f"Full history: {RUNS_LOG}")
    print(f"This run's summary: {summary_path}")


if __name__ == "__main__":
    main()
