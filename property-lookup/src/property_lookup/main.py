from __future__ import annotations

import json
import sys
from enum import IntEnum

import typer

from . import __version__

APP_NAME = "property-lookup"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Property data lookup — Zillow details + Texas water district data.",
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

    if format not in {"json", "text"}:
        print(
            json.dumps({"error": True, "code": "INVALID_INPUT", "message": f"Invalid format: {format}"}),
            file=sys.stderr,
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    ctx.ensure_object(dict)
    ctx.obj = OutputSettings(format=format, quiet=quiet)


# --- Commands ---
from .commands.districts_cmd import districts
from .commands.zillow_cmd import zillow
from .commands.lookup_cmd import lookup

app.command()(districts)
app.command()(zillow)
app.command()(lookup)

if __name__ == "__main__":
    app()
