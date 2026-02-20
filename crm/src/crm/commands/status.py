"""Status command: dashboard summary of CRM data."""
from __future__ import annotations

from datetime import datetime, timedelta

import typer
from rich.console import Console
from rich.panel import Panel

from ..db import get_connection
from ..main import ExitCode
from ..output import get_settings, emit_success


def status(ctx: typer.Context) -> None:
    """Show CRM dashboard summary."""
    settings = get_settings(ctx)
    today = datetime.now().date().isoformat()
    week_ahead = (datetime.now().date() + timedelta(days=7)).isoformat()

    conn = get_connection()
    try:
        # Active deals
        row = conn.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(value), 0) AS total FROM deals WHERE stage = 'active'"
        ).fetchone()
        active_deals = {"count": row["cnt"], "total_value": row["total"]}

        # Pipeline deals (non-closed)
        row = conn.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(value), 0) AS total FROM deals WHERE stage NOT IN ('closed-won', 'closed-lost')"
        ).fetchone()
        pipeline_deals = {"count": row["cnt"], "total_value": row["total"]}

        # Overdue follow-ups
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM interactions WHERE followup_date IS NOT NULL AND followup_date < ?",
            (today,),
        ).fetchone()
        overdue_followups = row["cnt"]

        # Upcoming follow-ups (today through next 7 days)
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM interactions WHERE followup_date IS NOT NULL AND followup_date >= ? AND followup_date <= ?",
            (today, week_ahead),
        ).fetchone()
        upcoming_followups = row["cnt"]

        # Recent interactions (last 5)
        rows = conn.execute(
            """
            SELECT i.id, i.type, i.summary, i.occurred_at,
                   c.name AS contact_name, co.name AS company_name
            FROM interactions i
            JOIN contacts c ON i.contact_id = c.id
            LEFT JOIN companies co ON i.company_id = co.id
            ORDER BY i.occurred_at DESC
            LIMIT 5
            """,
        ).fetchall()
        recent_interactions = [dict(r) for r in rows]

        # Company status counts
        rows = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM companies GROUP BY status"
        ).fetchall()
        company_counts = {r["status"]: r["cnt"] for r in rows}

        data = {
            "active_deals": active_deals,
            "pipeline_deals": pipeline_deals,
            "overdue_followups": overdue_followups,
            "upcoming_followups": upcoming_followups,
            "recent_interactions": recent_interactions,
            "company_counts": company_counts,
        }

        if settings.format == "text":
            console = Console()
            lines = []
            lines.append("[bold]Deals[/bold]")
            lines.append(f"  Active:   {active_deals['count']}  (${active_deals['total_value']:,.2f})")
            lines.append(f"  Pipeline: {pipeline_deals['count']}  (${pipeline_deals['total_value']:,.2f})")
            lines.append("")
            lines.append("[bold]Follow-ups[/bold]")
            lines.append(f"  Overdue:  {overdue_followups}")
            lines.append(f"  Upcoming: {upcoming_followups} (next 7 days)")
            lines.append("")
            lines.append("[bold]Companies[/bold]")
            for status_name, cnt in sorted(company_counts.items()):
                lines.append(f"  {status_name}: {cnt}")
            lines.append("")
            lines.append("[bold]Recent Interactions[/bold]")
            for ix in recent_interactions:
                lines.append(f"  [{ix['type']}] {ix['contact_name']}: {ix['summary']}")

            console.print(Panel("\n".join(lines), title="CRM Dashboard"))
            raise typer.Exit(ExitCode.SUCCESS)

        emit_success(data, settings)
    finally:
        conn.close()
