from unittest.mock import MagicMock

import pytest

from app.services import geocode


def setup_function():
    # Clear module-level caches between tests
    geocode._cache.clear()
    geocode._rate.clear()


def test_reverse_geocode_caches(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"display_name": "Test Address, Sydney NSW"}

    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        return mock_resp

    monkeypatch.setenv("NOMINATIM_CACHE_TTL_SECONDS", "9999")
    monkeypatch.setenv("NOMINATIM_RATE_LIMIT_PER_MINUTE", "9999")
    monkeypatch.setattr(geocode.httpx, "get", fake_get)

    a = geocode.reverse_geocode(lat=-33.8731, lon=151.2065, caller_key="u1", user_agent="ua")
    b = geocode.reverse_geocode(lat=-33.8731001, lon=151.2065002, caller_key="u1", user_agent="ua")

    assert a.address == "Test Address, Sydney NSW"
    assert b.address == "Test Address, Sydney NSW"
    assert calls["n"] == 1  # second call hits cache (rounded key)


def test_reverse_geocode_rate_limited(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"display_name": "X"}

    monkeypatch.setenv("NOMINATIM_CACHE_TTL_SECONDS", "0")
    monkeypatch.setenv("NOMINATIM_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setattr(geocode.httpx, "get", lambda *a, **k: mock_resp)

    geocode.reverse_geocode(lat=-33.0, lon=151.0, caller_key="u1", user_agent="ua")
    with pytest.raises(ValueError, match="Rate limit"):
        geocode.reverse_geocode(lat=-33.1, lon=151.1, caller_key="u1", user_agent="ua")

