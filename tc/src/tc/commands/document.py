"""Document tracking commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..config import VALID_DOC_TYPES, VALID_DOC_STATUSES
from ..db import get_connection, log_event
from ..main import ExitCode
from ..models import Document
from ..output import get_settings, emit_success, emit_error


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
        table.add_column("Notes")
        for d in doc_list:
            table.add_row(str(d.id), d.name, d.doc_type, d.status, (d.notes or "-")[:40])
        Console().print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([d.to_dict() for d in doc_list], settings)


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
