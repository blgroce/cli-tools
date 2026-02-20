"""Tests for crm followup commands."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from crm.db import get_connection
from crm.main import app


def test_followups_default_shows_overdue(runner, seeded_db):
    """Default followups should show overdue items (seeded data has past followup)."""
    result = runner.invoke(app, ["followups"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    # The seeded followup is 2026-01-20, which is in the past
    assert len(data["data"]) >= 1
    for item in data["data"]:
        assert item["followup_date"] <= datetime.now().date().isoformat()


def test_followups_week(runner, seeded_db):
    """--week should show followups due within 7 days."""
    # Add a followup due in 3 days
    conn = get_connection(seeded_db)
    future_date = (datetime.now().date() + timedelta(days=3)).isoformat()
    conn.execute(
        """INSERT INTO interactions (contact_id, company_id, type, summary, followup_date, followup_note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (1, 1, "call", "Future call", future_date, "Check back"),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(app, ["followups", "--week"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Should include both the overdue one and the upcoming one
    assert len(data["data"]) >= 2


def test_followups_all(runner, seeded_db):
    """--all should show all pending followups regardless of date."""
    # Add a followup far in the future
    conn = get_connection(seeded_db)
    far_future = (datetime.now().date() + timedelta(days=365)).isoformat()
    conn.execute(
        """INSERT INTO interactions (contact_id, company_id, type, summary, followup_date)
           VALUES (?, ?, ?, ?, ?)""",
        (1, 1, "note", "Far future", far_future),
    )
    conn.commit()
    conn.close()

    result = runner.invoke(app, ["followups", "--all"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    dates = [item["followup_date"] for item in data["data"]]
    assert far_future in dates


def test_followup_done(runner, seeded_db):
    """Done should clear followup_date and followup_note."""
    # Seeded interaction id=1 has a followup
    result = runner.invoke(app, ["followups", "done", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["followup_cleared"] is True

    # Verify followup is cleared
    conn = get_connection(seeded_db)
    row = conn.execute("SELECT followup_date, followup_note FROM interactions WHERE id = 1").fetchone()
    conn.close()
    assert row["followup_date"] is None
    assert row["followup_note"] is None


def test_followup_done_not_found(runner, tmp_db):
    """Done on non-existent interaction should error."""
    result = runner.invoke(app, ["followups", "done", "999"])
    assert result.exit_code == 3


def test_followups_empty(runner, tmp_db):
    """Followups with no data should return empty list."""
    result = runner.invoke(app, ["followups"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"] == []


def test_followup_days_overdue_field(runner, seeded_db):
    """Each followup result should include days_overdue."""
    result = runner.invoke(app, ["followups", "--all"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for item in data["data"]:
        assert "days_overdue" in item
