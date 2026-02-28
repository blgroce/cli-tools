"""Document tracking commands with doc-search integration."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..config import VALID_DOC_TYPES, VALID_DOC_STATUSES
from ..db import get_connection, log_event
from ..main import ExitCode
from ..models import Document
from ..output import get_settings, emit_success, emit_error


def _run_doc_search(args: list[str]) -> dict:
    """Run a doc-search command and return parsed JSON output.

    Raises RuntimeError with the error message on failure.
    """
    result = subprocess.run(
        ["doc-search", "--format", "json", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        try:
            err = json.loads(result.stderr)
            msg = err.get("message", result.stderr.strip())
        except (json.JSONDecodeError, ValueError):
            msg = result.stderr.strip() or f"doc-search exited with code {result.returncode}"
        raise RuntimeError(msg)
    return json.loads(result.stdout)


def add_doc(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    name: str = typer.Option(..., "--name", help="Document name (e.g. TAR-1901, Seller's Disclosure)"),
    doc_type: str = typer.Option("other", "--type", help="Type: contract/addendum/disclosure/earnest_money/title/survey/inspection/closing/other"),
    status: str = typer.Option("needed", "--status", help="Status: needed/requested/received/reviewed/filed"),
    file_path: Optional[str] = typer.Option(None, "--file", help="Path to file if saved locally"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Track a document for a transaction."""
    settings = get_settings(ctx)

    if doc_type not in VALID_DOC_TYPES:
        emit_error(f"Invalid doc type: {doc_type}. Must be one of: {', '.join(sorted(VALID_DOC_TYPES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)
    if status not in VALID_DOC_STATUSES:
        emit_error(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_DOC_STATUSES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    conn = get_connection()
    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    cursor = conn.execute(
        "INSERT INTO documents (transaction_id, name, doc_type, status, file_path, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (txn_id, name, doc_type, status, file_path, notes),
    )
    doc_id = cursor.lastrowid
    conn.commit()

    log_event(conn, txn_id, "doc_added", f"Document: {name} ({doc_type}) — {status}")
    conn.close()

    emit_success({"id": doc_id, "transaction_id": txn_id, "name": name}, settings, text=f"Document '{name}' added to transaction #{txn_id} ({status})")


def docs(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    doc_type: Optional[str] = typer.Option(None, "--type", help="Filter by type"),
) -> None:
    """List documents for a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    query = "SELECT * FROM documents WHERE transaction_id = ?"
    params: list = [txn_id]

    if status:
        query += " AND status = ?"
        params.append(status)
    if doc_type:
        query += " AND doc_type = ?"
        params.append(doc_type)

    query += " ORDER BY doc_type, name"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    doc_list = [Document.from_row(r) for r in rows]

    if settings.format == "text":
        if not doc_list:
            print(f"No documents on transaction #{txn_id}")
            raise typer.Exit(ExitCode.SUCCESS)
        table = Table(title=f"Documents — Transaction #{txn_id}")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Text", justify="center")
        table.add_column("Notes")
        for d in doc_list:
            has_text = "yes" if d.doc_search_id else ""
            table.add_row(str(d.id), d.name, d.doc_type, d.status, has_text, (d.notes or "-")[:40])
        Console().print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    data = []
    for d in doc_list:
        dd = d.to_dict()
        dd["has_text"] = d.doc_search_id is not None
        data.append(dd)
    emit_success(data, settings)


def update_doc(
    ctx: typer.Context,
    doc_id: int = typer.Argument(..., help="Document ID"),
    status: Optional[str] = typer.Option(None, "--status"),
    name: Optional[str] = typer.Option(None, "--name"),
    doc_type: Optional[str] = typer.Option(None, "--type"),
    file_path: Optional[str] = typer.Option(None, "--file"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Update a document's status or details."""
    settings = get_settings(ctx)

    if status and status not in VALID_DOC_STATUSES:
        emit_error(f"Invalid status: {status}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)
    if doc_type and doc_type not in VALID_DOC_TYPES:
        emit_error(f"Invalid doc type: {doc_type}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Document #{doc_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    updates: dict = {}
    for col, val in {"status": status, "name": name, "doc_type": doc_type, "file_path": file_path, "notes": notes}.items():
        if val is not None:
            updates[col] = val

    if not updates:
        conn.close()
        emit_error("No fields to update", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE documents SET {set_clause} WHERE id = ?", [*updates.values(), doc_id])
    conn.commit()

    log_event(conn, row["transaction_id"], "doc_updated", f"Document '{row['name']}': {', '.join(f'{k}={v}' for k, v in updates.items())}")
    conn.close()

    emit_success({"id": doc_id, "updated": list(updates.keys())}, settings, text=f"Updated document #{doc_id}: {', '.join(updates.keys())}")


# --- doc-search integration commands ---


def ingest_doc(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    pdf_path: str = typer.Argument(..., help="Path to PDF file"),
    doc_type: str = typer.Option("other", "--type", help="Document type"),
    name: Optional[str] = typer.Option(None, "--name", help="Document name (defaults to filename)"),
    status: str = typer.Option("received", "--status", help="Initial status (default: received)"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Ingest a PDF via doc-search and link it to a transaction."""
    settings = get_settings(ctx)

    pdf = Path(pdf_path).expanduser().resolve()
    if not pdf.exists():
        emit_error(f"File not found: {pdf}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    if doc_type not in VALID_DOC_TYPES:
        emit_error(f"Invalid doc type: {doc_type}. Must be one of: {', '.join(sorted(VALID_DOC_TYPES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)
    if status not in VALID_DOC_STATUSES:
        emit_error(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_DOC_STATUSES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    doc_name = name or pdf.stem

    conn = get_connection()
    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    # Ingest via doc-search
    ds_args = ["ingest", str(pdf), "--name", doc_name, "--tags", f"tc,txn-{txn_id}"]
    try:
        ds_result = _run_doc_search(ds_args)
    except RuntimeError as e:
        conn.close()
        emit_error(f"doc-search ingest failed: {e}", settings, code="EXTERNAL_FAILURE", exit_code=ExitCode.EXTERNAL_FAILURE)

    ds_id = ds_result["data"]["id"]
    page_count = ds_result["data"].get("page_count")
    char_count = ds_result["data"].get("char_count")

    # Create tc document record linked to doc-search
    cursor = conn.execute(
        "INSERT INTO documents (transaction_id, name, doc_type, status, file_path, doc_search_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (txn_id, doc_name, doc_type, status, str(pdf), ds_id, notes),
    )
    doc_id = cursor.lastrowid
    conn.commit()

    log_event(conn, txn_id, "doc_ingested", f"Ingested '{doc_name}' ({doc_type}, {page_count} pages) — doc-search #{ds_id}")
    conn.close()

    result_data = {
        "id": doc_id,
        "transaction_id": txn_id,
        "name": doc_name,
        "doc_type": doc_type,
        "doc_search_id": ds_id,
        "page_count": page_count,
        "char_count": char_count,
    }
    text = f"Ingested '{doc_name}' ({page_count} pages) → tc doc #{doc_id}, doc-search #{ds_id}"
    emit_success(result_data, settings, text=text)


def link_doc(
    ctx: typer.Context,
    tc_doc_id: int = typer.Argument(..., help="TC document ID"),
    doc_search_id: int = typer.Argument(..., help="doc-search document ID"),
) -> None:
    """Link an existing tc document to a doc-search document."""
    settings = get_settings(ctx)

    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (tc_doc_id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Document #{tc_doc_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    if row["doc_search_id"] is not None:
        conn.close()
        emit_error(
            f"Document #{tc_doc_id} is already linked to doc-search #{row['doc_search_id']}. "
            "Update it with update-doc if needed.",
            settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS,
        )

    # Verify the doc-search document exists
    try:
        _run_doc_search(["show", str(doc_search_id)])
    except RuntimeError as e:
        conn.close()
        emit_error(f"doc-search document #{doc_search_id} not found: {e}", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    conn.execute("UPDATE documents SET doc_search_id = ? WHERE id = ?", (doc_search_id, tc_doc_id))
    conn.commit()

    log_event(conn, row["transaction_id"], "doc_linked", f"Linked '{row['name']}' → doc-search #{doc_search_id}")
    conn.close()

    emit_success(
        {"id": tc_doc_id, "doc_search_id": doc_search_id},
        settings,
        text=f"Linked document #{tc_doc_id} ('{row['name']}') → doc-search #{doc_search_id}",
    )


def ask_doc(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    question: str = typer.Argument(..., help="Question to ask about the documents"),
    doc_type: Optional[str] = typer.Option(None, "--doc-type", help="Filter by document type"),
    deep: bool = typer.Option(False, "--deep", help="Send full text to LLM for thorough analysis (slower, costs tokens)"),
) -> None:
    """Ask a question about documents in a transaction.

    Two-tier approach:
      Default — returns form fields only (fast, no LLM). The calling agent
      evaluates whether the form fields answer the question.

      --deep — sends full document text to LLM via doc-search ask. Use when
      form fields don't contain the answer. Also includes form fields.
    """
    settings = get_settings(ctx)

    conn = get_connection()
    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    # Find linked documents
    query = "SELECT * FROM documents WHERE transaction_id = ? AND doc_search_id IS NOT NULL"
    params: list = [txn_id]
    if doc_type:
        query += " AND doc_type = ?"
        params.append(doc_type)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        filter_msg = f" (type={doc_type})" if doc_type else ""
        emit_error(
            f"No documents with searchable text on transaction #{txn_id}{filter_msg}",
            settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND,
        )

    docs_info = []
    form_fields_collected: dict = {}

    # Always collect form fields from all matching documents
    for row in rows:
        ds_id = row["doc_search_id"]
        doc_entry = {
            "tc_doc_id": row["id"],
            "doc_search_id": ds_id,
            "name": row["name"],
            "doc_type": row["doc_type"],
        }
        try:
            show_result = _run_doc_search(["show", str(ds_id)])
            ff = show_result.get("data", {}).get("form_fields")
            if ff and isinstance(ff, dict) and len(ff) > 0:
                form_fields_collected[row["name"]] = ff
        except RuntimeError:
            pass  # doc-search show failed — skip form fields for this doc
        docs_info.append(doc_entry)

    result_data: dict = {
        "transaction_id": txn_id,
        "question": question,
        "documents": docs_info,
        "mode": "deep" if deep else "fields",
    }

    if form_fields_collected:
        result_data["form_fields"] = form_fields_collected

    # Tier 2: LLM Q&A (only with --deep)
    if deep:
        primary_ds_id = rows[0]["doc_search_id"]
        try:
            ask_result = _run_doc_search(["ask", question, "--doc", str(primary_ds_id)])
            result_data["answer"] = ask_result.get("data", {}).get("answer", "")
            result_data["source_document"] = docs_info[0]
        except RuntimeError as e:
            emit_error(f"doc-search ask failed: {e}", settings, code="EXTERNAL_FAILURE", exit_code=ExitCode.EXTERNAL_FAILURE)

    if settings.format == "text":
        lines = [f"Q: {question}", ""]
        if deep and "answer" in result_data:
            lines.append(f"A: {result_data['answer']}")
            lines.append("")
        if form_fields_collected:
            lines.append("Form fields:")
            for doc_name, ffields in form_fields_collected.items():
                lines.append(f"  [{doc_name}]")
                for k, v in ffields.items():
                    lines.append(f"    {k}: {v}")
        elif not deep:
            lines.append("No form fields found. Re-run with --deep for LLM analysis.")
        lines.append(f"\nDocuments: {', '.join(d['name'] for d in docs_info)}")
        print("\n".join(lines))
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success(result_data, settings)
