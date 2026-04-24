"""
Nominatim reverse-geocode proxy utilities.

We proxy requests to respect Nominatim's usage policy (User-Agent identification),
apply a small in-memory TTL cache, and rate-limit to avoid abusive traffic.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


@dataclass(frozen=True)
class ReverseGeocodeResult:
    address: str
    latitude: float
    longitude: float
    raw: dict[str, Any] | None = None


_cache: dict[str, tuple[float, ReverseGeocodeResult]] = {}
_rate: dict[str, list[float]] = {}


def _cache_ttl_s() -> int:
    return int(os.getenv("NOMINATIM_CACHE_TTL_SECONDS", "86400"))


def _rate_limit_per_minute() -> int:
    return int(os.getenv("NOMINATIM_RATE_LIMIT_PER_MINUTE", "30"))


def _rate_limit_window_s() -> int:
    return 60


def _round_coord(x: float) -> float:
    # ~11m precision at equator; good enough for caching.
    return round(float(x), 4)


def _cache_key(lat: float, lon: float) -> str:
    return f"{_round_coord(lat)},{_round_coord(lon)}"


def _enforce_rate_limit(caller_key: str) -> None:
    now = time.time()
    window = _rate_limit_window_s()
    limit = _rate_limit_per_minute()
    times = _rate.get(caller_key, [])
    times = [t for t in times if (now - t) < window]
    if len(times) >= limit:
        raise ValueError("Rate limit exceeded for reverse geocoding")
    times.append(now)
    _rate[caller_key] = times


def reverse_geocode(
    *,
    lat: float,
    lon: float,
    caller_key: str,
    user_agent: str,
) -> ReverseGeocodeResult:
    """
    Reverse geocode coordinates via Nominatim.

    Raises ValueError for rate-limit or upstream issues.
    """
    ttl = _cache_ttl_s()
    key = _cache_key(lat, lon)
    if ttl > 0 and key in _cache:
        cached_at, cached = _cache[key]
        if (time.time() - cached_at) < ttl:
            return cached

    _enforce_rate_limit(caller_key)

    headers = {
        # Nominatim requires a valid User-Agent identifying the application.
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    params = {
        "format": "jsonv2",
        "lat": str(lat),
        "lon": str(lon),
        "addressdetails": "1",
        "zoom": "18",
    }

    try:
        resp = httpx.get(NOMINATIM_REVERSE_URL, params=params, headers=headers, timeout=10.0)
    except Exception as e:
        raise ValueError(f"Nominatim request failed: {e}") from e

    if resp.status_code != 200:
        raise ValueError(f"Nominatim error: HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception as e:
        raise ValueError(f"Nominatim returned invalid JSON: {e}") from e

    address = (data.get("display_name") or "").strip()
    if not address:
        # Fallback: build something from address fields if present.
        addr = data.get("address") or {}
        parts = [addr.get(k) for k in ("road", "suburb", "city", "state", "postcode") if addr.get(k)]
        address = ", ".join(parts)

    result = ReverseGeocodeResult(
        address=address,
        latitude=float(lat),
        longitude=float(lon),
        raw=data,
    )

    if ttl > 0:
        _cache[key] = (time.time(), result)

    return result

