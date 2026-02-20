"""Follow-up subcommands: list (default) and done."""
from __future__ import annotations

from datetime import datetime, timedelta

import typer
from rich.table import Table
from rich.console import Console

from ..db import get_connection
from ..main import ExitCode
from ..output import get_settings, emit_success, emit_error

app = typer.Typer(
    name="followups",
    help="View and manage follow-ups.",
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def list_followups(
    ctx: typer.Context,
    week: bool = typer.Option(False, "--week", help="Show follow-ups due within 7 days"),
    all_: bool = typer.Option(False, "--all", help="Show all pending follow-ups"),
) -> None:
    """List follow-ups. Default: due today + overdue."""
    if ctx.invoked_subcommand is not None:
        return

    settings = get_settings(ctx)
    today = datetime.now().date().isoformat()

    conn = get_connection()
    try:
        query = """
            SELECT i.id, i.summary, i.followup_date, i.followup_note, i.type,
                   c.name AS contact_name, co.name AS company_name
            FROM interactions i
            JOIN contacts c ON i.contact_id = c.id
            LEFT JOIN companies co ON i.company_id = co.id
            WHERE i.followup_date IS NOT NULL
        """
        params: list = []

        if all_:
            pass  # no date filter
        elif week:
            week_ahead = (datetime.now().date() + timedelta(days=7)).isoformat()
            query += " AND i.followup_date <= ?"
            params.append(week_ahead)
        else:
            # Default: due today + overdue
            query += " AND i.followup_date <= ?"
            params.append(today)

        query += " ORDER BY i.followup_date ASC"

        rows = conn.execute(query, params).fetchall()
        results = []
        for r in rows:
            days_overdue = (datetime.now().date() - datetime.strptime(r["followup_date"], "%Y-%m-%d").date()).days
            results.append({
                "id": r["id"],
                "contact_name": r["contact_name"],
                "company_name": r["company_name"],
                "type": r["type"],
                "summary": r["summary"],
                "followup_date": r["followup_date"],
                "followup_note": r["followup_note"],
                "days_overdue": days_overdue,
            })

        if settings.format == "text":
            console = Console()
            title = "Follow-ups"
            if week:
                title += " (next 7 days)"
            elif all_:
                title += " (all pending)"
            else:
                title += " (due/overdue)"

            table = Table(title=title)
            table.add_column("ID", style="dim")
            table.add_column("Contact", style="bold")
            table.add_column("Company")
            table.add_column("Summary")
            table.add_column("Due Date")
            table.add_column("Note")
            table.add_column("Overdue", justify="right")

            for item in results:
                overdue = item["days_overdue"]
                if overdue > 0:
                    date_style = "red bold"
                    overdue_str = f"+{overdue}d"
                elif overdue == 0:
                    date_style = "yellow"
                    overdue_str = "today"
                else:
                    date_style = "green"
                    overdue_str = f"{-overdue}d left"

                table.add_row(
                    str(item["id"]),
                    item["contact_name"],
                    item["company_name"] or "",
                    item["summary"] or "",
                    f"[{date_style}]{item['followup_date']}[/{date_style}]",
                    item["followup_note"] or "",
                    f"[{date_style}]{overdue_str}[/{date_style}]",
                )
            console.print(table)
            raise typer.Exit(ExitCode.SUCCESS)

        emit_success(results, settings)
    finally:
        conn.close()


@app.command()
def done(
    ctx: typer.Context,
    interaction_id: int = typer.Argument(..., help="Interaction ID to mark as done"),
) -> None:
    """Mark a follow-up as done (clears followup_date and followup_note)."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM interactions WHERE id = ?", (interaction_id,)).fetchone()
        if not row:
            emit_error(
                f"Interaction {interaction_id} not found",
                settings,
                code="NOT_FOUND",
                exit_code=ExitCode.NOT_FOUND,
            )
            return

        conn.execute(
            "UPDATE interactions SET followup_date = NULL, followup_note = NULL WHERE id = ?",
            (interaction_id,),
        )
        conn.commit()

        emit_success(
            {"id": interaction_id, "followup_cleared": True},
            settings,
            text=f"Follow-up for interaction {interaction_id} marked as done.",
        )
    finally:
        conn.close()
