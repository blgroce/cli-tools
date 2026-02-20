"""OpenRouter embedding client."""

import os
import sys
from typing import Optional

import requests

from .config import OPENROUTER_URL, EMBEDDING_MODEL, ENV_API_KEY


def get_api_key() -> str:
    key = os.environ.get(ENV_API_KEY)
    if not key:
        print(
            f"Error: {ENV_API_KEY} environment variable not set",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return key


def embed_texts(
    texts: list[str],
    api_key: Optional[str] = None,
    model: str = EMBEDDING_MODEL,
    batch_size: int = 50,
) -> list[list[float]]:
    """Embed a list of texts via OpenRouter. Returns list of embedding vectors.

    Batches requests to avoid exceeding API limits.
    """
    if not api_key:
        api_key = get_api_key()

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": batch},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Embedding API error: {data['error']}")

        # Sort by index to maintain order
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        all_embeddings.extend([d["embedding"] for d in sorted_data])

    return all_embeddings


def embed_query(query: str, api_key: Optional[str] = None) -> list[float]:
    """Embed a single query string."""
    results = embed_texts([query], api_key=api_key)
    return results[0]
