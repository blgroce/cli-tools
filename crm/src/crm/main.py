from __future__ import annotations

import json
import sys
from enum import IntEnum

import typer

from . import __version__

APP_NAME = "crm"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="CLI CRM for BCG Ventures — contacts, interactions, deals, and follow-ups.",
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


from .commands.company import app as company_app
from .commands.contact import app as contact_app
from .commands.log import app as log_app
from .commands.deal import app as deal_app
from .commands.followup import app as followup_app
from .commands.search import search
from .commands.status import status

app.add_typer(company_app)
app.add_typer(contact_app)
app.add_typer(log_app)
app.add_typer(deal_app)
app.add_typer(followup_app)

app.command()(search)
app.command()(status)

if __name__ == "__main__":
    app()
