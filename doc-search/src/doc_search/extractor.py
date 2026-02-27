"""PDF text extraction using AWS Textract.

Uses Textract's AnalyzeDocument (async) to extract text with proper handling of
form fields, filled-in blanks, checkboxes, and tables. Multi-page PDFs are
uploaded to S3 for async processing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import AWS_REGION, S3_UPLOAD_PATH


@dataclass
class ExtractionResult:
    text: str
    page_count: int
    char_count: int
    form_fields: dict[str, str]  # key-value pairs extracted by Textract
    warning: Optional[str] = None


def extract_pdf(pdf_path: str) -> ExtractionResult:
    """Extract text from a PDF using AWS Textract.

    Uses start_document_analysis (async) for multi-page PDF support.
    Requires AWS credentials and an S3 bucket for temporary upload.

    Returns ExtractionResult with text, page count, char count, and optional warning.
    Raises ValueError if the file doesn't exist or is not a PDF.
    Raises RuntimeError on Textract API errors.
    """
    from textractor import Textractor
    from textractor.data.constants import TextractFeatures

    path = Path(pdf_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {path}")

    try:
        extractor = Textractor(region_name=AWS_REGION)
        document = extractor.start_document_analysis(
            file_source=str(path),
            features=[TextractFeatures.FORMS, TextractFeatures.TABLES],
            s3_upload_path=S3_UPLOAD_PATH,
            save_image=False,
        )
    except Exception as e:
        raise RuntimeError(f"Textract extraction failed: {e}") from e

    import re
    # Textract outputs double-newlines after every line — collapse runs of 3+
    # blank lines down to a single blank line to reduce token waste
    raw_text = document.text
    text = re.sub(r'\n{3,}', '\n\n', raw_text).strip()
    page_count = len(document.pages)
    char_count = len(text)

    # Extract key-value pairs from Textract FORMS response
    form_fields: dict[str, str] = {}
    for page in document.pages:
        for kv in page.key_values:
            key = str(kv.key).strip()
            value = str(kv.value).strip() if kv.value else ""
            if key and value:
                form_fields[key] = value

    if char_count == 0:
        raise ValueError(
            "No text extracted — Textract could not read this PDF. "
            "It may be a corrupted file or unsupported format."
        )

    warning = None
    if page_count > 0:
        avg_chars = char_count / page_count
        if avg_chars < 50:
            warning = (
                f"Low text density ({avg_chars:.0f} chars/page avg) — "
                "this may be a scanned PDF with limited extractable text."
            )

    return ExtractionResult(
        text=text,
        page_count=page_count,
        char_count=char_count,
        form_fields=form_fields,
        warning=warning,
    )
