"""JSON output helpers for CLI tools."""

import json
import sys
from typing import Any

from .errors import CLIError, ExitCode


def success(data: Any) -> None:
    """Print success response to stdout and exit 0."""
    print(json.dumps({"success": True, "data": data}))
    sys.exit(ExitCode.SUCCESS)


def error(message: str, code: str = "ERROR", exit_code: ExitCode = ExitCode.GENERAL_ERROR) -> None:
    """Print error response to stderr and exit with code."""
    print(json.dumps({"error": True, "code": code, "message": message}), file=sys.stderr)
    sys.exit(exit_code)


def handle_error(e: CLIError) -> None:
    """Handle a CLIError and exit."""
    error(e.message, e.code, e.exit_code)


def output(data: Any) -> None:
    """Print JSON data to stdout without exiting. Use for streaming or partial output."""
    print(json.dumps(data))
