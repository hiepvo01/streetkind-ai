"""
Audio transcription via OpenAI Whisper.

Used as a quality-improvement pass over the browser's Web Speech API output:
the browser produces live text (instant feedback), then once recording stops
the same blob is sent here for a higher-accuracy re-transcription. The
frontend swaps the text in once this returns.

Disabled when OPENAI_API_KEY is unset - callers get None back and should fall
back to the live Web Speech text.
"""

import io
import logging
import os

logger = logging.getLogger(__name__)

# Default to whisper-1 (legacy, stable). Override via WHISPER_MODEL env var.
# Newer "gpt-4o-transcribe" / "gpt-4o-mini-transcribe" models are also valid.
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")


def is_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str,
    *,
    language: str | None = "en",
    prompt: str | None = None,
) -> str | None:
    """
    Send audio bytes to OpenAI Whisper and return the transcribed text.
    Returns None if the API key isn't configured or the call fails;
    callers should fall back to whatever transcript text they had already.
    """
    if not is_enabled():
        return None

    # Imported lazily so the rest of the backend doesn't pay the import cost
    # when Whisper isn't enabled.
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed; cannot transcribe")
        return None

    # Whisper accepts a file-like with a name suffix it can use to detect
    # the format. Pass the same extension the audio was uploaded with.
    ext = "webm"
    ct = (content_type or "").lower()
    if "mp4" in ct or "m4a" in ct:
        ext = "m4a"
    elif "ogg" in ct:
        ext = "ogg"
    elif "mpeg" in ct or "mp3" in ct:
        ext = "mp3"

    buf = io.BytesIO(audio_bytes)
    buf.name = f"audio.{ext}"

    try:
        client = OpenAI()  # reads OPENAI_API_KEY from env
        kwargs = {"model": DEFAULT_MODEL, "file": buf}
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt
        response = client.audio.transcriptions.create(**kwargs)
        return getattr(response, "text", None) or None
    except Exception as e:
        logger.warning("Whisper transcription failed: %s", e)
        return None
