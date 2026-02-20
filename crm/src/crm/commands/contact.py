"""Contact subcommands: add, list, show, edit, rm."""
from __future__ import annotations

import typer
from rich.table import Table
from rich.console import Console

from ..db import get_connection
from ..main import ExitCode
from ..models import Contact
from ..output import get_settings, emit_success, emit_error

app = typer.Typer(
    name="contact",
    help="Manage contacts.",
    no_args_is_help=True,
)


def _resolve_company(conn, name: str, settings):
    """Resolve a company name to its id. Emits error and exits if not found."""
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
    if not row:
        emit_error(
            f"Company '{name}' not found",
            settings,
            code="NOT_FOUND",
            exit_code=ExitCode.NOT_FOUND,
        )
    return row["id"]


@app.command()
def add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Contact name"),
    company: str | None = typer.Option(None, help="Company name"),
    email: str | None = typer.Option(None, help="Email address"),
    phone: str | None = typer.Option(None, help="Phone number"),
    role: str | None = typer.Option(None, help="Title or role"),
    tags: str | None = typer.Option(None, help="Comma-separated tags"),
    notes: str | None = typer.Option(None, help="Notes"),
) -> None:
    """Add a new contact."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        company_id = None
        if company:
            company_id = _resolve_company(conn, company, settings)

        cur = conn.execute(
            "INSERT INTO contacts (name, company_id, email, phone, role, tags, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, company_id, email, phone, role, tags, notes),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (cur.lastrowid,)).fetchone()
        contact = Contact.from_row(row)
        data = contact.to_dict()
        data["company_name"] = company

        emit_success(
            data,
            settings,
            text=f"Added contact: {contact.name} (id={contact.id})",
        )
    finally:
        conn.close()


@app.command("list")
def list_contacts(
    ctx: typer.Context,
    company: str | None = typer.Option(None, help="Filter by company name"),
    tag: str | None = typer.Option(None, help="Filter by tag"),
) -> None:
    """List contacts."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        query = """
            SELECT c.*, co.name AS company_name
            FROM contacts c
            LEFT JOIN companies co ON c.company_id = co.id
        """
        conditions: list[str] = []
        params: list = []

        if company:
            company_id = _resolve_company(conn, company, settings)
            conditions.append("c.company_id = ?")
            params.append(company_id)

        if tag:
            conditions.append("(',' || c.tags || ',') LIKE '%,' || ? || ',%'")
            params.append(tag)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY c.name"

        rows = conn.execute(query, params).fetchall()
        contacts = []
        for r in rows:
            d = Contact.from_row(r).to_dict()
            d["company_name"] = r["company_name"]
            contacts.append(d)

        if settings.format == "text":
            console = Console()
            table = Table(title="Contacts")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="bold")
            table.add_column("Company")
            table.add_column("Role")
            table.add_column("Email")
            for c in contacts:
                table.add_row(
                    str(c["id"]),
                    c["name"],
                    c["company_name"] or "",
                    c["role"] or "",
                    c["email"] or "",
                )
            console.print(table)
            raise typer.Exit(ExitCode.SUCCESS)

        emit_success(contacts, settings)
    finally:
        conn.close()


@app.command()
def show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Contact name"),
) -> None:
    """Show contact details."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT c.*, co.name AS company_name
            FROM contacts c
            LEFT JOIN companies co ON c.company_id = co.id
            WHERE c.name = ?
            """,
            (name,),
        ).fetchone()

        if not row:
            emit_error(
                f"Contact '{name}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        contact = Contact.from_row(row)
        data = contact.to_dict()
        data["company_name"] = row["company_name"]

        interactions_count = conn.execute(
            "SELECT COUNT(*) FROM interactions WHERE contact_id = ?", (contact.id,)
        ).fetchone()[0]
        data["interactions_count"] = interactions_count

        emit_success(
            data,
            settings,
            text=(
                f"Contact: {contact.name}\n"
                f"  Company: {row['company_name'] or '-'}\n"
                f"  Role:    {contact.role or '-'}\n"
                f"  Email:   {contact.email or '-'}\n"
                f"  Phone:   {contact.phone or '-'}\n"
                f"  Tags:    {contact.tags or '-'}\n"
                f"  Notes:   {contact.notes or '-'}\n"
                f"  Interactions: {interactions_count}"
            ),
        )
    finally:
        conn.close()


@app.command()
def edit(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Contact name to edit"),
    new_name: str | None = typer.Option(None, "--name", help="New name"),
    company: str | None = typer.Option(None, help="New company name"),
    email: str | None = typer.Option(None, help="New email"),
    phone: str | None = typer.Option(None, help="New phone"),
    role: str | None = typer.Option(None, help="New role"),
    tags: str | None = typer.Option(None, help="New tags"),
    notes: str | None = typer.Option(None, help="New notes"),
) -> None:
    """Edit a contact's fields."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM contacts WHERE name = ?", (name,)).fetchone()
        if not row:
            emit_error(
                f"Contact '{name}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        updates: list[str] = []
        params: list = []

        if new_name is not None:
            updates.append("name = ?")
            params.append(new_name)
        if company is not None:
            company_id = _resolve_company(conn, company, settings)
            updates.append("company_id = ?")
            params.append(company_id)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            emit_error(
                "No fields to update",
                settings,
                code="INVALID_INPUT",
                exit_code=ExitCode.INVALID_ARGS,
            )
            return

        params.append(row["id"])
        conn.execute(
            f"UPDATE contacts SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

        updated = conn.execute(
            """
            SELECT c.*, co.name AS company_name
            FROM contacts c
            LEFT JOIN companies co ON c.company_id = co.id
            WHERE c.id = ?
            """,
            (row["id"],),
        ).fetchone()
        contact = Contact.from_row(updated)
        data = contact.to_dict()
        data["company_name"] = updated["company_name"]

        emit_success(
            data,
            settings,
            text=f"Updated contact: {contact.name}",
        )
    finally:
        conn.close()


@app.command()
def rm(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Contact name to delete"),
) -> None:
    """Remove a contact and related interactions."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM contacts WHERE name = ?", (name,)).fetchone()
        if not row:
            emit_error(
                f"Contact '{name}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        contact_id = row["id"]

        # Clear contact reference on deals (contact_id is nullable)
        conn.execute("UPDATE deals SET contact_id = NULL WHERE contact_id = ?", (contact_id,))
        # Delete related interactions
        conn.execute("DELETE FROM interactions WHERE contact_id = ?", (contact_id,))
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()

        emit_success(
            {"id": contact_id, "name": name},
            settings,
            text=f"Deleted contact: {name}",
        )
    finally:
        conn.close()
