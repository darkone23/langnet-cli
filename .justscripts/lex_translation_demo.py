"""Translate sample lexicon rows from DuckDB via OpenRouter."""

from __future__ import annotations

import os
import re
import textwrap
import time
from collections.abc import Iterable
from pathlib import Path

import aisuite as ai
import click
import dotenv
import duckdb

from langnet.storage.db import connect_duckdb_rw
from langnet.translation import TranslationCache, TranslationRecord, build_translation_key
from langnet.translation.prompts import (
    BASE_SYSTEM,
    default_hints_for_mode,
)

dotenv.load_dotenv()

# DEFAULT_HINTS = [
#     "Translate into English. Keep abbreviations and any Sanskrit tokens unchanged. Preserve layout, punctuation, and style. Do not translate cross language examples (fr. gr. lat. an.) and do not expand abbreviations.",  # noqa: E501
#     "Do not add markdown styling such as bold, italics, or numbering.",
# ]


def get_client() -> ai.Client:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise click.ClickException("Set OPENAI_API_KEY before running translation.")

    api_base = os.getenv(
        "OPENAI_API_BASE",
        os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    os.environ["OPENAI_BASE_URL"] = api_base
    return ai.Client({"api_key": api_key})


def fetch_rows(
    db_path: str,
    table: str,
    limit: int,
    headword: str | None,
    entry_id: str | None,
) -> list[dict]:
    safe_table = table.replace('"', "")
    where_clauses = ["plain_text IS NOT NULL"]
    params: list[object] = []

    if headword:
        where_clauses.append("headword_norm = ?")
        params.append(headword)
    if entry_id:
        where_clauses.append("entry_id = ?")
        params.append(entry_id)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    params.append(limit)
    con = duckdb.connect(db_path, read_only=True)
    try:
        columns = {row[1] for row in con.execute(f"PRAGMA table_info('{safe_table}')").fetchall()}
        has_occurrence = "occurrence" in columns
        has_variant_num = "variant_num" in columns
        if has_occurrence:
            occurrence_sql = "occurrence"
        elif has_variant_num:
            occurrence_sql = "variant_num as occurrence"
        else:
            occurrence_sql = "0 as occurrence"

        query = f"""
            SELECT entry_id, {occurrence_sql}, headword_norm, plain_text
            FROM "{safe_table}"
            {where_sql}
            LIMIT ?
        """
        rows = con.execute(query, params).fetchall()
    finally:
        con.close()

    result = []
    for row_entry_id, occurrence, headword_norm, plain_text in rows:
        result.append(
            {
                "entry_id": row_entry_id,
                "occurrence": occurrence,
                "headword_norm": headword_norm,
                "plain_text": plain_text,
            }
        )
    return result


def translate_entry(  # noqa: PLR0913
    client: ai.Client,
    model: str,
    entry: dict,
    hints: Iterable[str],
    chunks: list[str],
    separator: str,
) -> list[tuple[str, str]]:
    combined_hint = "\n".join(hints)
    translated_parts: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        messages = [
            {"role": "system", "content": BASE_SYSTEM},
            {"role": "system", "content": combined_hint},
            {
                "role": "user",
                "content": chunk,
            },
        ]
        if len(chunks) > 1:
            click.echo(f"  [chunk {idx}/{len(chunks)}] sending {len(chunk)} characters")
            click.echo(textwrap.indent(chunk.strip(), "    "))
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        elapsed = time.perf_counter() - start
        content = response.choices[0].message.content or ""
        in_len = len(chunk)
        if len(chunks) > 1:
            rate = in_len / elapsed if elapsed > 0 else float("inf")
            click.echo(
                f"  [chunk {idx}/{len(chunks)}] took {elapsed:.2f}s | "
                f"in={in_len} chars | ~{rate:.1f} in-chars/s"
            )
        translated_parts.append(content)
    cleaned_parts = [part.strip() for part in translated_parts if part.strip()]
    combined = cleaned_parts[0] if len(cleaned_parts) == 1 else separator.join(cleaned_parts)
    return [(combined_hint, combined)]


def indent_block(text: str) -> str:
    return textwrap.indent(text.strip(), "  ")


def split_paragraphs(text: str) -> list[str]:
    """
    Split text on the Gaffiot paragraph marker (¶), keeping only non-empty chunks.
    Uses a newline-prefixed marker to keep boundaries obvious when rejoining.
    """
    normalized = re.split(r"\s*¶\s*", text.replace("\r\n", "\n"))
    parts = [part.strip() for part in normalized if part.strip()]
    return parts or [text.strip()]


def split_lines(text: str) -> list[str]:
    """
    Split text on line breaks, keeping only non-empty chunks.
    """
    parts = [part.strip() for part in text.splitlines() if part.strip()]
    return parts or [text]


def source_lexicon_for_mode(mode: str) -> str:
    return "gaffiot" if mode.lower() == "latin" else "dico"


def source_text_for_cache(mode: str, source_text: str) -> str:
    if mode.lower() == "latin":
        return re.sub(r"\s+", " ", source_text).strip()
    return source_text


def build_entry_translation_key(entry: dict, mode: str, model: str, hints: Iterable[str]):
    return build_translation_key(
        source_lexicon=source_lexicon_for_mode(mode),
        entry_id=str(entry["entry_id"]),
        occurrence=int(entry.get("occurrence") or 0),
        headword_norm=str(entry.get("headword_norm") or ""),
        source_text=source_text_for_cache(mode, str(entry["plain_text"])),
        model=model,
        prompt=BASE_SYSTEM,
        hint="\n".join(hints),
    )


@click.command()
@click.option(
    "--db",
    default=None,
    help=(
        "DuckDB file to read from. Defaults to lex_dico for Sanskrit mode "
        "and lex_gaffiot for Latin mode."
    ),
)
@click.option(
    "--table",
    default="entries_fr",
    show_default=True,
    help="Table name to read rows from.",
)
@click.option(
    "--limit",
    default=2,
    show_default=True,
    type=int,
    help="Number of rows to sample.",
)
@click.option(
    "--model",
    default="openai:google/gemma-4-31b-it",
    show_default=True,
    help="Model id to use via aisuite/OpenRouter.",
)
@click.option(
    "--hint",
    multiple=True,
    help="Custom translation hint. Can be passed multiple times.",
)
@click.option(
    "--mode",
    type=click.Choice(["sanskrit", "latin"], case_sensitive=False),
    default="sanskrit",
    show_default=True,
    help="Select preset hints tuned for Sanskrit (DICO) or Latin (Gaffiot).",
)
@click.option(
    "--headword",
    help="Optional headword_norm filter (exact match) to narrow the sample.",
)
@click.option(
    "--entry-id",
    help="Optional entry_id filter to narrow the sample.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Fetch and display rows/chunks without requiring OPENAI_API_KEY or calling the model.",
)
@click.option(
    "--cache-db",
    default="data/cache/langnet.duckdb",
    show_default=True,
    help="DuckDB cache for persisted translations.",
)
@click.option(
    "--write-cache",
    is_flag=True,
    help="Persist successful translations to the local translation cache.",
)
@click.option(
    "--show-cache-key",
    is_flag=True,
    help="Display the translation cache key for each row.",
)
def main(  # noqa: C901, PLR0912, PLR0913, PLR0915
    db: str,
    table: str,
    limit: int,
    model: str,
    hint: tuple[str, ...],
    mode: str,
    headword: str | None,
    entry_id: str | None,
    dry_run: bool,
    cache_db: str,
    write_cache: bool,
    show_cache_key: bool,
) -> None:
    """Translate lexicon rows from DuckDB using OpenRouter."""
    if db is None:
        db = (
            "data/build/lex_gaffiot.duckdb"
            if mode.lower() == "latin"
            else "data/build/lex_dico.duckdb"
        )
    hints = list(hint) if hint else default_hints_for_mode(mode)
    client = None if dry_run else get_client()
    rows = fetch_rows(db, table, limit, headword=headword, entry_id=entry_id)
    if not rows:
        raise click.ClickException("No rows found for given filters.")

    action = "Dry-running" if dry_run else "Translating"
    click.echo(f"{action} {len(rows)} rows from {db}:{table} using {model}")
    overall_start = time.perf_counter()
    for entry in rows:
        entry_start = time.perf_counter()
        title = f"{entry['entry_id']} (occ {entry['occurrence']})"
        click.echo("\n" + "=" * 60)
        click.echo(title)
        click.echo("- French entry:")
        click.echo(indent_block(entry["plain_text"]))

        lower_mode = mode.lower()
        if lower_mode == "latin":
            chunks = split_paragraphs(entry["plain_text"])
            separator = "\n¶ "
        elif lower_mode == "sanskrit":
            chunks = [entry["plain_text"]]
            separator = ""
        else:
            chunks = [entry["plain_text"]]
            separator = ""
        if dry_run:
            click.echo("\n- Translation skipped (--dry-run)")
            click.echo(f"  chunks={len(chunks)}")
            click.echo(f"  hints={len(hints)}")
            if show_cache_key:
                key = build_entry_translation_key(entry, lower_mode, model, hints)
                click.echo(f"  translation_id={key.translation_id}")
            continue
        assert client is not None
        translations = translate_entry(client, model, entry, hints, chunks, separator)
        for hint_text, content in translations:
            click.echo("\n- Translation: ")
            # normalize by stripping senseless markdown
            cleaned_content = content.replace("*", "")
            click.echo(indent_block(cleaned_content))
            key = build_entry_translation_key(entry, lower_mode, model, hints)
            if show_cache_key:
                click.echo(f"  translation_id={key.translation_id}")
            if write_cache:
                with connect_duckdb_rw(Path(cache_db)) as conn:
                    cache = TranslationCache(conn)
                    cache.upsert(
                        TranslationRecord(
                            key=key,
                            translated_text=cleaned_content.strip(),
                            status="ok",
                        )
                    )
                click.echo(f"  [cache] wrote {key.translation_id}")
        entry_elapsed = time.perf_counter() - entry_start
        total_in_chars = sum(len(chunk) for chunk in chunks)
        entry_rate = total_in_chars / entry_elapsed if entry_elapsed > 0 else float("inf")
        click.echo(
            f"  [entry timing] {entry_elapsed:.2f}s for {title} | "
            f"in={total_in_chars} chars | ~{entry_rate:.1f} in-chars/s"
        )
    overall_elapsed = time.perf_counter() - overall_start
    click.echo(f"\nDone. Processed {len(rows)} row(s) in {overall_elapsed:.2f}s.")


if __name__ == "__main__":
    main()
