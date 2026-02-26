"""Shared test fixtures for tc CLI tests."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tc.db import get_connection, get_db_path, init_db
from tc.main import app


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary test database and patch all imports."""
    db_path = tmp_path / "test_tc.db"

    patches = [
        patch("tc.db.get_db_path", return_value=db_path),
        patch("tc.commands.transaction.get_connection", lambda: get_connection(db_path)),
        patch("tc.commands.person.get_connection", lambda: get_connection(db_path)),
        patch("tc.commands.task.get_connection", lambda: get_connection(db_path)),
        patch("tc.commands.document.get_connection", lambda: get_connection(db_path)),
        patch("tc.commands.note.get_connection", lambda: get_connection(db_path)),
        patch("tc.commands.report.get_connection", lambda: get_connection(db_path)),
    ]

    for p in patches:
        p.start()

    init_db(get_connection(db_path))

    yield db_path

    for p in patches:
        p.stop()


@pytest.fixture()
def seeded_db(tmp_db):
    """Pre-seeded test data with one financed + HOA transaction."""
    conn = get_connection(tmp_db)
    conn.execute(
        """INSERT INTO transactions (
            id, address, city, status, type,
            effective_date, closing_date, option_period_days, option_period_end,
            sales_price, earnest_money, option_fee,
            is_financed, financing_amount, has_hoa, has_mud, is_pre_1978,
            is_seller_disclosure_exempt, is_cash_offer, is_new_construction
        ) VALUES (
            1, '123 Main St', 'Austin', 'active', 'buyer',
            '2026-03-01', '2026-04-15', 10, '2026-03-11',
            350000, 5000, 500,
            1, 280000, 1, 0, 0,
            0, 0, 0
        )"""
    )
    conn.execute(
        "INSERT INTO people (id, transaction_id, role, name, email) VALUES (1, 1, 'buyer', 'John Smith', 'john@example.com')"
    )
    conn.commit()
    conn.close()
    return tmp_db


def parse_json(result) -> dict:
    """Parse JSON output from CLI result."""
    return json.loads(result.output)
