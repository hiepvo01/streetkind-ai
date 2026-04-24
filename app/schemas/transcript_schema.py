"""
Schema for voice transcripts linked to incident reports.

Transcripts are stored at `transcripts/{transcriptId}` in Firebase RTDB.
The incident they belong to references them via `incidentForms/{id}/transcriptIds`.
Audio blobs live in Firebase Storage at `audio/{incidentId}/{transcriptId}.webm`.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ExtractionMeta(BaseModel):
    """AI extraction bookkeeping - useful for cost/quality analysis later."""
    model: str = ""
    tokensInput: int = 0
    tokensOutput: int = 0
    latencyMs: int = 0


class TranscriptSchema(BaseModel):
    """Matches the transcripts/{transcriptId} node."""

    incidentId: str = ""
    text: str = ""
    audioUrl: str = ""
    audioDurationMs: int = 0
    extractionMeta: ExtractionMeta = Field(default_factory=ExtractionMeta)
