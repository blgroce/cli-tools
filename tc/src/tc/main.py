from __future__ import annotations

import json
import sys
from enum import IntEnum

import typer

from . import __version__

APP_NAME = "tc"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Transaction Coordinator CLI — manage real estate transactions, tasks, people, and deadlines.",
)


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_ARGS = 2
    NOT_FOUND = 3
    EXTERNAL_FAILURE = 4


def _version_callback(value: bool) -> None:
    if value:
        print(f"{APP_NAME} {__version__}")
        raise typer.Exit(ExitCode.SUCCESS)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        is_eager=True,
        callback=_version_callback,
    ),
    format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or text",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error output",
    ),
) -> None:
    from .output import OutputSettings
    from .db import init_db

    if format not in {"json", "text"}:
        print(
            json.dumps({"error": True, "code": "INVALID_INPUT", "message": f"Invalid format: {format}"}),
            file=sys.stderr,
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    ctx.ensure_object(dict)
    ctx.obj = OutputSettings(format=format, quiet=quiet)
    init_db()


# --- Transaction commands ---
from .commands.transaction import create, get, list_transactions, update, search

app.command()(create)
app.command()(get)
app.command("list")(list_transactions)
app.command()(update)
app.command()(search)

# --- People commands ---
from .commands.person import add_person, people, update_person

app.command("add-person")(add_person)
app.command()(people)
app.command("update-person")(update_person)

# --- Task commands ---
from .commands.task import (
    tasks, tasks_due, complete_task, skip_task, add_task,
    generate_tasks, regenerate_tasks,
)

app.command()(tasks)
app.command("tasks-due")(tasks_due)
app.command("complete-task")(complete_task)
app.command("skip-task")(skip_task)
app.command("add-task")(add_task)
app.command("generate-tasks")(generate_tasks)
app.command("regenerate-tasks")(regenerate_tasks)

# --- Document commands ---
from .commands.document import add_doc, docs, update_doc, ingest_doc, link_doc, ask_doc

app.command("add-doc")(add_doc)
app.command()(docs)
app.command("update-doc")(update_doc)
app.command("ingest-doc")(ingest_doc)
app.command("link-doc")(link_doc)
app.command("ask-doc")(ask_doc)

# --- Note commands ---
from .commands.note import add_note, notes

app.command("add-note")(add_note)
app.command()(notes)

# --- Report commands ---
from .commands.report import summary, dashboard, timeline

app.command()(summary)
app.command()(dashboard)
app.command()(timeline)

if __name__ == "__main__":
    app()
