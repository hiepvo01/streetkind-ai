#!/usr/bin/env python3
"""
Fuzz-test generator: for each evals/<scenario>/script.txt, ask Haiku to
rewrite it 10 different ways - same facts, same ground truth, different
voice (vocabulary, sentence structure, pacing, informality). Saves each
variant to evals/<scenario>/variants/<scenario>-variant-<n>.txt.

The point is to measure the extraction pipeline's robustness to how a
volunteer happens to phrase the same underlying incident, holding
expected.json fixed as ground truth for every variant.

Usage:
    python generate_variants.py                      # all 9 scenarios, 10 variants each
    python generate_variants.py --scenarios easy-1    # just one
    python generate_variants.py --n 5                 # fewer variants per scenario

Requires ANTHROPIC_FOUNDRY_API_KEY + ANTHROPIC_FOUNDRY_BASE_URL (streetkind-ai/.env).
"""
import argparse
import json
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
AI_DIR = EVALS_DIR.parent  # evals/ lives inside streetkind-ai/

sys.path.insert(0, str(AI_DIR))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(AI_DIR / ".env")

from anthropic import AnthropicFoundry  # noqa: E402
import os  # noqa: E402

MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = """You are helping build a robustness test suite for a voice-to-form AI \
pipeline used by street outreach volunteers in Sydney, Australia. You will be given a \
volunteer's spoken account of an incident (a transcript) and the structured ground-truth \
JSON that a correct extraction should produce from it.

Rewrite the transcript {n} different ways. Each rewrite must describe the EXACT SAME \
incident - same people, same demographics, same risk signals, same actions/support given, \
same outcome - but in a genuinely different voice each time: vary sentence structure, \
vocabulary, level of detail, ordering of information, informality/slang, and pacing, as if \
a different volunteer with a different way of talking gave the account after the same shift.

Hard rules:
- Do not add any fact, risk signal, action, name, place, or detail that isn't in the \
original transcript or implied by the ground truth JSON.
- Do not remove or soften any fact, risk signal, or action that IS in the original - every \
disclosure, observation, and support action must still be clearly recoverable in each \
rewrite, in whatever words fit that variant's voice.
- Never mention field names, booleans, or JSON syntax in the rewrites - they must read as \
natural spoken volunteer accounts, exactly like the original.
- Keep each rewrite roughly the same length as the original (not a summary, not padded).
- Make the {n} variants meaningfully different from EACH OTHER too, not just from the \
original - vary which details are mentioned first, how casual/formal the language is, \
sentence length, and word choice each time.

Call the tool with exactly {n} variants."""


def build_tool(n: int) -> dict:
    return {
        "name": "submit_variants",
        "description": f"Submit exactly {n} rewritten variants of the transcript.",
        "input_schema": {
            "type": "object",
            "properties": {
                "variants": {
                    "type": "array",
                    "minItems": n,
                    "maxItems": n,
                    "items": {"type": "string"},
                }
            },
            "required": ["variants"],
        },
    }


def get_client() -> AnthropicFoundry:
    api_key = os.environ["ANTHROPIC_FOUNDRY_API_KEY"]
    base_url = os.environ.get("ANTHROPIC_FOUNDRY_BASE_URL")
    resource = os.environ.get("ANTHROPIC_FOUNDRY_RESOURCE")
    if base_url:
        return AnthropicFoundry(api_key=api_key, base_url=base_url)
    return AnthropicFoundry(api_key=api_key, resource=resource)


def generate_variants(client: AnthropicFoundry, transcript: str, expected: dict, n: int) -> list[str]:
    tool = build_tool(n)
    user_content = (
        f"Original transcript:\n\"\"\"\n{transcript}\n\"\"\"\n\n"
        f"Ground-truth JSON this transcript should extract to (for your reference only - "
        f"use it to know which facts matter, don't echo field names or structure):\n"
        f"{json.dumps(expected, indent=2)}"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT.format(n=n),
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_variants"},
        messages=[{"role": "user", "content": user_content}],
    )
    for block in response.content:
        if block.type == "tool_use":
            variants = block.input["variants"]
            if len(variants) != n:
                raise ValueError(f"Expected {n} variants, got {len(variants)}")
            return variants
    raise ValueError("No tool_use block in response")


def discover_scenarios(names: list[str] | None) -> list[Path]:
    dirs = sorted(
        p for p in EVALS_DIR.iterdir()
        if p.is_dir() and p.name != "results" and (p / "script.txt").exists()
    )
    if names:
        wanted = set(names)
        dirs = [d for d in dirs if d.name in wanted]
    return dirs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10, help="variants per scenario (default 10)")
    parser.add_argument("--scenarios", nargs="+", default=None)
    args = parser.parse_args()

    client = get_client()
    scenarios = discover_scenarios(args.scenarios)
    if not scenarios:
        print("No scenarios found.", file=sys.stderr)
        sys.exit(1)

    for scenario_dir in scenarios:
        name = scenario_dir.name
        transcript = (scenario_dir / "script.txt").read_text(encoding="utf-8").strip()
        expected = json.loads((scenario_dir / "expected.json").read_text(encoding="utf-8"))

        print(f"-- {name}: generating {args.n} variants...", end=" ", flush=True)
        try:
            variants = generate_variants(client, transcript, expected, args.n)
        except Exception as e:
            print(f"FAILED: {e}")
            continue

        variants_dir = scenario_dir / "variants"
        variants_dir.mkdir(exist_ok=True)
        for i, v in enumerate(variants, start=1):
            out_path = variants_dir / f"{name}-variant-{i}.txt"
            out_path.write_text(v.strip() + "\n", encoding="utf-8")
        print(f"wrote {len(variants)} files to {variants_dir}")

    print("\nDone.")


if __name__ == "__main__":
    main()
