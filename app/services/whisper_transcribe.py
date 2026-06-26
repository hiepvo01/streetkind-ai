"""
Audio transcription via OpenAI Whisper.

Used as a quality-improvement pass over the browser's Web Speech API output:
the browser produces live text (instant feedback), then once recording stops
the same blob is sent here for a higher-accuracy re-transcription. The
frontend swaps the text in once this returns.

The client points at one of three backends, in order of preference:
  1. Azure AI Foundry, native Azure OpenAI route - set WHISPER_BASE_URL and
     WHISPER_API_VERSION (mirrors how ai_extractor talks to AnthropicFoundry).
  2. Azure AI Foundry / any OpenAI-compatible gateway - set WHISPER_BASE_URL
     only (e.g. https://<resource>.services.ai.azure.com/openai/v1/).
  3. Plain api.openai.com - set neither; just provide the key.
The key comes from WHISPER_API_KEY, falling back to OPENAI_API_KEY.

Disabled when no key is set - callers get None back and should fall back to
the live Web Speech text.
"""

import io
import logging
import os

logger = logging.getLogger(__name__)

# Whisper model, or the Azure deployment name when running on Foundry.
# Defaults to whisper-1 (legacy, stable). "gpt-4o-transcribe" /
# "gpt-4o-mini-transcribe" are also valid on api.openai.com.
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")

_client = None


def _get_api_key() -> str | None:
    # Prefer a Whisper-specific key (Foundry), fall back to the generic one.
    return os.getenv("WHISPER_API_KEY") or os.getenv("OPENAI_API_KEY")


def is_enabled() -> bool:
    return bool(_get_api_key())


def _get_client():
    """
    Build (and cache) the OpenAI client. Routes to Azure Foundry when
    WHISPER_BASE_URL is set, mirroring ai_extractor._get_client(); otherwise
    talks to api.openai.com.
    """
    global _client
    if _client is not None:
        return _client

    api_key = _get_api_key()
    base_url = os.getenv("WHISPER_BASE_URL")
    api_version = os.getenv("WHISPER_API_VERSION")

    if base_url and api_version:
        # Native Azure OpenAI route - needs an api-version; "model" below is
        # the Azure deployment name (set via WHISPER_MODEL).
        from openai import AzureOpenAI

        _client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,
            api_version=api_version,
        )
    elif base_url:
        # OpenAI-compatible gateway (incl. Foundry's /openai/v1/ surface).
        from openai import OpenAI

        _client = OpenAI(api_key=api_key, base_url=base_url)
    else:
        from openai import OpenAI

        _client = OpenAI(api_key=api_key)  # api.openai.com
    return _client


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

    # Build the client lazily so the rest of the backend doesn't pay the
    # import cost (or fail on a missing openai package) when Whisper is off.
    try:
        client = _get_client()
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
