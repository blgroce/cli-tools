"""Shared fixtures for CRM tests."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from crm.db import get_connection, init_db
from crm.main import app


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary database and patch get_connection everywhere."""
    db_path = tmp_path / "test_crm.db"

    def _patched_connection(db_path_arg=None):
        return get_connection(db_path)

    # Patch get_connection in every module that imports it
    patches = [
        patch("crm.db.get_db_path", return_value=db_path),
        patch("crm.commands.company.get_connection", side_effect=_patched_connection),
        patch("crm.commands.contact.get_connection", side_effect=_patched_connection),
        patch("crm.commands.log.get_connection", side_effect=_patched_connection),
        patch("crm.commands.deal.get_connection", side_effect=_patched_connection),
        patch("crm.commands.followup.get_connection", side_effect=_patched_connection),
        patch("crm.commands.search.get_connection", side_effect=_patched_connection),
        patch("crm.commands.status.get_connection", side_effect=_patched_connection),
    ]

    for p in patches:
        p.start()

    # Initialize schema
    conn = get_connection(db_path)
    init_db(conn)
    conn.close()

    yield db_path

    for p in patches:
        p.stop()


@pytest.fixture()
def runner():
    """Typer CLI test runner."""
    return CliRunner()


@pytest.fixture()
def seeded_db(tmp_db):
    """Database pre-seeded with sample data."""
    conn = get_connection(tmp_db)
    conn.execute(
        "INSERT INTO companies (name, industry, status) VALUES (?, ?, ?)",
        ("Acme Corp", "Technology", "active"),
    )
    conn.execute(
        "INSERT INTO contacts (name, company_id, email, role, tags) VALUES (?, ?, ?, ?, ?)",
        ("Alice Smith", 1, "alice@acme.com", "CTO", "tech,vip"),
    )
    conn.execute(
        """INSERT INTO interactions (contact_id, company_id, type, summary, occurred_at, followup_date, followup_note)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (1, 1, "call", "Discussed roadmap", "2026-01-15 10:00:00", "2026-01-20", "Follow up on proposal"),
    )
    conn.execute(
        "INSERT INTO deals (title, company_id, contact_id, value, stage) VALUES (?, ?, ?, ?, ?)",
        ("Acme Deal", 1, 1, 50000.0, "proposal"),
    )
    conn.commit()
    conn.close()
    return tmp_db
