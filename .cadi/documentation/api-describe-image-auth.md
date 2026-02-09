# describe-image Auth Subcommand

> API key management commands for storing, checking, and clearing OpenRouter API keys

## Location

| Type | Path |
|------|------|
| Script | `describe-image/src/describe_image/main.py` |

## How It Works

- auth set: Store API key in system keyring using --key or --key-stdin
- auth status: Check if key exists in env var or keyring, reports source
- auth clear: Remove stored key from system keyring
- resolve_api_key(): Checks DESCRIBE_IMAGE_API_KEY env var first, then keyring

## Usage

```bash
describe-image auth set --key sk-or-...\ndescribe-image auth status\ndescribe-image auth clear
```

## Related Docs

- [describe-image CLI - Core Structure](./api-describe-image-core.md)

---
*Created: 2026-02-09 | Task: #3*
