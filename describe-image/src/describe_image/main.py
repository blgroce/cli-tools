from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, Optional

import keyring
import requests
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


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DEFAULT_PROMPT = "Describe this image in detail."


def get_mime_type(image_path: Path) -> Optional[str]:
    """Get MIME type from file extension."""
    ext = image_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_map.get(ext)


def encode_image_to_base64(image_path: Path) -> str:
    """Read and base64 encode an image file."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def send_to_openrouter(
    api_key: str,
    base64_image: str,
    mime_type: str,
    model: str,
    prompt: str,
) -> dict[str, Any]:
    """Send image to OpenRouter API and get description."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data_url = f"data:{mime_type};base64,{base64_image}"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    return response


@app.command("describe", help="Describe an image using AI via OpenRouter.")
def describe(
    ctx: typer.Context,
    image_path: Path = typer.Argument(..., help="Path to the image file to describe"),
    model: str = typer.Option(
        DEFAULT_MODEL, "--model", "-m", help="Model to use for description"
    ),
    prompt: str = typer.Option(
        DEFAULT_PROMPT, "--prompt", "-p", help="Prompt to use for describing the image"
    ),
) -> None:
    settings = get_settings(ctx)

    # Validate image file exists
    if not image_path.exists():
        emit_error(
            f"Image file not found: {image_path}",
            settings,
            code="NOT_FOUND",
            exit_code=ExitCode.NOT_FOUND,
        )

    # Validate file is readable
    if not image_path.is_file():
        emit_error(
            f"Path is not a file: {image_path}",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )

    # Get MIME type
    mime_type = get_mime_type(image_path)
    if not mime_type:
        emit_error(
            f"Unsupported image format. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )

    # Get API key
    api_key = resolve_api_key(settings)

    # Encode image
    try:
        base64_image = encode_image_to_base64(image_path)
    except (OSError, IOError) as exc:
        emit_error(
            f"Failed to read image file: {exc}",
            settings,
            code="GENERAL_ERROR",
            exit_code=ExitCode.GENERAL_ERROR,
        )

    # Send to OpenRouter
    try:
        response = send_to_openrouter(api_key, base64_image, mime_type, model, prompt)
    except requests.exceptions.Timeout:
        emit_error(
            "Request to OpenRouter timed out",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )
    except requests.exceptions.RequestException as exc:
        emit_error(
            f"Request failed: {exc}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    # Handle API errors
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except (json.JSONDecodeError, KeyError):
            error_msg = response.text
        emit_error(
            f"OpenRouter API error ({response.status_code}): {error_msg}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    # Parse response
    try:
        result = response.json()
        description = result["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        emit_error(
            f"Failed to parse OpenRouter response: {exc}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    emit_success(
        {
            "description": description,
            "image_path": str(image_path.resolve()),
            "model": model,
        },
        settings,
        text=description,
    )


if __name__ == "__main__":
    app()
