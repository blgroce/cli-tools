"""OpenRouter LLM client for document Q&A."""
from __future__ import annotations

import os

import requests

from .config import DEFAULT_MODEL, LLM_SYSTEM_PROMPT, OPENROUTER_KEY_ENV, OPENROUTER_URL


def ask_document(question: str, document_text: str, model: str | None = None) -> str:
    """Send a question + document text to the LLM and return the answer.

    Raises ValueError if the API key is not set.
    Raises RuntimeError on API errors.
    """
    api_key = os.environ.get(OPENROUTER_KEY_ENV)
    if not api_key:
        raise ValueError(
            f"OpenRouter API key not set. Export {OPENROUTER_KEY_ENV} or add it to ~/assistant/.env"
        )

    model = model or DEFAULT_MODEL
    user_message = f"## Document Text\n\n{document_text}\n\n## Question\n\n{question}"

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter API error ({resp.status_code}): {resp.text}")

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"No response from model. Raw: {data}")

    return choices[0]["message"]["content"]
