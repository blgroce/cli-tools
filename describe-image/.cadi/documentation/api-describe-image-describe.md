# describe-image describe Command

> CLI command to send images to OpenRouter API for AI-powered description

## Location

| Type | Path |
|------|------|
| Script | `describe-image/src/describe_image/main.py` |

## How It Works

- Takes image file path as required argument
- Validates file exists, is a file, and has supported extension (jpg/jpeg/png/gif/webp)
- Base64 encodes the image and detects MIME type
- Builds OpenRouter API request with image as data URL in content array
- Sends POST to OpenRouter with Bearer token authentication
- Parses response and extracts description from choices[0].message.content
- Supports --model to override default (google/gemini-2.5-flash-preview:thinking)
- Supports --prompt to customize description prompt (default: 'Describe this image in detail.')
- Returns JSON output by default, text output with --format text

## Usage

```bash
describe-image describe path/to/image.jpg\ndescribe-image describe image.png --model google/gemini-2.5-pro-preview\ndescribe-image describe photo.webp --prompt 'What objects are in this image?'\ndescribe-image describe --format text image.gif
```

## Related Docs

- None yet

---
*Created: 2026-02-09 | Task: #4*
