# Output Saving for describe-image CLI

> Save AI-generated image descriptions to file using --out/-o option

## Location

| Type | Path |
|------|------|
| Feature | `describe-image/src/describe_image/main.py` |

## How It Works

- Added --out/-o option to describe command
- If path is file, saves directly to that path
- If path is directory, generates timestamped filename (description-YYYYMMDD-HHMMSS.txt)
- Creates parent directories if they don't exist
- Includes 'saved_to' field in JSON success output when saving

## Usage

```bash
describe-image describe image.png --out /path/to/output.txt\ndescribe-image describe image.png -o /path/to/output-dir/
```

## Related Docs

- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [describe-image Package Structure](./infra-describe-image-structure.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-09 | Task: #5*
