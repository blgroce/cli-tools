from __future__ import annotations

import json
import sys
from enum import IntEnum
from pathlib import Path
from typing import Optional

import typer

from . import __version__

APP_NAME = "doc-search"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="CLI for ingesting PDFs into SQLite FTS5 and querying them with LLM-powered Q&A.",
)


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_ARGS = 2
    NOT_FOUND = 3
    EXTERNAL_FAILURE = 4


def _version_callback(value: bool) -> None:
    if value:
        print(f"{APP_NAME} {__version__}")
        raise typer.Exit(ExitCode.SUCCESS)


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        is_eager=True,
        callback=_version_callback,
    ),
    format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or text",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress non-error output",
    ),
) -> None:
    from .output import OutputSettings
    from .db import init_db

    if format not in {"json", "text"}:
        print(
            json.dumps({"error": True, "code": "INVALID_INPUT", "message": f"Invalid format: {format}"}),
            file=sys.stderr,
        )
        raise typer.Exit(ExitCode.INVALID_ARGS)

    ctx.ensure_object(dict)
    ctx.obj = OutputSettings(format=format, quiet=quiet)
    init_db()


@app.command()
def ingest(
    ctx: typer.Context,
    pdf: str = typer.Argument(..., help="Path to PDF file"),
    name: Optional[str] = typer.Option(None, "--name", help="Document name (defaults to filename)"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
) -> None:
    """Extract text from a PDF and store it in the database."""
    from .output import get_settings, emit_success, emit_error
    from .db import get_connection, insert_document
    from .extractor import extract_pdf

    settings = get_settings(ctx)

    try:
        result = extract_pdf(pdf)
    except (ValueError, RuntimeError) as e:
        emit_error(str(e), settings, code="EXTRACTION_ERROR")

    doc_name = name or Path(pdf).stem
    source_path = str(Path(pdf).expanduser().resolve())
    metadata = json.dumps({"form_fields": result.form_fields}) if result.form_fields else "{}"

    conn = get_connection()
    doc_id = insert_document(
        conn=conn,
        name=doc_name,
        source_path=source_path,
        extracted_text=result.text,
        page_count=result.page_count,
        char_count=result.char_count,
        tags=tags,
        metadata=metadata,
    )
    conn.close()

    data = {
        "id": doc_id,
        "name": doc_name,
        "page_count": result.page_count,
        "char_count": result.char_count,
        "tags": tags,
    }
    warning_line = ""
    if result.warning:
        data["warning"] = result.warning
        warning_line = f"\nWarning: {result.warning}"

    text_output = (
        f"Ingested: {doc_name} (ID {doc_id})\n"
        f"Pages: {result.page_count} | Chars: {result.char_count}"
        f"{warning_line}"
    )
    emit_success(data, settings, text=text_output)


@app.command()
def ask(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="Question to ask about the document"),
    doc: Optional[int] = typer.Option(None, "--doc", help="Document ID (defaults to most recent)"),
    model: Optional[str] = typer.Option(None, "--model", help="Override LLM model"),
) -> None:
    """Ask a question about a document using LLM."""
    from .output import get_settings, emit_success, emit_error
    from .db import get_connection, get_document, get_latest_document
    from .llm import ask_document

    settings = get_settings(ctx)
    conn = get_connection()

    if doc is not None:
        document = get_document(conn, doc)
        if not document:
            conn.close()
            emit_error(f"Document ID {doc} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)
    else:
        document = get_latest_document(conn)
        if not document:
            conn.close()
            emit_error("No documents in database. Ingest a PDF first.", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    conn.close()

    try:
        answer = ask_document(question, document["extracted_text"], model=model)
    except (ValueError, RuntimeError) as e:
        emit_error(str(e), settings, code="LLM_ERROR", exit_code=ExitCode.EXTERNAL_FAILURE)

    data = {
        "document_id": document["id"],
        "document_name": document["name"],
        "question": question,
        "answer": answer,
    }
    text_output = f"Document: {document['name']} (ID {document['id']})\nQ: {question}\n\n{answer}"
    emit_success(data, settings, text=text_output)


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", help="Max results"),
) -> None:
    """Search documents using FTS5 keyword matching."""
    from .output import get_settings, emit_success, emit_error
    from .db import get_connection, search_documents

    settings = get_settings(ctx)
    conn = get_connection()
    results = search_documents(conn, query, limit=limit)
    conn.close()

    if not results:
        emit_error(f"No results for: {query}", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    data = {"query": query, "count": len(results), "results": results}
    lines = [f"Search: \"{query}\" ({len(results)} results)\n"]
    for r in results:
        lines.append(f"  [{r['id']}] {r['name']} ({r['tags'] or 'no tags'})")
        lines.append(f"      ...{r['snippet']}...")
    emit_success(data, settings, text="\n".join(lines))


@app.command("list")
def list_docs(
    ctx: typer.Context,
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
) -> None:
    """List stored documents."""
    from .output import get_settings, emit_success, emit_error
    from .db import get_connection, list_documents

    settings = get_settings(ctx)
    conn = get_connection()
    docs = list_documents(conn, tag=tag)
    conn.close()

    if not docs:
        msg = "No documents found" + (f" with tag '{tag}'" if tag else "")
        emit_error(msg, settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    data = {"count": len(docs), "documents": docs}
    lines = [f"Documents: {len(docs)}\n"]
    for d in docs:
        lines.append(f"  [{d['id']}] {d['name']}")
        lines.append(f"      {d['page_count']} pages, {d['char_count']} chars | tags: {d['tags'] or 'none'} | {d['created_at']}")
    emit_success(data, settings, text="\n".join(lines))


@app.command()
def show(
    ctx: typer.Context,
    doc_id: int = typer.Argument(..., help="Document ID"),
) -> None:
    """Display full extracted text of a document."""
    from .output import get_settings, emit_success, emit_error
    from .db import get_connection, get_document

    settings = get_settings(ctx)
    conn = get_connection()
    document = get_document(conn, doc_id)
    conn.close()

    if not document:
        emit_error(f"Document ID {doc_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    metadata = json.loads(document["metadata"]) if document["metadata"] else {}
    form_fields = metadata.get("form_fields", {})

    data = {
        "id": document["id"],
        "name": document["name"],
        "page_count": document["page_count"],
        "char_count": document["char_count"],
        "text": document["extracted_text"],
        "form_fields": form_fields,
    }

    form_section = ""
    if form_fields:
        kv_lines = [f"  {k}: {v}" for k, v in form_fields.items()]
        form_section = f"\n\n--- Form Fields ({len(form_fields)}) ---\n" + "\n".join(kv_lines)

    text_output = (
        f"=== {document['name']} (ID {document['id']}) ===\n"
        f"Pages: {document['page_count']} | Chars: {document['char_count']}\n\n"
        f"{document['extracted_text']}"
        f"{form_section}"
    )
    emit_success(data, settings, text=text_output)


@app.command()
def delete(
    ctx: typer.Context,
    doc_id: int = typer.Argument(..., help="Document ID"),
) -> None:
    """Delete a document from the database."""
    from .output import get_settings, emit_success, emit_error
    from .db import get_connection, get_document, delete_document

    settings = get_settings(ctx)
    conn = get_connection()

    document = get_document(conn, doc_id)
    if not document:
        conn.close()
        emit_error(f"Document ID {doc_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    delete_document(conn, doc_id)
    conn.close()

    data = {"id": doc_id, "name": document["name"], "deleted": True}
    text_output = f"Deleted: {document['name']} (ID {doc_id})"
    emit_success(data, settings, text=text_output)


if __name__ == "__main__":
    app()
