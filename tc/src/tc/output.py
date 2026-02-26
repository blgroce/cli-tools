"""Output helpers for JSON and text formatting."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Optional

import typer

from .main import ExitCode


@dataclass
class OutputSettings:
    format: str
    quiet: bool


def get_settings(ctx: typer.Context) -> OutputSettings:
    if isinstance(ctx.obj, OutputSettings):
        return ctx.obj
    return OutputSettings(format="json", quiet=False)


def emit_success(data: Any, settings: OutputSettings, text: Optional[str] = None) -> None:
    if settings.quiet:
        raise typer.Exit(ExitCode.SUCCESS)
    if settings.format == "text":
        print(text or "")
        raise typer.Exit(ExitCode.SUCCESS)
    print(json.dumps({"success": True, "data": data}))
    raise typer.Exit(ExitCode.SUCCESS)


def emit_error(
    message: str,
    settings: OutputSettings,
    code: str = "ERROR",
    exit_code: ExitCode = ExitCode.GENERAL_ERROR,
) -> None:
    if settings.format == "text":
        print(f"{code}: {message}", file=sys.stderr)
        raise typer.Exit(exit_code)
    print(json.dumps({"error": True, "code": code, "message": message}), file=sys.stderr)
    raise typer.Exit(exit_code)
