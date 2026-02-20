"""Search command: cross-entity search across all CRM tables."""
from __future__ import annotations

import typer
from rich.table import Table
from rich.console import Console

from ..db import get_connection
from ..main import ExitCode
from ..output import get_settings, emit_success


def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search term"),
) -> None:
    """Search across contacts, companies, interactions, and deals."""
    settings = get_settings(ctx)
    pattern = f"%{query}%"

    conn = get_connection()
    try:
        companies = [
            dict(r) for r in conn.execute(
                "SELECT * FROM companies WHERE name LIKE ? OR industry LIKE ? OR notes LIKE ?",
                (pattern, pattern, pattern),
            ).fetchall()
        ]

        contacts = [
            dict(r) for r in conn.execute(
                "SELECT * FROM contacts WHERE name LIKE ? OR email LIKE ? OR role LIKE ? OR tags LIKE ? OR notes LIKE ?",
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchall()
        ]

        interactions = [
            dict(r) for r in conn.execute(
                "SELECT * FROM interactions WHERE summary LIKE ? OR followup_note LIKE ?",
                (pattern, pattern),
            ).fetchall()
        ]

        deals = [
            dict(r) for r in conn.execute(
                "SELECT * FROM deals WHERE title LIKE ? OR notes LIKE ?",
                (pattern, pattern),
            ).fetchall()
        ]

        data = {
            "companies": companies,
            "contacts": contacts,
            "interactions": interactions,
            "deals": deals,
        }

        if settings.format == "text":
            console = Console()
            found = False

            if companies:
                found = True
                t = Table(title="Companies")
                t.add_column("ID", style="dim")
                t.add_column("Name", style="bold")
                t.add_column("Industry")
                t.add_column("Status")
                for c in companies:
                    t.add_row(str(c["id"]), c["name"], c.get("industry") or "", c.get("status") or "")
                console.print(t)

            if contacts:
                found = True
                t = Table(title="Contacts")
                t.add_column("ID", style="dim")
                t.add_column("Name", style="bold")
                t.add_column("Email")
                t.add_column("Role")
                t.add_column("Tags")
                for c in contacts:
                    t.add_row(str(c["id"]), c["name"], c.get("email") or "", c.get("role") or "", c.get("tags") or "")
                console.print(t)

            if interactions:
                found = True
                t = Table(title="Interactions")
                t.add_column("ID", style="dim")
                t.add_column("Type")
                t.add_column("Summary")
                t.add_column("Date")
                for i in interactions:
                    t.add_row(str(i["id"]), i.get("type") or "", i.get("summary") or "", i.get("occurred_at") or "")
                console.print(t)

            if deals:
                found = True
                t = Table(title="Deals")
                t.add_column("ID", style="dim")
                t.add_column("Title", style="bold")
                t.add_column("Stage")
                t.add_column("Value", justify="right")
                for d in deals:
                    t.add_row(
                        str(d["id"]),
                        d["title"],
                        d.get("stage") or "",
                        f"${d['value']:,.2f}" if d.get("value") else "",
                    )
                console.print(t)

            if not found:
                console.print(f"No results for '{query}'")
            raise typer.Exit(ExitCode.SUCCESS)

        emit_success(data, settings)
    finally:
        conn.close()
