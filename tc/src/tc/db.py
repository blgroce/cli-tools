"""SQLite database connection, schema initialization, and migrations."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_DIR = Path.home() / ".local" / "share" / "tc"
DB_NAME = "tc.db"

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

        -- ===== TRANSACTIONS =====
        CREATE TABLE IF NOT EXISTS transactions (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            address                     TEXT,
            city                        TEXT,
            county                      TEXT,
            zip                         TEXT,
            status                      TEXT NOT NULL DEFAULT 'draft',
            type                        TEXT,
            effective_date              DATE,
            closing_date                DATE,
            option_period_days          INTEGER,
            option_period_end           DATE,
            sales_price                 REAL,
            earnest_money               REAL,
            option_fee                  REAL,
            is_financed                 INTEGER DEFAULT 1,
            financing_amount            REAL,
            has_hoa                     INTEGER DEFAULT 0,
            has_mud                     INTEGER DEFAULT 0,
            is_pre_1978                 INTEGER DEFAULT 0,
            is_seller_disclosure_exempt INTEGER DEFAULT 0,
            is_cash_offer               INTEGER DEFAULT 0,
            is_new_construction         INTEGER DEFAULT 0,
            has_existing_survey         INTEGER,
            notes                       TEXT,
            created_at                  DATETIME DEFAULT (datetime('now')),
            updated_at                  DATETIME DEFAULT (datetime('now'))
        );

        -- ===== PEOPLE =====
        CREATE TABLE IF NOT EXISTS people (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id  INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            role            TEXT NOT NULL,
            name            TEXT NOT NULL,
            email           TEXT,
            phone           TEXT,
            company         TEXT,
            notes           TEXT,
            created_at      DATETIME DEFAULT (datetime('now')),
            updated_at      DATETIME DEFAULT (datetime('now'))
        );

        -- ===== TASKS =====
        CREATE TABLE IF NOT EXISTS tasks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id  INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            template_id     TEXT,
            title           TEXT NOT NULL,
            description     TEXT,
            phase           TEXT,
            group_id        TEXT,
            due_date        DATE,
            status          TEXT NOT NULL DEFAULT 'pending',
            completed_at    DATETIME,
            sort_order      INTEGER DEFAULT 0,
            depends_on      TEXT,
            is_conditional  INTEGER DEFAULT 0,
            condition_met   INTEGER DEFAULT 1,
            skip_reason     TEXT,
            created_at      DATETIME DEFAULT (datetime('now')),
            updated_at      DATETIME DEFAULT (datetime('now'))
        );

        -- ===== DOCUMENTS =====
        CREATE TABLE IF NOT EXISTS documents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id  INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            name            TEXT NOT NULL,
            doc_type        TEXT NOT NULL DEFAULT 'other',
            status          TEXT NOT NULL DEFAULT 'needed',
            file_path       TEXT,
            notes           TEXT,
            created_at      DATETIME DEFAULT (datetime('now')),
            updated_at      DATETIME DEFAULT (datetime('now'))
        );

        -- ===== NOTES =====
        CREATE TABLE IF NOT EXISTS notes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id  INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            content         TEXT NOT NULL,
            is_pinned       INTEGER DEFAULT 0,
            created_at      DATETIME DEFAULT (datetime('now'))
        );

        -- ===== TIMELINE EVENTS =====
        CREATE TABLE IF NOT EXISTS timeline_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id  INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,
            description     TEXT NOT NULL,
            created_at      DATETIME DEFAULT (datetime('now'))
        );

        -- ===== INDEXES =====
        CREATE INDEX IF NOT EXISTS idx_people_txn ON people(transaction_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_txn ON tasks(transaction_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
        CREATE INDEX IF NOT EXISTS idx_tasks_template ON tasks(template_id);
        CREATE INDEX IF NOT EXISTS idx_docs_txn ON documents(transaction_id);
        CREATE INDEX IF NOT EXISTS idx_notes_txn ON notes(transaction_id);
        CREATE INDEX IF NOT EXISTS idx_timeline_txn ON timeline_events(transaction_id);
        CREATE INDEX IF NOT EXISTS idx_txn_status ON transactions(status);

        -- ===== TRIGGERS =====
        CREATE TRIGGER IF NOT EXISTS transactions_updated_at
            AFTER UPDATE ON transactions
            FOR EACH ROW
            BEGIN
                UPDATE transactions SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

        CREATE TRIGGER IF NOT EXISTS people_updated_at
            AFTER UPDATE ON people
            FOR EACH ROW
            BEGIN
                UPDATE people SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

        CREATE TRIGGER IF NOT EXISTS tasks_updated_at
            AFTER UPDATE ON tasks
            FOR EACH ROW
            BEGIN
                UPDATE tasks SET updated_at = datetime('now') WHERE id = OLD.id;
            END;

        CREATE TRIGGER IF NOT EXISTS documents_updated_at
            AFTER UPDATE ON documents
            FOR EACH ROW
            BEGIN
                UPDATE documents SET updated_at = datetime('now') WHERE id = OLD.id;
            END;
    """)

    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()

    return conn


def log_event(conn: sqlite3.Connection, txn_id: int, event_type: str, description: str) -> None:
    """Insert a timeline event for a transaction."""
    conn.execute(
        "INSERT INTO timeline_events (transaction_id, event_type, description) VALUES (?, ?, ?)",
        (txn_id, event_type, description),
    )
    conn.commit()
