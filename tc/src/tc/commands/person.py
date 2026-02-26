"""People management commands."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..config import VALID_PERSON_ROLES
from ..db import get_connection, log_event
from ..main import ExitCode
from ..models import Person
from ..output import get_settings, emit_success, emit_error


def add_person(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    role: str = typer.Option(..., "--role", help="Role: buyer/seller/buyer_agent/listing_agent/lender_contact/title_contact/inspector/appraiser/other"),
    name: str = typer.Option(..., "--name"),
    email: Optional[str] = typer.Option(None, "--email"),
    phone: Optional[str] = typer.Option(None, "--phone"),
    company: Optional[str] = typer.Option(None, "--company"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Add a person to a transaction."""
    settings = get_settings(ctx)

    if role not in VALID_PERSON_ROLES:
        emit_error(f"Invalid role: {role}. Must be one of: {', '.join(sorted(VALID_PERSON_ROLES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    conn = get_connection()

    # Verify transaction exists
    txn = conn.execute("SELECT id, address FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    cursor = conn.execute(
        "INSERT INTO people (transaction_id, role, name, email, phone, company, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (txn_id, role, name, email, phone, company, notes),
    )
    person_id = cursor.lastrowid
    conn.commit()

    log_event(conn, txn_id, "person_added", f"Added {role}: {name}")
    conn.close()

    data = {"id": person_id, "transaction_id": txn_id, "role": role, "name": name}
    emit_success(data, settings, text=f"Added {role} '{name}' to transaction #{txn_id}")


def people(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
) -> None:
    """List all people on a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    # Verify transaction exists
    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    rows = conn.execute(
        "SELECT * FROM people WHERE transaction_id = ? ORDER BY role, name", (txn_id,)
    ).fetchall()
    conn.close()

    persons = [Person.from_row(r) for r in rows]

    if settings.format == "text":
        if not persons:
            print(f"No people on transaction #{txn_id}")
            raise typer.Exit(ExitCode.SUCCESS)
        table = Table(title=f"People — Transaction #{txn_id}")
        table.add_column("ID", style="bold")
        table.add_column("Role")
        table.add_column("Name")
        table.add_column("Email")
        table.add_column("Phone")
        table.add_column("Company")
        for p in persons:
            table.add_row(str(p.id), p.role, p.name, p.email or "-", p.phone or "-", p.company or "-")
        Console().print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([p.to_dict() for p in persons], settings)


def update_person(
    ctx: typer.Context,
    person_id: int = typer.Argument(..., help="Person ID"),
    name: Optional[str] = typer.Option(None, "--name"),
    role: Optional[str] = typer.Option(None, "--role"),
    email: Optional[str] = typer.Option(None, "--email"),
    phone: Optional[str] = typer.Option(None, "--phone"),
    company: Optional[str] = typer.Option(None, "--company"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Update a person's details."""
    settings = get_settings(ctx)

    if role and role not in VALID_PERSON_ROLES:
        emit_error(f"Invalid role: {role}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    conn = get_connection()
    row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Person #{person_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    updates: dict = {}
    for col, val in {"name": name, "role": role, "email": email, "phone": phone, "company": company, "notes": notes}.items():
        if val is not None:
            updates[col] = val

    if not updates:
        conn.close()
        emit_error("No fields to update", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE people SET {set_clause} WHERE id = ?", [*updates.values(), person_id])
    conn.commit()

    log_event(conn, row["transaction_id"], "person_updated", f"Updated {row['role']} '{row['name']}': {', '.join(updates.keys())}")
    conn.close()

    emit_success({"id": person_id, "updated": list(updates.keys())}, settings, text=f"Updated person #{person_id}: {', '.join(updates.keys())}")
