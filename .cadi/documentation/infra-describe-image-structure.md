# describe-image Package Structure

> CLI tool package for image description via OpenRouter with Gemini Flash

## Location

| Type | Path |
|------|------|
| Config | `describe-image/pyproject.toml` |

## How It Works

- Standard Python package structure following cli-tools conventions
- Uses setuptools for building
- Dependencies: typer (CLI), requests (HTTP), keyring (credential storage)
- Entry point: describe-image command maps to describe_image.main:app

## Usage

```bash
cd describe-image && pip install -e .
```

## Related Docs

- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-09 | Task: #1*
