#!/usr/bin/env python3
"""
Robustness eval: run the extraction pipeline against every phrasing variant
of each scenario (evals/<scenario>/script.txt + evals/<scenario>/variants/*.txt),
scoring all of them against that scenario's single expected.json. Measures how
sensitive the pipeline is to how a volunteer happens to phrase the same
underlying incident, holding the prompt fixed.

Usage:
    python run_variant_eval.py                       # current worktree prompt, all scenarios, all variants
    python run_variant_eval.py --scenarios hard-1     # just one scenario
    python run_variant_eval.py --prompt-ref HEAD      # test a specific prompt version instead
"""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import EVALS_DIR, RESULTS_DIR, RUNS_LOG, prompt_for_ref, snapshot_prompt, compare  # noqa: E402
from app.services.ai_extractor import extract_incident  # noqa: E402


def discover_cases(names):
    dirs = sorted(
        p for p in EVALS_DIR.iterdir()
        if p.is_dir() and p.name != "results" and (p / "script.txt").exists()
    )
    if names:
        wanted = set(names)
        dirs = [d for d in dirs if d.name in wanted]

    cases = []
    for d in dirs:
        cases.append({
            "scenario": d.name, "variant": "original",
            "script_path": d / "script.txt", "expected_path": d / "expected.json",
        })
        variants_dir = d / "variants"
        if variants_dir.exists():
            for vf in sorted(variants_dir.glob(f"{d.name}-variant-*.txt")):
                idx = vf.stem.rsplit("-", 1)[-1]
                cases.append({
                    "scenario": d.name, "variant": f"variant-{idx}",
                    "script_path": vf, "expected_path": d / "expected.json",
                })
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-ref", default="worktree")
    parser.add_argument("--scenarios", nargs="+", default=None)
    args = parser.parse_args()

    prompt_text = prompt_for_ref(args.prompt_ref)
    prompt_hash = snapshot_prompt(prompt_text)
    print(f"prompt ref={args.prompt_ref!r} hash={prompt_hash}")

    cases = discover_cases(args.scenarios)
    if not cases:
        print("No cases found.", file=sys.stderr)
        sys.exit(1)
    print(f"{len(cases)} test cases (original + variants)\n")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_batch_id = f"variants-{hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:8]}"
    per_scenario = {}

    with open(RUNS_LOG, "a", encoding="utf-8") as log_f:
        for case in cases:
            name, variant = case["scenario"], case["variant"]
            transcript = case["script_path"].read_text(encoding="utf-8").strip()
            expected = json.loads(case["expected_path"].read_text(encoding="utf-8"))

            print(f"-- {name} [{variant}] ...", end=" ", flush=True)
            try:
                extracted, meta = extract_incident(transcript, site="", system_prompt=prompt_text)
                error = None
            except Exception as e:
                extracted, meta, error = None, {}, str(e)

            record = {
                "run_id": f"{run_batch_id}-{name}-{variant}",
                "run_batch_id": run_batch_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "scenario": name,
                "variant": variant,
                "prompt_label": "latest",
                "prompt_ref": args.prompt_ref,
                "prompt_hash": prompt_hash,
                "model": meta.get("model"),
                "claude_ms": meta.get("claudeMs"),
                "tokens_input": meta.get("tokensInput"),
                "tokens_output": meta.get("tokensOutput"),
                "error": error,
                "output": extracted,
            }
            log_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            log_f.flush()

            mismatches = compare(expected, extracted, name) if extracted is not None else [f"CALL FAILED: {error}"]
            per_scenario.setdefault(name, []).append({"variant": variant, "mismatches": mismatches})
            print("PASS" if not mismatches else f"{len(mismatches)} mismatch(es)")

    print("\n=== Robustness summary ===")
    for name, rows in per_scenario.items():
        counts = [len(r["mismatches"]) for r in rows]
        n_pass = sum(1 for c in counts if c == 0)
        avg = sum(counts) / len(counts)
        print(f"{name:12s} pass {n_pass}/{len(rows)}  avg mismatches {avg:.1f}  (min {min(counts)}, max {max(counts)})")

    summary_path = RESULTS_DIR / f"{run_batch_id}-variant-summary.json"
    summary_path.write_text(
        json.dumps(per_scenario, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nRun batch: {run_batch_id}")
    print(f"Full history: {RUNS_LOG}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
