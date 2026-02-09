"""Standard error handling and exit codes for CLI tools."""

import sys
from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_ARGS = 2
    NOT_FOUND = 3
    EXTERNAL_FAILURE = 4


class CLIError(Exception):
    """Base exception for CLI tools."""

    def __init__(self, message: str, code: str = "ERROR", exit_code: ExitCode = ExitCode.GENERAL_ERROR):
        self.message = message
        self.code = code
        self.exit_code = exit_code
        super().__init__(message)


class InvalidArgsError(CLIError):
    """Raised when arguments are invalid."""

    def __init__(self, message: str):
        super().__init__(message, code="INVALID_ARGS", exit_code=ExitCode.INVALID_ARGS)


class NotFoundError(CLIError):
    """Raised when a resource is not found."""

    def __init__(self, message: str):
        super().__init__(message, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)


class ExternalError(CLIError):
    """Raised when an external dependency fails (API, network, etc)."""

    def __init__(self, message: str):
        super().__init__(message, code="EXTERNAL_FAILURE", exit_code=ExitCode.EXTERNAL_FAILURE)
