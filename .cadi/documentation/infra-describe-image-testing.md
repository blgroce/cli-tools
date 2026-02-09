# describe-image CLI End-to-End Testing

> Verification of describe-image CLI tool functionality including help, version, auth, describe commands, error handling, and output formats

## Location

| Type | Path |
|------|------|
| Script | `describe-image/src/describe_image/main.py` |

## How It Works

- Installed package with pip install -e .
- Verified --help displays correct usage and commands
- Verified --version shows 0.1.0
- Tested auth subcommand (status, set, clear)
- Tested describe command error handling (no API key, non-existent file, unsupported format)
- Verified JSON output format matches spec (success: true/data or error: true/code/message)
- Verified --format text output works correctly
- Verified exit codes match spec (0=success, 2=invalid args, 3=not found, 4=external failure)
- All 4 unit tests pass for --out option functionality

## Usage

```bash
describe-image --help\ndescribe-image --version\ndescribe-image auth status\ndescribe-image describe path/to/image.png --out output.txt
```

## Related Docs

- [Output Saving for describe-image CLI](./infra-describe-image-output-saving.md)
- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [describe-image Package Structure](./infra-describe-image-structure.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-09 | Task: #6*
