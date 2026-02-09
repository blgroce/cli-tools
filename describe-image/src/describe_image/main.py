from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Optional

import keyring
import typer
from keyring.errors import KeyringError, PasswordDeleteError

from . import __version__

APP_NAME = "describe-image"
DEFAULT_MODEL = "google/gemini-2.5-flash-preview:thinking"
ENV_API_KEY = "DESCRIBE_IMAGE_API_KEY"
KEYRING_SERVICE = "describe-image"
KEYRING_ACCOUNT = "openrouter_api_key"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Describe images using AI models via OpenRouter API.",
)
auth_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(auth_app, name="auth", help="Manage OpenRouter API key storage.")


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_ARGS = 2
    NOT_FOUND = 3
    EXTERNAL_FAILURE = 4


@dataclass
class OutputSettings:
    format: str
    quiet: bool


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


def get_settings(ctx: typer.Context) -> OutputSettings:
    if isinstance(ctx.obj, OutputSettings):
        return ctx.obj
    return OutputSettings(format="json", quiet=False)


def _version_callback(value: bool) -> None:
    if value:
        print(f"{APP_NAME} {__version__}")
        raise typer.Exit(ExitCode.SUCCESS)


@app.callback()
def main(
    ctx: typer.Context,
    format: str = typer.Option("json", "--format", help="Output format: json or text"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    if format not in {"json", "text"}:
        print(
            json.dumps(
                {"error": True, "code": "INVALID_ARGS", "message": "Format must be json or text"}
            ),
            file=sys.stderr,
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)
    ctx.obj = OutputSettings(format=format, quiet=quiet)


def resolve_api_key(settings: OutputSettings) -> str:
    env_key = os.getenv(ENV_API_KEY)
    if env_key:
        return env_key
    try:
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
    except KeyringError as exc:
        emit_error(
            f"Keyring error: {exc}. Set {ENV_API_KEY} instead.",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )
    if not stored:
        emit_error(
            f"OpenRouter API key not found. Set {ENV_API_KEY} or run '{APP_NAME} auth set --key ...'.",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )
    return stored


@auth_app.command("set", help="Store OpenRouter API key in system keyring.")
def auth_set(
    ctx: typer.Context,
    key: Optional[str] = typer.Option(None, "--key", help="OpenRouter API key"),
    key_stdin: bool = typer.Option(False, "--key-stdin", help="Read key from stdin"),
) -> None:
    settings = get_settings(ctx)

    if key and key_stdin:
        emit_error(
            "Use either --key or --key-stdin, not both.",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )
    if key_stdin:
        key = sys.stdin.read().strip()
    if not key:
        emit_error(
            "API key is required. Use --key or --key-stdin.",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )

    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, key)
    except KeyringError as exc:
        emit_error(
            f"Keyring error: {exc}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    emit_success(
        {"stored": True, "location": "keyring"},
        settings,
        text="Stored OpenRouter API key in system keyring.",
    )


@auth_app.command("status", help="Check if an API key is configured.")
def auth_status(ctx: typer.Context) -> None:
    settings = get_settings(ctx)

    env_present = bool(os.getenv(ENV_API_KEY))
    keyring_present = False
    keyring_error: Optional[str] = None

    try:
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        keyring_present = bool(stored)
    except KeyringError as exc:
        keyring_error = str(exc)

    source = "env" if env_present else ("keyring" if keyring_present else None)
    data = {"env": env_present, "keyring": keyring_present, "source": source}
    if keyring_error:
        data["keyring_error"] = keyring_error

    text_parts = [f"env: {env_present}", f"keyring: {keyring_present}"]
    if keyring_error:
        text_parts.append(f"keyring_error: {keyring_error}")

    emit_success(data, settings, text="; ".join(text_parts))


@auth_app.command("clear", help="Remove API key from system keyring.")
def auth_clear(ctx: typer.Context) -> None:
    settings = get_settings(ctx)

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
    except PasswordDeleteError:
        emit_error(
            "No stored key found in keyring.",
            settings,
            code="NOT_FOUND",
            exit_code=ExitCode.NOT_FOUND,
        )
    except KeyringError as exc:
        emit_error(
            f"Keyring error: {exc}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    emit_success(
        {"cleared": True, "location": "keyring"},
        settings,
        text="Removed OpenRouter API key from system keyring.",
    )


if __name__ == "__main__":
    app()
