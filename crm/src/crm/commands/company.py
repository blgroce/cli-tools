"""Company subcommands: add, list, show, edit, rm."""
from __future__ import annotations

import sqlite3

import typer
from rich.table import Table
from rich.console import Console

from ..db import get_connection
from ..main import ExitCode
from ..models import Company
from ..output import get_settings, emit_success, emit_error

app = typer.Typer(
    name="company",
    help="Manage companies.",
    no_args_is_help=True,
)


@app.command()
def add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Company name"),
    status: str = typer.Option("prospect", help="Status: active/prospect/past/lead"),
    industry: str | None = typer.Option(None, help="Industry"),
    website: str | None = typer.Option(None, help="Website URL"),
    notes: str | None = typer.Option(None, help="Notes"),
) -> None:
    """Add a new company."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO companies (name, status, industry, website, notes) VALUES (?, ?, ?, ?, ?)",
            (name, status, industry, website, notes),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM companies WHERE id = ?", (cur.lastrowid,)).fetchone()
        company = Company.from_row(row)
        emit_success(
            company.to_dict(),
            settings,
            text=f"Added company: {company.name} (id={company.id})",
        )
    except sqlite3.IntegrityError:
        emit_error(
            f"Company '{name}' already exists",
            settings,
            code="DUPLICATE",
            exit_code=ExitCode.GENERAL_ERROR,
        )
    finally:
        conn.close()


@app.command("list")
def list_companies(
    ctx: typer.Context,
    status: str | None = typer.Option(None, help="Filter by status"),
) -> None:
    """List companies."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM companies WHERE status = ? ORDER BY name", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM companies ORDER BY name").fetchall()

        companies = [Company.from_row(r).to_dict() for r in rows]

        if settings.format == "text":
            console = Console()
            table = Table(title="Companies")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="bold")
            table.add_column("Industry")
            table.add_column("Status")
            for c in companies:
                table.add_row(
                    str(c["id"]),
                    c["name"],
                    c["industry"] or "",
                    c["status"] or "",
                )
            console.print(table)
            raise typer.Exit(ExitCode.SUCCESS)

        emit_success(companies, settings)
    finally:
        conn.close()


@app.command()
def show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Company name"),
) -> None:
    """Show company details."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM companies WHERE name = ?", (name,)).fetchone()
        if not row:
            emit_error(
                f"Company '{name}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return  # unreachable, emit_error raises

        company = Company.from_row(row)
        data = company.to_dict()

        contacts_count = conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE company_id = ?", (company.id,)
        ).fetchone()[0]
        deals_count = conn.execute(
            "SELECT COUNT(*) FROM deals WHERE company_id = ?", (company.id,)
        ).fetchone()[0]
        data["contacts_count"] = contacts_count
        data["deals_count"] = deals_count

        emit_success(
            data,
            settings,
            text=(
                f"Company: {company.name}\n"
                f"  Industry: {company.industry or '-'}\n"
                f"  Status:   {company.status or '-'}\n"
                f"  Website:  {company.website or '-'}\n"
                f"  Notes:    {company.notes or '-'}\n"
                f"  Contacts: {contacts_count}\n"
                f"  Deals:    {deals_count}"
            ),
        )
    finally:
        conn.close()


@app.command()
def edit(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Company name to edit"),
    new_name: str | None = typer.Option(None, "--name", help="New name"),
    status: str | None = typer.Option(None, help="New status"),
    industry: str | None = typer.Option(None, help="New industry"),
    website: str | None = typer.Option(None, help="New website"),
    notes: str | None = typer.Option(None, help="New notes"),
) -> None:
    """Edit a company's fields."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM companies WHERE name = ?", (name,)).fetchone()
        if not row:
            emit_error(
                f"Company '{name}' not found",
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
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if industry is not None:
            updates.append("industry = ?")
            params.append(industry)
        if website is not None:
            updates.append("website = ?")
            params.append(website)
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
            f"UPDATE companies SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

        updated = conn.execute("SELECT * FROM companies WHERE id = ?", (row["id"],)).fetchone()
        company = Company.from_row(updated)
        emit_success(
            company.to_dict(),
            settings,
            text=f"Updated company: {company.name}",
        )
    except sqlite3.IntegrityError:
        emit_error(
            f"Company name '{new_name}' already exists",
            settings,
            code="DUPLICATE",
            exit_code=ExitCode.GENERAL_ERROR,
        )
    finally:
        conn.close()


@app.command()
def rm(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Company name to delete"),
    force: bool = typer.Option(False, "--force", help="Force delete with related records"),
) -> None:
    """Remove a company."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM companies WHERE name = ?", (name,)).fetchone()
        if not row:
            emit_error(
                f"Company '{name}' not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        company_id = row["id"]
        contacts_count = conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE company_id = ?", (company_id,)
        ).fetchone()[0]
        deals_count = conn.execute(
            "SELECT COUNT(*) FROM deals WHERE company_id = ?", (company_id,)
        ).fetchone()[0]

        if (contacts_count > 0 or deals_count > 0) and not force:
            emit_error(
                f"Company '{name}' has {contacts_count} contact(s) and {deals_count} deal(s). Use --force to delete.",
                settings,
                code="HAS_RELATIONS",
                exit_code=ExitCode.GENERAL_ERROR,
            )
            return

        if force:
            # Cascade: delete interactions for contacts of this company
            conn.execute(
                "DELETE FROM interactions WHERE contact_id IN (SELECT id FROM contacts WHERE company_id = ?)",
                (company_id,),
            )
            conn.execute("DELETE FROM deals WHERE company_id = ?", (company_id,))
            conn.execute("DELETE FROM contacts WHERE company_id = ?", (company_id,))

        conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        conn.commit()

        emit_success(
            {"id": company_id, "name": name},
            settings,
            text=f"Deleted company: {name}",
        )
    finally:
        conn.close()
