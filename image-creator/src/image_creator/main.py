from __future__ import annotations

import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, Iterable, Optional

import keyring
import requests
import typer
from keyring.errors import KeyringError, PasswordDeleteError

from . import __version__

APP_NAME = "image-creator"
DEFAULT_MODEL = "google/gemini-3-pro-image-preview"
ENV_API_KEY = "IMAGE_CREATOR_API_KEY"
ENV_API_KEY_FALLBACK = "OPENROUTER_API_KEY"
KEYRING_SERVICE = "image-creator"
KEYRING_ACCOUNT = "openrouter_api_key"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

IMAGE_DATA_URL_PATTERN = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+")
SUPPORTED_ASPECT_RATIOS = {
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
}
SUPPORTED_IMAGE_SIZES = {"1K", "2K", "4K"}

# Models that only support image output (not text+image)
IMAGE_ONLY_MODEL_PREFIXES = (
    "black-forest-labs/",
    "bytedance-seed/",
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Generate images using AI models via OpenRouter API.",
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
    env_key = os.getenv(ENV_API_KEY) or os.getenv(ENV_API_KEY_FALLBACK)
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
            f"OpenRouter API key not found. Set {ENV_API_KEY} or {ENV_API_KEY_FALLBACK} or run '{APP_NAME} auth set --key ...'.",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )
    return stored


def extract_image_urls(message: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    images = message.get("images")
    if isinstance(images, list):
        for image in images:
            if not isinstance(image, dict):
                continue
            image_url = image.get("image_url") or image.get("imageUrl")
            if isinstance(image_url, dict):
                url = image_url.get("url")
                if url:
                    urls.append(url)
            elif isinstance(image_url, str):
                urls.append(image_url)
    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") != "image_url":
                continue
            image_url = part.get("image_url") or part.get("imageUrl")
            if isinstance(image_url, dict):
                url = image_url.get("url")
                if url:
                    urls.append(url)
            elif isinstance(image_url, str):
                urls.append(image_url)
    elif isinstance(content, str):
        urls.extend(IMAGE_DATA_URL_PATTERN.findall(content))
    return dedupe(urls)


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def parse_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:image/"):
        raise ValueError("Expected image data URL")
    header, b64_data = data_url.split(",", 1)
    mime = header.split(";")[0].replace("data:", "")
    try:
        image_bytes = base64.b64decode(b64_data, validate=True)
    except ValueError:
        image_bytes = base64.b64decode(b64_data)
    return mime, image_bytes


def extension_from_mime(mime: str) -> str:
    ext = mime.split("/")[-1].lower()
    if ext == "jpeg":
        return "jpg"
    return ext or "png"


def mime_from_extension(ext: str) -> str:
    """Determine MIME type from file extension."""
    ext = ext.lower().lstrip(".")
    mapping = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return mapping.get(ext, "image/png")


def load_input_image(image_path: Path, settings: OutputSettings) -> tuple[str, str]:
    """Load an image file and return (mime_type, base64_data)."""
    if not image_path.exists():
        emit_error(
            f"Image file not found: {image_path}",
            settings,
            code="NOT_FOUND",
            exit_code=ExitCode.NOT_FOUND,
        )
    if not image_path.is_file():
        emit_error(
            f"Not a file: {image_path}",
            settings,
            code="INVALID_ARGS",
            exit_code=ExitCode.INVALID_ARGS,
        )
    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        emit_error(
            f"Failed to read image: {exc}",
            settings,
            code="GENERAL_ERROR",
            exit_code=ExitCode.GENERAL_ERROR,
        )
    mime = mime_from_extension(image_path.suffix)
    b64_data = base64.b64encode(image_bytes).decode("ascii")
    return mime, b64_data


def build_message_content(prompt: str, image_paths: Optional[list[Path]], settings: OutputSettings) -> Any:
    """Build message content, optionally including input image(s)."""
    if not image_paths:
        return prompt

    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image_path in image_paths:
        mime, b64_data = load_input_image(image_path.expanduser(), settings)
        data_url = f"data:{mime};base64,{b64_data}"
        parts.append({"type": "image_url", "image_url": {"url": data_url}})

    return parts


DEFAULT_OUTPUT_DIR = Path.home() / "generated-images"


def resolve_output_path(out: Optional[Path], ext: str) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f"image-{timestamp}.{ext}"
    if out is None:
        return DEFAULT_OUTPUT_DIR / filename
    out = out.expanduser()
    if out.exists() and out.is_dir():
        return out / filename
    if out.suffix:
        return out
    return out.with_suffix(f".{ext}")


def is_image_only_model(model: str) -> bool:
    """Check if a model only supports image output (not text+image)."""
    return model.startswith(IMAGE_ONLY_MODEL_PREFIXES)


def validate_image_config(
    aspect_ratio: Optional[str], image_size: Optional[str], settings: OutputSettings
) -> dict[str, str]:
    config: dict[str, str] = {}
    if aspect_ratio:
        if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            emit_error(
                "Aspect ratio must be one of: " + ", ".join(sorted(SUPPORTED_ASPECT_RATIOS)),
                settings,
                code="INVALID_ARGS",
                exit_code=ExitCode.INVALID_ARGS,
            )
        config["aspect_ratio"] = aspect_ratio
    if image_size:
        if image_size not in SUPPORTED_IMAGE_SIZES:
            emit_error(
                "Image size must be one of: " + ", ".join(sorted(SUPPORTED_IMAGE_SIZES)),
                settings,
                code="INVALID_ARGS",
                exit_code=ExitCode.INVALID_ARGS,
            )
        config["image_size"] = image_size
    return config


@app.command(help="Generate an image from a text prompt.")
def create(
    ctx: typer.Context,
    prompt: str = typer.Argument(..., help="Text prompt for image generation"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="OpenRouter model ID"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Output path [default: ~/generated-images/]"),
    image: Optional[list[Path]] = typer.Option(
        None, "--image", "-i", help="Input image(s) for editing or reference (repeatable)"
    ),
    aspect_ratio: Optional[str] = typer.Option(
        None, "--aspect-ratio", help="Aspect ratio: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9"
    ),
    image_size: Optional[str] = typer.Option(None, "--image-size", help="Resolution: 1K, 2K, or 4K"),
) -> None:
    settings = get_settings(ctx)
    api_key = resolve_api_key(settings)

    image_config = validate_image_config(aspect_ratio, image_size, settings)
    message_content = build_message_content(prompt, image, settings)

    # Image-only models (FLUX, Seedream) don't support text output modality
    modalities = ["image"] if is_image_only_model(model) else ["image", "text"]

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message_content}],
        "modalities": modalities,
        "stream": False,
    }
    if image_config:
        payload["image_config"] = image_config
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    except requests.exceptions.RequestException as exc:
        emit_error(
            f"OpenRouter request failed: {exc}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    try:
        result = response.json()
    except ValueError:
        emit_error(
            f"OpenRouter returned non-JSON response (status {response.status_code}).",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    if not response.ok:
        error_message = ""
        if isinstance(result, dict):
            error_message = result.get("error", {}).get("message") or result.get("message") or ""
        if not error_message:
            error_message = f"HTTP {response.status_code}"
        emit_error(
            f"OpenRouter error: {error_message}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    choices = result.get("choices") if isinstance(result, dict) else None
    if not choices:
        emit_error(
            "OpenRouter response missing choices.",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        emit_error(
            "OpenRouter response missing message.",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    image_urls = extract_image_urls(message)
    if not image_urls:
        emit_error(
            "No images returned by model. Ensure it supports image generation.",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    try:
        mime, image_bytes = parse_data_url(image_urls[0])
    except ValueError as exc:
        emit_error(
            f"Invalid image data URL: {exc}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    output_path = resolve_output_path(out, extension_from_mime(mime))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    result_data = {"image_path": str(output_path), "model": model, "mime_type": mime, "prompt": prompt}
    if image:
        input_images = [str(p.expanduser()) for p in image]
        result_data["input_images"] = input_images
        # Backwards compat: also set input_image to the first one
        result_data["input_image"] = input_images[0]

    emit_success(result_data, settings, text=str(output_path))


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
