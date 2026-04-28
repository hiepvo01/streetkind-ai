"""Tests for incident narrative per-user rate limiter."""

import pytest

from app.services import narrative_rate_limit as nrl


def setup_function():
    nrl._rate.clear()


def test_narrative_rate_limit_allows_under_cap(monkeypatch):
    monkeypatch.setenv("INCIDENT_NARRATIVE_RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.setenv("INCIDENT_NARRATIVE_RATE_WINDOW_SECONDS", "60")

    nrl.enforce_incident_narrative_rate_limit("user-a")
    nrl.enforce_incident_narrative_rate_limit("user-a")
    nrl.enforce_incident_narrative_rate_limit("user-a")


def test_narrative_rate_limit_blocks_over_cap(monkeypatch):
    monkeypatch.setenv("INCIDENT_NARRATIVE_RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("INCIDENT_NARRATIVE_RATE_WINDOW_SECONDS", "60")

    nrl.enforce_incident_narrative_rate_limit("user-b")
    nrl.enforce_incident_narrative_rate_limit("user-b")
    with pytest.raises(ValueError, match="Rate limit"):
        nrl.enforce_incident_narrative_rate_limit("user-b")


def test_narrative_rate_limit_is_per_user(monkeypatch):
    monkeypatch.setenv("INCIDENT_NARRATIVE_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("INCIDENT_NARRATIVE_RATE_WINDOW_SECONDS", "60")

    nrl.enforce_incident_narrative_rate_limit("u1")
    with pytest.raises(ValueError, match="Rate limit"):
        nrl.enforce_incident_narrative_rate_limit("u1")
    nrl.enforce_incident_narrative_rate_limit("u2")
