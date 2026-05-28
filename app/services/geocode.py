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


# In-process only: under gunicorn/uvicorn multi-worker, each worker has its own
# dicts so effective cache hit rate and rate limits scale ~linearly with workers.
# Use Redis (or similar) if you need a single global cap or shared cache.
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
        "extratags": "1",
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

    addr = data.get("address") or {}
    # extratags contains OSM-tagged addr:street / addr:housenumber on POIs —
    # more accurate than Nominatim's road interpolation for businesses/buildings.
    extratags = data.get("extratags") or {}
    parts: list[str] = []

    # Named place at the pin (park, building, venue, etc.).
    # Present when the pin is not directly on a named road.
    place = (
        addr.get("amenity")
        or addr.get("leisure")
        or addr.get("tourism")
        or addr.get("building")
        or addr.get("historic")
        or addr.get("natural")
        or addr.get("man_made")
        or ""
    )

    # Prefer explicitly OSM-tagged street address (addr:street / addr:housenumber)
    # over Nominatim's road-network interpolation. Tagged values are set by OSM
    # mappers from the actual signage and are typically correct even when the
    # interpolated road snaps to the wrong nearby street.
    tagged_street = extratags.get("addr:street") or ""
    tagged_num = extratags.get("addr:housenumber") or ""

    # Interpolated road (fallback when no explicit OSM address tags)
    interp_num = addr.get("house_number", "")
    interp_road = (
        addr.get("road")
        or addr.get("pedestrian")
        or addr.get("path")
        or addr.get("footway")
        or ""
    )

    if tagged_street:
        # Use OSM-tagged address — most accurate for businesses / mapped buildings
        num_part = tagged_num or interp_num
        street = f"{num_part} {tagged_street}".strip() if num_part else tagged_street
        parts.append(f"{place}, {street}" if place else street)
    elif interp_road:
        street = f"{interp_num} {interp_road}".strip() if interp_num else interp_road
        parts.append(f"{place}, {street}" if place else street)
    elif place:
        # No road at all — use the place name alone (park interior, open space)
        parts.append(place)

    # Locality: prefer the most specific available
    for key in ("suburb", "neighbourhood", "quarter", "village", "town", "city"):
        if addr.get(key):
            parts.append(addr[key])
            break

    # State + postcode
    state = addr.get("state", "")
    postcode = addr.get("postcode", "")
    if state and postcode:
        parts.append(f"{state} {postcode}")
    elif state or postcode:
        parts.append(state or postcode)

    address = ", ".join(p for p in parts if p)

    # Final fallback to display_name if structured fields produced nothing
    if not address:
        address = (data.get("display_name") or "").strip()

    result = ReverseGeocodeResult(
        address=address,
        latitude=float(lat),
        longitude=float(lon),
        raw=data,
    )

    if ttl > 0:
        _cache[key] = (time.time(), result)

    return result

