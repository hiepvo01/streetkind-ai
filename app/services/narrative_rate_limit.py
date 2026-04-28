"""
Per-user in-memory rate limit for POST /api/incident/narrative (LLM cost control).

Uses the same sliding-window pattern as geocode. Process-local: with multiple
workers, effective cap scales roughly with worker count until a shared store
(e.g. Redis) backs the limiter.
"""

from __future__ import annotations

import os
import time

_rate: dict[str, list[float]] = {}


def _window_s() -> int:
    return int(os.getenv("INCIDENT_NARRATIVE_RATE_WINDOW_SECONDS", "60"))


def _limit_per_window() -> int:
    return int(os.getenv("INCIDENT_NARRATIVE_RATE_LIMIT_PER_MINUTE", "10"))


def enforce_incident_narrative_rate_limit(caller_key: str) -> None:
    """
    Allow at most N requests per caller per window (default 10 per 60s).

    Raises:
        ValueError: with message containing "Rate limit" when exceeded.
    """
    now = time.time()
    window = _window_s()
    limit = _limit_per_window()
    times = _rate.get(caller_key, [])
    times = [t for t in times if (now - t) < window]
    if len(times) >= limit:
        raise ValueError("Rate limit exceeded for incident narrative generation")
    times.append(now)
    _rate[caller_key] = times
