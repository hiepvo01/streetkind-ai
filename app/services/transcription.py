"""
Speech-to-text service.

Primary: Web Speech API (runs in browser, zero cost)
Fallback: OpenAI Whisper (local, for offline use or higher accuracy)
"""

import os
from ..config import get_app_config


def transcribe_audio_file(audio_path: str) -> str:
    """
    Transcribe an audio file using local Whisper model.
    Used as fallback when browser Web Speech API is unavailable.
    """
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "Whisper not installed. Install with: pip install openai-whisper"
        )

    app = get_app_config()
    model_size = os.getenv("WHISPER_MODEL", app["whisper"]["default_model"])
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    return result["text"]
