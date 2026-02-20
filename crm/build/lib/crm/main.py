from __future__ import annotations

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
) -> None:
    pass


if __name__ == "__main__":
    app()
