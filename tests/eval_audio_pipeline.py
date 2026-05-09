"""
Run the production Whisper + Claude extraction pipeline on the 15
test audio files in tests/test_audio/ and save results to JSON.

Usage (from streetkind-ai/):
    python tests/eval_audio_pipeline.py
Outputs:
    tests/test_audio/results.json
"""
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Make `app` importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import after load_dotenv so the production extractor sees the env vars.
from app.services.ai_extractor import extract_incident  # noqa: E402

AUDIO_DIR = Path(__file__).parent / "test_audio"
RESULTS_PATH = AUDIO_DIR / "results.json"
DEFAULT_SITE = "Town Hall"

WHISPER_MODEL = "whisper-1"


def transcribe(client: OpenAI, audio_path: Path) -> tuple[str, float]:
    t0 = time.time()
    with audio_path.open("rb") as f:
        resp = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=f,
            language="en",
        )
    return resp.text or "", time.time() - t0


def run() -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not set")

    openai_client = OpenAI()
    files = sorted(AUDIO_DIR.glob("*.m4a"))
    if not files:
        raise SystemExit(f"No .m4a files found under {AUDIO_DIR}")

    results = []
    for path in files:
        name = path.stem
        print(f"\n=== {name} ===", flush=True)

        try:
            transcript, whisper_s = transcribe(openai_client, path)
            print(f"  whisper: {whisper_s:.2f}s, {len(transcript)} chars")
            print(f"  text: {transcript[:200]}")
        except Exception as e:
            print(f"  WHISPER FAILED: {e}")
            results.append({"name": name, "error": f"whisper: {e}"})
            continue

        try:
            t0 = time.time()
            extracted = extract_incident(transcript, site=DEFAULT_SITE)
            extract_s = time.time() - t0
            print(f"  claude: {extract_s:.2f}s, clients={len(extracted.get('clients', []))}")
        except Exception as e:
            print(f"  CLAUDE FAILED: {e}")
            results.append({
                "name": name,
                "transcript": transcript,
                "whisper_seconds": whisper_s,
                "error": f"claude: {e}",
            })
            continue

        results.append({
            "name": name,
            "transcript": transcript,
            "whisper_seconds": round(whisper_s, 3),
            "extract_seconds": round(extract_s, 3),
            "extracted": extracted,
        })

    summary = {
        "model_whisper": WHISPER_MODEL,
        "model_claude": os.getenv("AI_MODEL", "from app.json"),
        "n_files": len(files),
        "n_success": sum(1 for r in results if "error" not in r),
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {RESULTS_PATH}")
    return summary


if __name__ == "__main__":
    run()
