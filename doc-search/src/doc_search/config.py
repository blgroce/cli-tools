"""Configuration constants for doc-search."""
import os
from pathlib import Path

DB_DIR = Path.home() / ".local" / "share" / "doc-search"
DB_NAME = "doc-search.db"
DB_PATH = DB_DIR / DB_NAME

# AWS Textract (configurable via env vars)
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
S3_UPLOAD_PATH = os.environ.get("DOC_SEARCH_S3_PATH", "s3://transaction-coordinator/textract-temp/")

# LLM (OpenRouter)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY_ENV = "SPROCKET_OPENROUTER_KEY"
DEFAULT_MODEL = "google/gemini-2.5-flash"

LLM_SYSTEM_PROMPT = """You are a document analysis assistant. Answer questions using ONLY the document text provided below.

Rules:
- Answer strictly from the document text. Do not use outside knowledge.
- Cite the relevant section or paragraph when possible.
- Quote exact values, dates, dollar amounts, and names from the document.
- If the answer is not found in the document, say clearly: "This information is not found in the document."
- Be concise and direct."""
