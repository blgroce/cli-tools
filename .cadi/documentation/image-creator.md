# Image Creator CLI

> Generate images with OpenRouter (Nano Banana Pro by default).

## Location

| Type | Path |
|------|------|
| Package | `image-creator/` |
| Entry point | `image-creator/src/image_creator/main.py` |

## How It Works

- Uses Typer for CLI with standard flags (`--help`, `--version`, `--quiet`, `--format`)
- Stores OpenRouter API keys in OS keyring or reads from `OPENROUTER_API_KEY`
- Sends requests to OpenRouter `/chat/completions` with `modalities: ["image","text"]`
- Saves the first returned base64 image to a file and outputs the path
- Supports `--model` override plus `--aspect-ratio` and `--image-size` via `image_config`

## Usage

```bash
# Install
cd image-creator && pip install .

# Store key safely
image-creator auth set --key "sk-..."
cat key.txt | image-creator auth set --key-stdin

# Check key status (no secrets printed)
image-creator auth status

# Generate an image (default model)
image-creator create "A nano banana plated like fine dining"

# Custom output path and model
image-creator create "Futuristic banana stand" --out output.png --model google/gemini-3-pro-image-preview

# Image configuration
image-creator create "City skyline at dusk" --aspect-ratio 16:9 --image-size 2K
```

## Related Docs

- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-04*
