# describe-image CLI - Core Structure

> Core CLI structure and output helpers for the describe-image tool

## Location

| Type | Path |
|------|------|
| Script | `describe-image/src/describe_image/main.py` |

## How It Works

- Typer CLI framework with add_completion=False, no_args_is_help=True
- ExitCode enum: SUCCESS=0, GENERAL_ERROR=1, INVALID_ARGS=2, NOT_FOUND=3, EXTERNAL_FAILURE=4
- OutputSettings dataclass tracks format (json/text) and quiet mode
- emit_success() outputs JSON {success: true, data: ...} or plain text
- emit_error() outputs JSON {error: true, code: ..., message: ...} to stderr
- resolve_api_key() checks DESCRIBE_IMAGE_API_KEY env var, then keyring
- Constants: DEFAULT_MODEL=google/gemini-2.5-flash-preview:thinking, OPENROUTER_URL

## Usage

```bash
describe-image --help\ndescribe-image --version\ndescribe-image --format text --quiet
```

## Related Docs

- None yet

---
*Created: 2026-02-09 | Task: #2*
