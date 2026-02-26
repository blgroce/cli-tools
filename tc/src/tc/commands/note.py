"""Note commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ..db import get_connection, log_event
from ..main import ExitCode
from ..models import Note
from ..output import get_settings, emit_success, emit_error


def add_note(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    content: str = typer.Argument(..., help="Note content"),
    pin: bool = typer.Option(False, "--pin", help="Pin this note"),
) -> None:
    """Add a note to a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    cursor = conn.execute(
        "INSERT INTO notes (transaction_id, content, is_pinned) VALUES (?, ?, ?)",
        (txn_id, content, int(pin)),
    )
    note_id = cursor.lastrowid
    conn.commit()

    log_event(conn, txn_id, "note_added", content[:100])
    conn.close()

    emit_success({"id": note_id, "transaction_id": txn_id}, settings, text=f"Note #{note_id} added to transaction #{txn_id}")


def notes(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    limit: int = typer.Option(20, "--limit", help="Max notes to show"),
) -> None:
    """List notes for a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    rows = conn.execute(
        "SELECT * FROM notes WHERE transaction_id = ? ORDER BY is_pinned DESC, created_at DESC LIMIT ?",
        (txn_id, limit),
    ).fetchall()
    conn.close()

    note_list = [Note.from_row(r) for r in rows]

    if settings.format == "text":
        if not note_list:
            print(f"No notes on transaction #{txn_id}")
            raise typer.Exit(ExitCode.SUCCESS)
        console = Console()
        console.print(f"\n[bold]Notes — Transaction #{txn_id}[/bold]\n")
        for n in note_list:
            pin_icon = "[yellow]*[/yellow] " if n.is_pinned else ""
            console.print(f"  {pin_icon}[dim]#{n.id} {n.created_at}[/dim]")
            console.print(f"  {n.content}\n")
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([n.to_dict() for n in note_list], settings)
