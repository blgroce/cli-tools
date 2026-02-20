"""Tests for crm log commands (call, email, meeting, note)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from crm.main import app
from crm.commands.log import _parse_followup


def test_log_call(runner, seeded_db):
    """Log a phone call interaction."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Discussed Q1 targets",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["type"] == "call"
    assert data["data"]["summary"] == "Discussed Q1 targets"
    assert data["data"]["contact_name"] == "Alice Smith"


def test_log_email(runner, seeded_db):
    """Log an email interaction."""
    result = runner.invoke(app, [
        "log", "email", "Alice Smith",
        "--summary", "Sent proposal",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["type"] == "email"


def test_log_meeting(runner, seeded_db):
    """Log a meeting interaction."""
    result = runner.invoke(app, [
        "log", "meeting", "Alice Smith",
        "--summary", "Quarterly review",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["type"] == "meeting"


def test_log_note(runner, seeded_db):
    """Log a note interaction."""
    result = runner.invoke(app, [
        "log", "note", "Alice Smith",
        "--summary", "Important observations",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["type"] == "note"


def test_log_with_followup_days(runner, seeded_db):
    """Log with followup in Nd format."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Will follow up",
        "--followup", "7d",
        "--followup-note", "Check on proposal",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    expected = (datetime.now().date() + timedelta(days=7)).isoformat()
    assert data["data"]["followup_date"] == expected
    assert data["data"]["followup_note"] == "Check on proposal"


def test_log_with_followup_weeks(runner, seeded_db):
    """Log with followup in Nw format."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Weekly check-in",
        "--followup", "2w",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    expected = (datetime.now().date() + timedelta(weeks=2)).isoformat()
    assert data["data"]["followup_date"] == expected


def test_log_with_followup_iso_date(runner, seeded_db):
    """Log with followup as YYYY-MM-DD."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Specific date followup",
        "--followup", "2026-06-15",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["followup_date"] == "2026-06-15"


def test_log_with_date_override(runner, seeded_db):
    """Log with --date to override occurred_at."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Past call",
        "--date", "2026-01-01",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "2026-01-01" in data["data"]["occurred_at"]


def test_log_invalid_followup(runner, seeded_db):
    """Invalid followup format should error."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Bad followup",
        "--followup", "xyz",
    ])
    assert result.exit_code == 2


def test_log_invalid_date(runner, seeded_db):
    """Invalid date format should error."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Bad date",
        "--date", "not-a-date",
    ])
    assert result.exit_code == 2


def test_log_nonexistent_contact(runner, tmp_db):
    """Logging for a non-existent contact should error."""
    result = runner.invoke(app, [
        "log", "call", "Nobody",
        "--summary", "Hello",
    ])
    assert result.exit_code == 3


def test_log_auto_company_id(runner, seeded_db):
    """Interaction should auto-resolve company_id from contact."""
    result = runner.invoke(app, [
        "log", "call", "Alice Smith",
        "--summary", "Auto company test",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["company_id"] is not None
    assert data["data"]["company_name"] == "Acme Corp"


# Unit tests for _parse_followup
def test_parse_followup_days():
    """Nd format should add N days."""
    result = _parse_followup("5d")
    expected = (datetime.now().date() + timedelta(days=5)).isoformat()
    assert result == expected


def test_parse_followup_weeks():
    """Nw format should add N weeks."""
    result = _parse_followup("3w")
    expected = (datetime.now().date() + timedelta(weeks=3)).isoformat()
    assert result == expected


def test_parse_followup_iso():
    """ISO date should pass through."""
    assert _parse_followup("2026-12-25") == "2026-12-25"


def test_parse_followup_invalid():
    """Invalid format should return empty string."""
    assert _parse_followup("xyz") == ""
    assert _parse_followup("abc123") == ""
