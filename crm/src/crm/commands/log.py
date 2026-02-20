"""Interaction logging subcommands: call, email, meeting, note."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

import typer

from ..db import get_connection
from ..main import ExitCode
from ..models import Interaction
from ..output import get_settings, emit_success, emit_error

app = typer.Typer(
    name="log",
    help="Log interactions with contacts.",
    no_args_is_help=True,
)


def _parse_followup(value: str) -> str:
    """Parse followup shorthand into YYYY-MM-DD.

    Accepts: Nd (days), Nw (weeks), or YYYY-MM-DD.
    """
    today = datetime.now().date()

    m = re.fullmatch(r"(\d+)d", value)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()

    m = re.fullmatch(r"(\d+)w", value)
    if m:
        return (today + timedelta(weeks=int(m.group(1)))).isoformat()

    m = re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
    if m:
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            pass

    return ""


def _resolve_contact(conn, name: str, settings):
    """Resolve a contact name to its row. Emits error and exits if not found."""
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
    return row


def _log_interaction(
    ctx: typer.Context,
    interaction_type: str,
    contact_name: str,
    summary: str,
    followup: str | None,
    followup_note: str | None,
    date: str | None,
) -> None:
    """Shared logic for all interaction subcommands."""
    settings = get_settings(ctx)
    conn = get_connection()
    try:
        contact_row = _resolve_contact(conn, contact_name, settings)
        contact_id = contact_row["id"]
        company_id = contact_row["company_id"]
        company_name = contact_row["company_name"]

        followup_date = None
        if followup:
            followup_date = _parse_followup(followup)
            if not followup_date:
                emit_error(
                    f"Invalid followup format: '{followup}'. Use Nd, Nw, or YYYY-MM-DD.",
                    settings,
                    code="INVALID_INPUT",
                    exit_code=ExitCode.INVALID_ARGS,
                )

        occurred_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
                occurred_at = f"{date} 00:00:00"
            except ValueError:
                emit_error(
                    f"Invalid date format: '{date}'. Use YYYY-MM-DD.",
                    settings,
                    code="INVALID_INPUT",
                    exit_code=ExitCode.INVALID_ARGS,
                )

        cur = conn.execute(
            """INSERT INTO interactions
               (contact_id, company_id, type, summary, occurred_at, followup_date, followup_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (contact_id, company_id, interaction_type, summary, occurred_at, followup_date, followup_note),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM interactions WHERE id = ?", (cur.lastrowid,)).fetchone()
        interaction = Interaction.from_row(row)
        data = interaction.to_dict()
        data["contact_name"] = contact_name
        data["company_name"] = company_name

        text_parts = [f"Logged {interaction_type} with {contact_name}: {summary}"]
        if followup_date:
            text_parts.append(f"  Follow-up: {followup_date}")
            if followup_note:
                text_parts.append(f"  Note: {followup_note}")

        emit_success(data, settings, text="\n".join(text_parts))
    finally:
        conn.close()


@app.command()
def call(
    ctx: typer.Context,
    contact_name: str = typer.Argument(..., help="Contact name"),
    summary: str = typer.Option(..., "--summary", help="What happened"),
    followup: str | None = typer.Option(None, "--followup", help="Follow-up: Nd, Nw, or YYYY-MM-DD"),
    followup_note: str | None = typer.Option(None, "--followup-note", help="Follow-up note"),
    date: str | None = typer.Option(None, "--date", help="When it happened (YYYY-MM-DD)"),
) -> None:
    """Log a phone call."""
    _log_interaction(ctx, "call", contact_name, summary, followup, followup_note, date)


@app.command()
def email(
    ctx: typer.Context,
    contact_name: str = typer.Argument(..., help="Contact name"),
    summary: str = typer.Option(..., "--summary", help="What happened"),
    followup: str | None = typer.Option(None, "--followup", help="Follow-up: Nd, Nw, or YYYY-MM-DD"),
    followup_note: str | None = typer.Option(None, "--followup-note", help="Follow-up note"),
    date: str | None = typer.Option(None, "--date", help="When it happened (YYYY-MM-DD)"),
) -> None:
    """Log an email interaction."""
    _log_interaction(ctx, "email", contact_name, summary, followup, followup_note, date)


@app.command()
def meeting(
    ctx: typer.Context,
    contact_name: str = typer.Argument(..., help="Contact name"),
    summary: str = typer.Option(..., "--summary", help="What happened"),
    followup: str | None = typer.Option(None, "--followup", help="Follow-up: Nd, Nw, or YYYY-MM-DD"),
    followup_note: str | None = typer.Option(None, "--followup-note", help="Follow-up note"),
    date: str | None = typer.Option(None, "--date", help="When it happened (YYYY-MM-DD)"),
) -> None:
    """Log a meeting."""
    _log_interaction(ctx, "meeting", contact_name, summary, followup, followup_note, date)


@app.command()
def note(
    ctx: typer.Context,
    contact_name: str = typer.Argument(..., help="Contact name"),
    summary: str = typer.Option(..., "--summary", help="What happened"),
    followup: str | None = typer.Option(None, "--followup", help="Follow-up: Nd, Nw, or YYYY-MM-DD"),
    followup_note: str | None = typer.Option(None, "--followup-note", help="Follow-up note"),
    date: str | None = typer.Option(None, "--date", help="When it happened (YYYY-MM-DD)"),
) -> None:
    """Log a note about a contact."""
    _log_interaction(ctx, "note", contact_name, summary, followup, followup_note, date)
