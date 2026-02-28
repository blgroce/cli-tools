"""Tests for document commands including doc-search integration."""
import json
from unittest.mock import patch, MagicMock

from tc.main import app
from .conftest import parse_json


# ---- Existing document commands ----


def test_add_doc(runner, seeded_db):
    result = runner.invoke(app, [
        "add-doc", "1", "--name", "TAR-1901", "--type", "addendum", "--status", "received",
    ])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["success"] is True
    assert data["data"]["name"] == "TAR-1901"


def test_add_doc_invalid_type(runner, seeded_db):
    result = runner.invoke(app, [
        "add-doc", "1", "--name", "Bad", "--type", "bogus",
    ])
    assert result.exit_code != 0


def test_docs_empty(runner, seeded_db):
    result = runner.invoke(app, ["docs", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"] == []


def test_docs_with_records(runner, seeded_db):
    runner.invoke(app, ["add-doc", "1", "--name", "Contract", "--type", "contract", "--status", "received"])
    runner.invoke(app, ["add-doc", "1", "--name", "Survey", "--type", "survey", "--status", "needed"])
    result = runner.invoke(app, ["docs", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 2


def test_docs_filter_by_status(runner, seeded_db):
    runner.invoke(app, ["add-doc", "1", "--name", "Contract", "--type", "contract", "--status", "received"])
    runner.invoke(app, ["add-doc", "1", "--name", "Survey", "--type", "survey", "--status", "needed"])
    result = runner.invoke(app, ["docs", "1", "--status", "needed"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Survey"


def test_docs_has_text_flag(runner, seeded_db):
    """Documents with doc_search_id should show has_text=true in JSON."""
    from tc.db import get_connection
    conn = get_connection(seeded_db)
    conn.execute(
        "INSERT INTO documents (transaction_id, name, doc_type, status, doc_search_id) VALUES (1, 'Linked', 'contract', 'received', 42)"
    )
    conn.execute(
        "INSERT INTO documents (transaction_id, name, doc_type, status) VALUES (1, 'Unlinked', 'other', 'needed')"
    )
    conn.commit()
    conn.close()

    result = runner.invoke(app, ["docs", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 2

    linked = next(d for d in data["data"] if d["name"] == "Linked")
    unlinked = next(d for d in data["data"] if d["name"] == "Unlinked")
    assert linked["has_text"] is True
    assert linked["doc_search_id"] == 42
    assert unlinked["has_text"] is False
    assert unlinked["doc_search_id"] is None


def test_docs_text_mode_shows_text_badge(runner, seeded_db):
    """In text mode, linked documents show [text] badge."""
    from tc.db import get_connection
    conn = get_connection(seeded_db)
    conn.execute(
        "INSERT INTO documents (transaction_id, name, doc_type, status, doc_search_id) VALUES (1, 'Contract', 'contract', 'received', 10)"
    )
    conn.commit()
    conn.close()

    result = runner.invoke(app, ["--format", "text", "docs", "1"])
    assert result.exit_code == 0
    assert "yes" in result.output


def test_update_doc(runner, seeded_db):
    runner.invoke(app, ["add-doc", "1", "--name", "Contract", "--type", "contract"])
    result = runner.invoke(app, ["update-doc", "1", "--status", "reviewed"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert "status" in data["data"]["updated"]


# ---- doc-search integration commands ----


def _mock_subprocess_run(args, **kwargs):
    """Mock subprocess.run for doc-search commands."""
    mock_result = MagicMock()
    # Find the subcommand — skip "doc-search" and any global flags (--format, json, etc.)
    subcmds = {"ingest", "show", "ask", "search", "list", "delete"}
    cmd = next((a for a in args if a in subcmds), "")

    if cmd == "ingest":
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "success": True,
            "data": {
                "id": 99,
                "name": "test-doc",
                "page_count": 5,
                "char_count": 2000,
                "tags": "tc,txn-1",
            }
        })
        mock_result.stderr = ""
    elif cmd == "show":
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "success": True,
            "data": {
                "id": 99,
                "name": "test-doc",
                "page_count": 5,
                "char_count": 2000,
                "text": "Full document text here...",
                "form_fields": {
                    "Sales Price": "$350,000",
                    "Option Period": "10 days",
                    "Earnest Money": "$5,000",
                },
            }
        })
        mock_result.stderr = ""
    elif cmd == "ask":
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "success": True,
            "data": {
                "document_id": 99,
                "document_name": "test-doc",
                "question": args[args.index("ask") + 1] if "ask" in args else "",
                "answer": "The option period is 10 days.",
            }
        })
        mock_result.stderr = ""
    else:
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = json.dumps({"error": True, "code": "NOT_FOUND", "message": "Unknown command"})

    return mock_result


def _mock_subprocess_fail(args, **kwargs):
    """Mock subprocess.run that always fails."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = json.dumps({"error": True, "code": "EXTRACTION_ERROR", "message": "PDF extraction failed"})
    return mock_result


class TestIngestDoc:
    def test_ingest_success(self, runner, seeded_db, tmp_path):
        pdf = tmp_path / "contract.pdf"
        pdf.write_text("fake pdf content")

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            result = runner.invoke(app, [
                "ingest-doc", "1", str(pdf), "--type", "contract", "--name", "Purchase Contract",
            ])

        assert result.exit_code == 0
        data = parse_json(result)
        assert data["success"] is True
        assert data["data"]["doc_search_id"] == 99
        assert data["data"]["page_count"] == 5
        assert data["data"]["name"] == "Purchase Contract"

    def test_ingest_creates_tc_doc_record(self, runner, seeded_db, tmp_path):
        pdf = tmp_path / "contract.pdf"
        pdf.write_text("fake pdf content")

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            runner.invoke(app, ["ingest-doc", "1", str(pdf), "--type", "contract"])

        # Verify the doc record exists in tc
        result = runner.invoke(app, ["docs", "1"])
        data = parse_json(result)
        assert len(data["data"]) == 1
        assert data["data"][0]["doc_search_id"] == 99
        assert data["data"][0]["doc_type"] == "contract"
        assert data["data"][0]["status"] == "received"

    def test_ingest_default_name_from_filename(self, runner, seeded_db, tmp_path):
        pdf = tmp_path / "Smith-Jones-Contract.pdf"
        pdf.write_text("fake pdf content")

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            result = runner.invoke(app, ["ingest-doc", "1", str(pdf)])

        data = parse_json(result)
        assert data["data"]["name"] == "Smith-Jones-Contract"

    def test_ingest_file_not_found(self, runner, seeded_db):
        result = runner.invoke(app, ["ingest-doc", "1", "/nonexistent/file.pdf"])
        assert result.exit_code != 0

    def test_ingest_txn_not_found(self, runner, seeded_db, tmp_path):
        pdf = tmp_path / "contract.pdf"
        pdf.write_text("fake pdf content")

        result = runner.invoke(app, ["ingest-doc", "999", str(pdf)])
        assert result.exit_code != 0

    def test_ingest_doc_search_failure(self, runner, seeded_db, tmp_path):
        pdf = tmp_path / "contract.pdf"
        pdf.write_text("fake pdf content")

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_fail):
            result = runner.invoke(app, ["ingest-doc", "1", str(pdf)])

        assert result.exit_code != 0

    def test_ingest_invalid_doc_type(self, runner, seeded_db, tmp_path):
        pdf = tmp_path / "contract.pdf"
        pdf.write_text("fake pdf content")

        result = runner.invoke(app, ["ingest-doc", "1", str(pdf), "--type", "bogus"])
        assert result.exit_code != 0


class TestLinkDoc:
    def test_link_success(self, runner, seeded_db):
        # Create a tc document first
        runner.invoke(app, ["add-doc", "1", "--name", "Contract", "--type", "contract", "--status", "received"])

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            result = runner.invoke(app, ["link-doc", "1", "99"])

        assert result.exit_code == 0
        data = parse_json(result)
        assert data["data"]["doc_search_id"] == 99

        # Verify the link persists
        docs_result = runner.invoke(app, ["docs", "1"])
        docs_data = parse_json(docs_result)
        assert docs_data["data"][0]["doc_search_id"] == 99

    def test_link_already_linked(self, runner, seeded_db):
        """Can't re-link a document that's already linked."""
        from tc.db import get_connection
        conn = get_connection(seeded_db)
        conn.execute(
            "INSERT INTO documents (id, transaction_id, name, doc_type, status, doc_search_id) VALUES (1, 1, 'Already Linked', 'contract', 'received', 42)"
        )
        conn.commit()
        conn.close()

        result = runner.invoke(app, ["link-doc", "1", "99"])
        assert result.exit_code != 0

    def test_link_doc_not_found(self, runner, seeded_db):
        result = runner.invoke(app, ["link-doc", "999", "99"])
        assert result.exit_code != 0

    def test_link_doc_search_not_found(self, runner, seeded_db):
        runner.invoke(app, ["add-doc", "1", "--name", "Contract", "--type", "contract"])

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_fail):
            result = runner.invoke(app, ["link-doc", "1", "999"])

        assert result.exit_code != 0


class TestAskDoc:
    def _seed_linked_doc(self, seeded_db, ds_id=99, doc_type="contract", name="Contract"):
        from tc.db import get_connection
        conn = get_connection(seeded_db)
        conn.execute(
            "INSERT INTO documents (transaction_id, name, doc_type, status, doc_search_id) VALUES (1, ?, ?, 'received', ?)",
            (name, doc_type, ds_id),
        )
        conn.commit()
        conn.close()

    def test_default_returns_form_fields_only(self, runner, seeded_db):
        """Default mode (no --deep) returns form fields without LLM call."""
        self._seed_linked_doc(seeded_db)

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run) as mock_run:
            result = runner.invoke(app, ["ask-doc", "1", "What is the option period?"])

        assert result.exit_code == 0
        data = parse_json(result)
        assert data["success"] is True
        assert data["data"]["mode"] == "fields"
        assert data["data"]["question"] == "What is the option period?"
        assert "form_fields" in data["data"]
        assert data["data"]["form_fields"]["Contract"]["Option Period"] == "10 days"
        # Should NOT have an answer key (no LLM call)
        assert "answer" not in data["data"]
        # Should only have called doc-search show, not ask
        all_args = [call[0][0] for call in mock_run.call_args_list]
        assert any("show" in a for a in all_args)
        assert not any("ask" in a for a in all_args)

    def test_deep_returns_llm_answer_and_form_fields(self, runner, seeded_db):
        """--deep mode returns LLM answer plus form fields."""
        self._seed_linked_doc(seeded_db)

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run) as mock_run:
            result = runner.invoke(app, ["ask-doc", "1", "What is the option period?", "--deep"])

        assert result.exit_code == 0
        data = parse_json(result)
        assert data["data"]["mode"] == "deep"
        assert "answer" in data["data"]
        assert "10 days" in data["data"]["answer"]
        assert "form_fields" in data["data"]
        assert data["data"]["form_fields"]["Contract"]["Option Period"] == "10 days"
        # Should have called both show and ask
        all_args = [call[0][0] for call in mock_run.call_args_list]
        assert any("show" in a for a in all_args)
        assert any("ask" in a for a in all_args)

    def test_filter_by_doc_type(self, runner, seeded_db):
        """Filter documents by type when asking."""
        self._seed_linked_doc(seeded_db, ds_id=99, doc_type="contract", name="Contract")
        from tc.db import get_connection
        conn = get_connection(seeded_db)
        conn.execute(
            "INSERT INTO documents (transaction_id, name, doc_type, status, doc_search_id) VALUES (1, 'Survey', 'survey', 'received', 100)"
        )
        conn.commit()
        conn.close()

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            result = runner.invoke(app, ["ask-doc", "1", "Sales price?", "--doc-type", "contract"])

        data = parse_json(result)
        assert len(data["data"]["documents"]) == 1
        assert data["data"]["documents"][0]["doc_type"] == "contract"

    def test_no_linked_docs(self, runner, seeded_db):
        """Should error when no documents have searchable text."""
        result = runner.invoke(app, ["ask-doc", "1", "What is the price?"])
        assert result.exit_code != 0

    def test_txn_not_found(self, runner, seeded_db):
        result = runner.invoke(app, ["ask-doc", "999", "What is the price?"])
        assert result.exit_code != 0

    def test_deep_text_mode(self, runner, seeded_db):
        """Text mode with --deep should show Q&A format with answer."""
        self._seed_linked_doc(seeded_db)

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            result = runner.invoke(app, ["--format", "text", "ask-doc", "1", "What is the option period?", "--deep"])

        assert result.exit_code == 0
        assert "Q:" in result.output
        assert "A:" in result.output
        assert "10 days" in result.output

    def test_fields_text_mode_no_answer(self, runner, seeded_db):
        """Text mode without --deep should show form fields but no answer."""
        self._seed_linked_doc(seeded_db)

        with patch("tc.commands.document.subprocess.run", side_effect=_mock_subprocess_run):
            result = runner.invoke(app, ["--format", "text", "ask-doc", "1", "What is the option period?"])

        assert result.exit_code == 0
        assert "Q:" in result.output
        assert "A:" not in result.output
        assert "Form fields:" in result.output
        assert "Option Period" in result.output

    def test_deep_failure(self, runner, seeded_db):
        """--deep should report error if doc-search ask fails."""
        self._seed_linked_doc(seeded_db)

        def _show_ok_ask_fail(args, **kwargs):
            if args[1] == "show":
                return _mock_subprocess_run(args, **kwargs)
            return _mock_subprocess_fail(args, **kwargs)

        with patch("tc.commands.document.subprocess.run", side_effect=_show_ok_ask_fail):
            result = runner.invoke(app, ["ask-doc", "1", "What is the price?", "--deep"])

        assert result.exit_code != 0


class TestMigration:
    def test_v1_to_v2_migration(self, tmp_path):
        """Existing v1 databases should get doc_search_id column on init."""
        from tc.db import get_connection, init_db
        db_path = tmp_path / "migrate_test.db"
        conn = get_connection(db_path)

        # Create a v1 schema (no doc_search_id)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version (version) VALUES (1);
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at DATETIME DEFAULT (datetime('now')),
                updated_at DATETIME DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                doc_type TEXT NOT NULL DEFAULT 'other',
                status TEXT NOT NULL DEFAULT 'needed',
                file_path TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT (datetime('now')),
                updated_at DATETIME DEFAULT (datetime('now'))
            );
        """)
        conn.commit()

        # Verify no doc_search_id column yet
        cols = {r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()}
        assert "doc_search_id" not in cols

        conn.close()

        # Re-init should trigger migration
        with patch("tc.db.get_db_path", return_value=db_path):
            conn2 = init_db(get_connection(db_path))

        cols = {r[1] for r in conn2.execute("PRAGMA table_info(documents)").fetchall()}
        assert "doc_search_id" in cols

        version = conn2.execute("SELECT version FROM schema_version LIMIT 1").fetchone()[0]
        assert version == 2
        conn2.close()
