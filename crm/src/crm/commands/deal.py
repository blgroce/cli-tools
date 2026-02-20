"""Deal subcommands: add, list, show, move, rm."""
from __future__ import annotations

import typer
from rich.table import Table
from rich.console import Console

from ..db import get_connection
from ..main import ExitCode
from ..models import Deal
from ..output import get_settings, emit_success, emit_error

app = typer.Typer(
    name="deal",
    help="Manage deals.",
    no_args_is_help=True,
)

VALID_STAGES = {"lead", "proposal", "negotiation", "active", "closed-won", "closed-lost"}


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


def _resolve_contact(conn, name: str, settings):
    """Resolve a contact name to its id. Emits error and exits if not found."""
    row = conn.execute("SELECT id FROM contacts WHERE name = ?", (name,)).fetchone()
    if not row:
        emit_error(
            f"Contact '{name}' not found",
            settings,
            code="NOT_FOUND",
            exit_code=ExitCode.NOT_FOUND,
        )
    return row["id"]


def _validate_stage(stage: str, settings) -> None:
    """Validate that stage is one of the allowed values."""
    if stage not in VALID_STAGES:
        emit_error(
            f"Invalid stage '{stage}'. Must be one of: {', '.join(sorted(VALID_STAGES))}",
            settings,
            code="INVALID_INPUT",
            exit_code=ExitCode.INVALID_ARGS,
        )


@app.command()
def add(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Deal title"),
    company: str = typer.Option(..., "--company", help="Company name (required)"),
    value: float | None = typer.Option(None, "--value", help="Dollar amount"),
    stage: str = typer.Option("lead", "--stage", help="Stage: lead/proposal/negotiation/active/closed-won/closed-lost"),
    contact: str | None = typer.Option(None, "--contact", help="Primary contact name"),
    notes: str | None = typer.Option(None, "--notes", help="Notes"),
) -> None:
    """Add a new deal."""
    settings = get_settings(ctx)
    _validate_stage(stage, settings)

    conn = get_connection()
    try:
        company_id = _resolve_company(conn, company, settings)

        contact_id = None
        if contact:
            contact_id = _resolve_contact(conn, contact, settings)

        cur = conn.execute(
            "INSERT INTO deals (title, company_id, contact_id, value, stage, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (title, company_id, contact_id, value, stage, notes),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT d.*, co.name AS company_name, ct.name AS contact_name
            FROM deals d
            JOIN companies co ON d.company_id = co.id
            LEFT JOIN contacts ct ON d.contact_id = ct.id
            WHERE d.id = ?
            """,
            (cur.lastrowid,),
        ).fetchone()
        deal = Deal.from_row(row)
        data = deal.to_dict()
        data["company_name"] = row["company_name"]
        data["contact_name"] = row["contact_name"]

        emit_success(
            data,
            settings,
            text=f"Added deal: {deal.title} (id={deal.id})",
        )
    finally:
        conn.close()


@app.command("list")
def list_deals(
    ctx: typer.Context,
    stage: str | None = typer.Option(None, "--stage", help="Filter by stage"),
    company: str | None = typer.Option(None, "--company", help="Filter by company name"),
) -> None:
    """List deals."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        query = """
            SELECT d.*, co.name AS company_name, ct.name AS contact_name
            FROM deals d
            JOIN companies co ON d.company_id = co.id
            LEFT JOIN contacts ct ON d.contact_id = ct.id
        """
        conditions: list[str] = []
        params: list = []

        if stage:
            _validate_stage(stage, settings)
            conditions.append("d.stage = ?")
            params.append(stage)

        if company:
            company_id = _resolve_company(conn, company, settings)
            conditions.append("d.company_id = ?")
            params.append(company_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY d.created_at DESC"

        rows = conn.execute(query, params).fetchall()
        deals = []
        for r in rows:
            d = Deal.from_row(r).to_dict()
            d["company_name"] = r["company_name"]
            d["contact_name"] = r["contact_name"]
            deals.append(d)

        if settings.format == "text":
            console = Console()
            table = Table(title="Deals")
            table.add_column("ID", style="dim")
            table.add_column("Title", style="bold")
            table.add_column("Company")
            table.add_column("Value", justify="right")
            table.add_column("Stage")
            for d in deals:
                table.add_row(
                    str(d["id"]),
                    d["title"],
                    d["company_name"] or "",
                    f"${d['value']:,.2f}" if d["value"] else "",
                    d["stage"] or "",
                )
            console.print(table)
            raise typer.Exit(ExitCode.SUCCESS)

        emit_success(deals, settings)
    finally:
        conn.close()


@app.command()
def show(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Deal title"),
) -> None:
    """Show deal details."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT d.*, co.name AS company_name, ct.name AS contact_name
            FROM deals d
            JOIN companies co ON d.company_id = co.id
            LEFT JOIN contacts ct ON d.contact_id = ct.id
            WHERE d.title = ?
            """,
            (title,),
        ).fetchone()

        if not row:
            emit_error(
                f"Deal '{title}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        deal = Deal.from_row(row)
        data = deal.to_dict()
        data["company_name"] = row["company_name"]
        data["contact_name"] = row["contact_name"]

        value_str = f"${deal.value:,.2f}" if deal.value else "-"
        emit_success(
            data,
            settings,
            text=(
                f"Deal: {deal.title}\n"
                f"  Company: {row['company_name']}\n"
                f"  Contact: {row['contact_name'] or '-'}\n"
                f"  Value:   {value_str}\n"
                f"  Stage:   {deal.stage or '-'}\n"
                f"  Notes:   {deal.notes or '-'}\n"
                f"  Created: {deal.created_at}\n"
                f"  Updated: {deal.updated_at}"
            ),
        )
    finally:
        conn.close()


@app.command()
def move(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Deal title"),
    stage: str = typer.Option(..., "--stage", help="New stage"),
) -> None:
    """Move a deal to a new stage."""
    settings = get_settings(ctx)
    _validate_stage(stage, settings)

    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM deals WHERE title = ?", (title,)).fetchone()
        if not row:
            emit_error(
                f"Deal '{title}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        conn.execute(
            "UPDATE deals SET stage = ? WHERE id = ?",
            (stage, row["id"]),
        )
        conn.commit()

        updated = conn.execute(
            """
            SELECT d.*, co.name AS company_name, ct.name AS contact_name
            FROM deals d
            JOIN companies co ON d.company_id = co.id
            LEFT JOIN contacts ct ON d.contact_id = ct.id
            WHERE d.id = ?
            """,
            (row["id"],),
        ).fetchone()
        deal = Deal.from_row(updated)
        data = deal.to_dict()
        data["company_name"] = updated["company_name"]
        data["contact_name"] = updated["contact_name"]

        emit_success(
            data,
            settings,
            text=f"Moved deal '{deal.title}' to stage: {stage}",
        )
    finally:
        conn.close()


@app.command()
def rm(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Deal title to delete"),
) -> None:
    """Remove a deal."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM deals WHERE title = ?", (title,)).fetchone()
        if not row:
            emit_error(
                f"Deal '{title}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        deal_id = row["id"]
        conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
        conn.commit()

        emit_success(
            {"id": deal_id, "title": title},
            settings,
            text=f"Deleted deal: {title}",
        )
    finally:
        conn.close()
