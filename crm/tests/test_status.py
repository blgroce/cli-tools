"""Tests for crm status command."""
from __future__ import annotations

import json

from crm.main import app


def test_status_with_data(runner, seeded_db):
    """Status should return dashboard metrics."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    data = json.loads(result.output)

    assert "active_deals" in data["data"]
    assert "pipeline_deals" in data["data"]
    assert "overdue_followups" in data["data"]
    assert "upcoming_followups" in data["data"]
    assert "recent_interactions" in data["data"]
    assert "company_counts" in data["data"]


def test_status_pipeline_counts(runner, seeded_db):
    """Pipeline should include non-closed deals."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Seeded deal is in 'proposal' stage (non-closed)
    assert data["data"]["pipeline_deals"]["count"] >= 1


def test_status_company_counts(runner, seeded_db):
    """Company counts should reflect seeded data."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "active" in data["data"]["company_counts"]


def test_status_empty_db(runner, tmp_db):
    """Status on empty DB should return zero counts."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["active_deals"]["count"] == 0
    assert data["data"]["pipeline_deals"]["count"] == 0
    assert data["data"]["overdue_followups"] == 0
    assert data["data"]["upcoming_followups"] == 0
    assert data["data"]["recent_interactions"] == []
    assert data["data"]["company_counts"] == {}


def test_status_overdue_followups(runner, seeded_db):
    """Overdue followups should be counted (seeded data has past followup)."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["overdue_followups"] >= 1
