"""SQLite database connection, schema initialization, and migrations."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_DIR = Path.home() / ".local" / "share" / "crm"
DB_NAME = "crm.db"

SCHEMA_VERSION = 1


def get_db_path() -> Path:
    return DB_DIR / DB_NAME


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    if conn is None:
        conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            industry    TEXT,
            status      TEXT DEFAULT 'prospect',
            website     TEXT,
            notes       TEXT,
            created_at  DATETIME DEFAULT (datetime('now')),
            updated_at  DATETIME DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            company_id  INTEGER REFERENCES companies(id),
            role        TEXT,
            email       TEXT,
            phone       TEXT,
            tags        TEXT,
            notes       TEXT,
            created_at  DATETIME DEFAULT (datetime('now')),
            updated_at  DATETIME DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS interactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id      INTEGER NOT NULL REFERENCES contacts(id),
            company_id      INTEGER REFERENCES companies(id),
            type            TEXT NOT NULL,
            summary         TEXT NOT NULL,
            occurred_at     DATETIME DEFAULT (datetime('now')),
            followup_date   DATE,
            followup_note   TEXT,
            created_at      DATETIME DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS deals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            company_id  INTEGER NOT NULL REFERENCES companies(id),
            contact_id  INTEGER REFERENCES contacts(id),
            value       REAL,
            stage       TEXT DEFAULT 'lead',
            notes       TEXT,
            created_at  DATETIME DEFAULT (datetime('now')),
            updated_at  DATETIME DEFAULT (datetime('now'))
        );

        -- Auto-update triggers for updated_at
        CREATE TRIGGER IF NOT EXISTS companies_updated_at
            AFTER UPDATE ON companies
            FOR EACH ROW
            BEGIN
                UPDATE companies SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

        CREATE TRIGGER IF NOT EXISTS contacts_updated_at
            AFTER UPDATE ON contacts
            FOR EACH ROW
            BEGIN
                UPDATE contacts SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

        CREATE TRIGGER IF NOT EXISTS deals_updated_at
            AFTER UPDATE ON deals
            FOR EACH ROW
            BEGIN
                UPDATE deals SET updated_at = datetime('now') WHERE id = OLD.id;
            END;
    """)

    # Set schema version if not present
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()

    return conn
