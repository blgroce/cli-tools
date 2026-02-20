"""Tests for crm.db — schema initialization and database setup."""
from __future__ import annotations

from crm.db import get_connection, init_db, SCHEMA_VERSION


def test_init_db_creates_tables(tmp_db):
    """init_db should create all required tables."""
    conn = get_connection(tmp_db)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = sorted(r["name"] for r in rows)
    conn.close()

    assert "companies" in table_names
    assert "contacts" in table_names
    assert "interactions" in table_names
    assert "deals" in table_names
    assert "schema_version" in table_names


def test_schema_version_set(tmp_db):
    """Schema version should be recorded after init."""
    conn = get_connection(tmp_db)
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    assert row["version"] == SCHEMA_VERSION


def test_companies_columns(tmp_db):
    """Companies table should have all expected columns."""
    conn = get_connection(tmp_db)
    rows = conn.execute("PRAGMA table_info(companies)").fetchall()
    conn.close()
    columns = {r["name"] for r in rows}
    expected = {"id", "name", "industry", "status", "website", "notes", "created_at", "updated_at"}
    assert expected == columns


def test_contacts_columns(tmp_db):
    """Contacts table should have all expected columns."""
    conn = get_connection(tmp_db)
    rows = conn.execute("PRAGMA table_info(contacts)").fetchall()
    conn.close()
    columns = {r["name"] for r in rows}
    expected = {"id", "name", "company_id", "role", "email", "phone", "tags", "notes", "created_at", "updated_at"}
    assert expected == columns


def test_interactions_columns(tmp_db):
    """Interactions table should have all expected columns."""
    conn = get_connection(tmp_db)
    rows = conn.execute("PRAGMA table_info(interactions)").fetchall()
    conn.close()
    columns = {r["name"] for r in rows}
    expected = {"id", "contact_id", "company_id", "type", "summary", "occurred_at", "followup_date", "followup_note", "created_at"}
    assert expected == columns


def test_deals_columns(tmp_db):
    """Deals table should have all expected columns."""
    conn = get_connection(tmp_db)
    rows = conn.execute("PRAGMA table_info(deals)").fetchall()
    conn.close()
    columns = {r["name"] for r in rows}
    expected = {"id", "title", "company_id", "contact_id", "value", "stage", "notes", "created_at", "updated_at"}
    assert expected == columns


def test_foreign_key_enforcement(tmp_db):
    """Foreign keys should be enforced."""
    import sqlite3 as sqlite3_mod
    conn = get_connection(tmp_db)
    # Attempting to insert a contact with a non-existent company_id should fail
    try:
        conn.execute(
            "INSERT INTO contacts (name, company_id) VALUES (?, ?)",
            ("Bad Contact", 9999),
        )
        conn.commit()
        assert False, "Should have raised IntegrityError"
    except sqlite3_mod.IntegrityError:
        pass
    finally:
        conn.close()


def test_unique_company_name(tmp_db):
    """Company name should be unique."""
    import sqlite3 as sqlite3_mod
    conn = get_connection(tmp_db)
    conn.execute("INSERT INTO companies (name) VALUES (?)", ("UniqueTest",))
    conn.commit()
    try:
        conn.execute("INSERT INTO companies (name) VALUES (?)", ("UniqueTest",))
        conn.commit()
        assert False, "Should have raised IntegrityError for duplicate name"
    except sqlite3_mod.IntegrityError:
        pass
    finally:
        conn.close()


def test_idempotent_init(tmp_db):
    """Calling init_db twice should be safe."""
    conn = get_connection(tmp_db)
    init_db(conn)
    init_db(conn)
    # Should still work fine
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    conn.close()
    assert row["version"] == SCHEMA_VERSION
