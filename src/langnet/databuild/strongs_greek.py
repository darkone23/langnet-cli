from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
from returns.result import Failure, Success

from langnet.normalizer.utils import strip_accents
from langnet.storage.db import connect_duckdb_ro

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_strongs_greek_path

LEX_ID = "STRONGS_GREEK_EN"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    strongs_number VARCHAR NOT NULL,
    strongs_int INTEGER NOT NULL,
    lemma_unicode VARCHAR NOT NULL,
    lemma_beta VARCHAR,
    lemma_translit VARCHAR,
    pronunciation VARCHAR,
    derivation TEXT,
    definition TEXT,
    kjv_definition TEXT,
    display_gloss TEXT NOT NULL,
    entry_hash VARCHAR NOT NULL,
    source_path VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS aliases (
    alias_key VARCHAR NOT NULL,
    alias_display VARCHAR NOT NULL,
    alias_kind VARCHAR NOT NULL,
    entry_id VARCHAR NOT NULL,
    strongs_number VARCHAR NOT NULL,
    rank INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS strongs_lexicon (
    strongs_number VARCHAR PRIMARY KEY,
    language VARCHAR NOT NULL,
    lemma_unicode VARCHAR NOT NULL,
    lemma_translit VARCHAR,
    pronunciation VARCHAR,
    description TEXT,
    source_path VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS strongs_greek_alias_key_idx ON aliases(alias_key);
CREATE INDEX IF NOT EXISTS strongs_greek_alias_entry_idx ON aliases(alias_key, entry_id);
CREATE INDEX IF NOT EXISTS strongs_greek_strongs_number_idx ON entries(strongs_number);
CREATE INDEX IF NOT EXISTS strongs_lexicon_language_idx ON strongs_lexicon(language);
"""


@dataclass
class StrongsGreekBuildConfig:
    """Configuration for building the MorphGNT Strong's Greek XML index."""

    source_path: Path
    combined_lexicon_path: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False


class StrongsGreekBuilder:
    """Build a local DuckDB index from MorphGNT's Strong's Greek XML."""

    def __init__(self, config: StrongsGreekBuildConfig) -> None:
        self.source_path = config.source_path.expanduser()
        self.combined_lexicon_path = (
            config.combined_lexicon_path.expanduser()
            if config.combined_lexicon_path is not None
            else None
        )
        self.output_path = config.output_path or default_strongs_greek_path()
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Strong's Greek XML not found at {self.source_path}")
            if self.output_path.exists():
                if self.wipe_existing:
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            apply_strongs_greek_schema(self._conn)
            strongs_lemmas = self._load_combined_lexicon()
            if strongs_lemmas:
                self._resolved_ref_lemmas = strongs_lemmas
            processed = self._load_entries()
            stats = replace(self.get_stats(), entry_count=processed)
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
            )
        except Exception as exc:  # noqa: BLE001
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.output_path,
                stats=Failure(BuildErrorStats(error=str(exc))),
                message=str(exc),
            )
        finally:
            self.cleanup()

    def _load_entries(self) -> int:
        assert self._conn is not None
        total = 0
        batch: list[dict[str, Any]] = []
        ref_lemmas = getattr(self, "_resolved_ref_lemmas", {})
        for entry in _iter_xml_entries(self.source_path, ref_lemmas=ref_lemmas):
            if self.limit is not None and total + len(batch) >= self.limit:
                break
            batch.append(entry)
            if len(batch) >= self.batch_size:
                total += self._insert_batch(batch)
                batch = []
        if batch:
            total += self._insert_batch(batch)
        return total

    def _load_combined_lexicon(self) -> dict[str, str]:
        assert self._conn is not None
        if self.combined_lexicon_path is None:
            return {}
        if not self.combined_lexicon_path.exists():
            raise FileNotFoundError(
                f"Combined Strong's lexicon not found at {self.combined_lexicon_path}"
            )

        rows = list(_iter_combined_lexicon_rows(self.combined_lexicon_path))
        if not rows:
            return {}
        self._conn.register("strongs_lexicon_batch", pa.Table.from_pylist(rows))
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO strongs_lexicon (
                    strongs_number, language, lemma_unicode, lemma_translit,
                    pronunciation, description, source_path
                )
                SELECT
                    strongs_number, language, lemma_unicode, lemma_translit,
                    pronunciation, description, source_path
                FROM strongs_lexicon_batch
                """
            )
        finally:
            self._conn.unregister("strongs_lexicon_batch")
        return {str(row["strongs_number"]): str(row["lemma_unicode"]) for row in rows}

    def _insert_batch(self, entries: Sequence[Mapping[str, Any]]) -> int:
        assert self._conn is not None
        entry_rows = [_entry_row(entry, self.source_path) for entry in entries]
        alias_rows = [
            alias_row
            for entry, entry_row in zip(entries, entry_rows, strict=True)
            for alias_row in _alias_rows(entry, entry_row[0], entry_row[1])
        ]
        entry_table = _entry_arrow_table(entry_rows)
        alias_table = _alias_arrow_table(alias_rows)
        self._conn.register("strongs_greek_entry_batch", entry_table)
        self._conn.register("strongs_greek_alias_batch", alias_table)
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO entries (
                    entry_id,
                    strongs_number,
                    strongs_int,
                    lemma_unicode,
                    lemma_beta,
                    lemma_translit,
                    pronunciation,
                    derivation,
                    definition,
                    kjv_definition,
                    display_gloss,
                    entry_hash,
                    source_path,
                    updated_at
                )
                SELECT
                    entry_id,
                    strongs_number,
                    strongs_int,
                    lemma_unicode,
                    lemma_beta,
                    lemma_translit,
                    pronunciation,
                    derivation,
                    definition,
                    kjv_definition,
                    display_gloss,
                    entry_hash,
                    source_path,
                    CURRENT_TIMESTAMP
                FROM strongs_greek_entry_batch
                """
            )
            self._conn.execute(
                """
                INSERT INTO aliases (
                    alias_key,
                    alias_display,
                    alias_kind,
                    entry_id,
                    strongs_number,
                    rank
                )
                SELECT
                    alias_key,
                    alias_display,
                    alias_kind,
                    entry_id,
                    strongs_number,
                    rank
                FROM strongs_greek_alias_batch
                """
            )
        finally:
            self._conn.unregister("strongs_greek_entry_batch")
            self._conn.unregister("strongs_greek_alias_batch")
        return len(entries)

    def get_stats(self) -> LexiconStats:
        size_mb = None
        entry_count = None
        headword_count = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3)
            conn = self._conn or duckdb.connect(str(self.output_path), read_only=True)
            try:
                entry_result = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
                alias_result = conn.execute(
                    "SELECT COUNT(DISTINCT alias_key) FROM aliases"
                ).fetchone()
                entry_count = entry_result[0] if entry_result else 0
                headword_count = alias_result[0] if alias_result else 0
            finally:
                if conn is not self._conn:
                    conn.close()
        return LexiconStats(
            lex_id=LEX_ID,
            path=str(self.output_path),
            entry_count=entry_count,
            headword_count=headword_count,
            size_mb=size_mb,
        )

    def cleanup(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def apply_strongs_greek_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create Strong's Greek dictionary tables."""
    for stmt in SCHEMA_SQL.strip().split(";"):
        sql_stmt = stmt.strip()
        if sql_stmt:
            conn.execute(sql_stmt)


def normalize_strongs_greek_key(raw: str) -> str:
    """Normalize Greek, transliteration, or Strong's-number input for lookup."""
    normalized = strip_accents(unicodedata.normalize("NFKD", raw or "")).lower()
    normalized = normalized.replace("ς", "σ")
    return "".join(ch for ch in normalized if ch.isalnum())


def lookup_strongs_greek_entries(
    headword: str, db_path: Path | None = None
) -> list[dict[str, Any]]:
    """Resolve a Greek form, transliteration, or Strong's number from the local index."""
    return lookup_strongs_greek_entries_by_headword([headword], db_path)


def lookup_strongs_greek_entries_by_headword(  # noqa: C901
    headwords: list[str], db_path: Path | None = None
) -> list[dict[str, Any]]:
    """Resolve local Strong's Greek entries from ordered lookup candidates."""
    keys: list[str] = []
    seen_keys: set[str] = set()
    for headword in headwords:
        for key in _candidate_keys(headword):
            if key and key not in seen_keys:
                seen_keys.add(key)
                keys.append(key)
    if not keys:
        return []
    if db_path is None:
        db_path = default_strongs_greek_path()
    if not db_path.exists():
        return []

    entries_by_key: dict[str, list[dict[str, Any]]] = {}
    placeholders = ",".join(["?"] * len(keys))
    with connect_duckdb_ro(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                aliases.alias_key,
                aliases.alias_display,
                aliases.alias_kind,
                aliases.rank,
                entries.entry_id,
                entries.strongs_number,
                entries.strongs_int,
                entries.lemma_unicode,
                entries.lemma_beta,
                entries.lemma_translit,
                entries.pronunciation,
                entries.derivation,
                entries.definition,
                entries.kjv_definition,
                entries.display_gloss,
                entries.entry_hash
            FROM aliases
            JOIN entries ON entries.entry_id = aliases.entry_id
            WHERE aliases.alias_key IN ({placeholders})
            ORDER BY aliases.alias_key, aliases.rank, entries.strongs_int
            """,
            keys,
        ).fetchall()
    for row in rows:
        entry = {
            "matched_alias_key": row[0],
            "matched_alias_display": row[1],
            "matched_alias_kind": row[2],
            "matched_alias_rank": row[3],
            "entry_id": row[4],
            "strongs_number": row[5],
            "strongs_int": row[6],
            "lemma_unicode": row[7],
            "lemma_beta": row[8],
            "lemma_translit": row[9],
            "pronunciation": row[10],
            "derivation": row[11],
            "definition": row[12],
            "kjv_definition": row[13],
            "display_gloss": row[14],
            "entry_hash": row[15],
        }
        entries_by_key.setdefault(str(row[0]), []).append(entry)

    results: list[dict[str, Any]] = []
    seen_entries: set[str] = set()
    for key in keys:
        for entry in entries_by_key.get(key, []):
            entry_id = str(entry["entry_id"])
            if entry_id in seen_entries:
                continue
            seen_entries.add(entry_id)
            results.append(entry)
    return results


def _candidate_keys(raw: str) -> list[str]:
    key = normalize_strongs_greek_key(raw)
    if not key:
        return []
    keys = [key]
    match = re.fullmatch(r"g?0*(\d+)", key)
    if match:
        value = int(match.group(1))
        keys.extend([f"g{value}", str(value), f"{value:05d}", f"g{value:05d}"])
    return _unique(keys)


def _iter_combined_lexicon_rows(source_path: Path) -> Iterable[dict[str, str | None]]:
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        yield from _iter_combined_json_rows(source_path)
    elif suffix in {".db", ".sqlite", ".sqlite3"}:
        yield from _iter_combined_sqlite_rows(source_path)
    elif suffix == ".csv":
        yield from _iter_combined_csv_rows(source_path)
    else:
        raise ValueError(
            f"Combined Strong's lexicon must be JSON, SQLite, or CSV (got {source_path.name})"
        )


def _iter_combined_json_rows(source_path: Path) -> Iterable[dict[str, str | None]]:
    loaded = json.loads(source_path.read_text(encoding="utf-8"))
    rows: Iterable[object]
    if isinstance(loaded, list):
        rows = loaded
    elif isinstance(loaded, Mapping):
        rows = loaded.values()
    else:
        rows = []
    for row in rows:
        if isinstance(row, Mapping):
            normalized = _combined_lexicon_row(row, source_path)
            if normalized:
                yield normalized


def _iter_combined_sqlite_rows(source_path: Path) -> Iterable[dict[str, str | None]]:
    with sqlite3.connect(str(source_path)) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            "SELECT number, lemma, xlit, pronounce, description FROM strongs ORDER BY number"
        ):
            normalized = _combined_lexicon_row(row, source_path)
            if normalized:
                yield normalized


def _iter_combined_csv_rows(source_path: Path) -> Iterable[dict[str, str | None]]:
    with source_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            normalized = _combined_lexicon_row(row, source_path)
            if normalized:
                yield normalized


def _combined_lexicon_row(
    row: Mapping[str, object], source_path: Path
) -> dict[str, str | None] | None:
    strongs_number = _canonical_strongs_number(str(row.get("number") or ""))
    lemma = str(row.get("lemma") or "").strip()
    if not strongs_number or not lemma:
        return None
    return {
        "strongs_number": strongs_number,
        "language": _strongs_language(strongs_number),
        "lemma_unicode": lemma,
        "lemma_translit": _none_if_empty(row.get("xlit")),
        "pronunciation": _none_if_empty(row.get("pronounce")),
        "description": _none_if_empty(row.get("description")),
        "source_path": str(source_path),
    }


def _canonical_strongs_number(value: str) -> str:
    match = re.search(r"([GH])?\s*0*(\d+)", (value or "").upper())
    if not match:
        return ""
    prefix = match.group(1) or ""
    if not prefix:
        return ""
    return f"{prefix}{int(match.group(2))}"


def _strongs_language(strongs_number: str) -> str:
    return "heb" if strongs_number.startswith("H") else "grc"


def _iter_xml_entries(
    source_path: Path, *, ref_lemmas: Mapping[str, str] | None = None
) -> Iterable[dict[str, Any]]:
    ref_lemmas = ref_lemmas or {}
    root = ET.parse(source_path).getroot()  # noqa: S314 - local XML source file
    for entry_el in root.iter("entry"):
        strongs_text = _child_text(entry_el, "strongs") or entry_el.attrib.get("strongs") or ""
        strongs_int = _strongs_int(strongs_text)
        if strongs_int is None:
            continue
        greek_el = entry_el.find("greek")
        lemma_unicode = (greek_el.attrib.get("unicode", "") if greek_el is not None else "").strip()
        if not lemma_unicode:
            continue
        yield {
            "strongs_int": strongs_int,
            "strongs_number": f"G{strongs_int}",
            "lemma_unicode": lemma_unicode,
            "lemma_beta": (greek_el.attrib.get("BETA", "") if greek_el is not None else "").strip(),
            "lemma_translit": (
                greek_el.attrib.get("translit", "") if greek_el is not None else ""
            ).strip(),
            "pronunciation": _pronunciation(entry_el),
            "derivation": _child_text(entry_el, "strongs_derivation", ref_lemmas=ref_lemmas),
            "definition": _child_text(entry_el, "strongs_def", ref_lemmas=ref_lemmas),
            "kjv_definition": _clean_kjv(_child_text(entry_el, "kjv_def", ref_lemmas=ref_lemmas)),
        }


def _child_text(
    element: ET.Element, tag: str, *, ref_lemmas: Mapping[str, str] | None = None
) -> str | None:
    child = element.find(tag)
    if child is None:
        return None
    return _collapse_ws(_element_text_with_refs(child, ref_lemmas=ref_lemmas or {}))


def _element_text_with_refs(element: ET.Element, *, ref_lemmas: Mapping[str, str]) -> str:
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if child.tag == "strongsref":
            ref = _strongs_ref_text(child, ref_lemmas=ref_lemmas)
            if ref:
                parts.append(ref)
        else:
            parts.append(_element_text_with_refs(child, ref_lemmas=ref_lemmas))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _strongs_ref_text(element: ET.Element, *, ref_lemmas: Mapping[str, str]) -> str:
    number = _strongs_int(element.attrib.get("strongs") or "")
    if number is None:
        return ""
    language = (element.attrib.get("language") or "").strip().lower()
    prefix = "H" if language == "hebrew" else "G"
    strongs_number = f"{prefix}{number}"
    return ref_lemmas.get(strongs_number, strongs_number)


def _pronunciation(entry_el: ET.Element) -> str | None:
    child = entry_el.find("pronunciation")
    if child is None:
        return None
    return child.attrib.get("strongs") or _collapse_ws("".join(child.itertext())) or None


def _strongs_int(value: str) -> int | None:
    match = re.search(r"\d+", value or "")
    return int(match.group(0)) if match else None


def _clean_kjv(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    cleaned = re.sub(r"^:--\s*", "", cleaned)
    return cleaned or None


def _entry_row(
    entry: Mapping[str, Any], source_path: Path
) -> tuple[
    str,
    str,
    int,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str,
    str,
    str,
]:
    strongs_number = str(entry["strongs_number"])
    entry_id = f"strongs-greek:{strongs_number}"
    display_gloss = _display_gloss(entry)
    hash_text = "\0".join(
        str(entry.get(key) or "")
        for key in (
            "strongs_number",
            "lemma_unicode",
            "lemma_beta",
            "lemma_translit",
            "pronunciation",
            "derivation",
            "definition",
            "kjv_definition",
        )
    )
    entry_hash = hashlib.sha256(hash_text.encode()).hexdigest()
    return (
        entry_id,
        strongs_number,
        int(entry["strongs_int"]),
        str(entry["lemma_unicode"]),
        _none_if_empty(entry.get("lemma_beta")),
        _none_if_empty(entry.get("lemma_translit")),
        _none_if_empty(entry.get("pronunciation")),
        _none_if_empty(entry.get("derivation")),
        _none_if_empty(entry.get("definition")),
        _none_if_empty(entry.get("kjv_definition")),
        display_gloss,
        entry_hash,
        str(source_path),
    )


def _display_gloss(entry: Mapping[str, Any]) -> str:
    parts = [
        _gloss_part(entry.get("derivation")),
        _gloss_part(entry.get("definition")),
    ]
    kjv = _gloss_part(entry.get("kjv_definition"))
    if kjv:
        parts.append(f"KJV: {kjv}")
    return "; ".join(part for part in parts if part) or str(entry["lemma_unicode"])


def _gloss_part(value: object) -> str:
    return str(value or "").strip().strip(";").strip()


def _alias_rows(
    entry: Mapping[str, Any], entry_id: str, strongs_number: str
) -> list[tuple[str, str, str, str, str, int]]:
    aliases: list[tuple[str, str, str, int]] = []
    strongs_int = int(entry["strongs_int"])
    aliases.extend(
        [
            (f"G{strongs_int}", "strongs_number", 0),
            (f"G{strongs_int:05d}", "strongs_number", 0),
            (str(strongs_int), "strongs_number", 0),
            (f"{strongs_int:05d}", "strongs_number", 0),
        ]
    )
    lemma = str(entry["lemma_unicode"])
    aliases.append((lemma, "lemma", 0))
    for form in _generated_greek_forms(lemma):
        aliases.append((form, "generated_form", 1))
    translit = str(entry.get("lemma_translit") or "").strip()
    if translit:
        aliases.append((translit, "transliteration", 2))

    rows: list[tuple[str, str, str, str, str, int]] = []
    seen: set[tuple[str, str]] = set()
    for display, kind, rank in aliases:
        key = normalize_strongs_greek_key(display)
        if not key:
            continue
        fingerprint = (key, kind)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        rows.append((key, display, kind, entry_id, strongs_number, rank))
    return rows


def _generated_greek_forms(lemma: str) -> list[str]:
    forms: list[str] = []
    if lemma.endswith("ας"):
        stem = lemma[:-2]
        forms.extend([f"{stem}ου", f"{stem}ᾳ", f"{stem}αν"])
    if lemma.endswith("ης"):
        stem = lemma[:-2]
        forms.extend([f"{stem}ου", f"{stem}ῃ", f"{stem}ην"])
    if lemma.endswith("ος"):
        stem = lemma[:-2]
        forms.extend([f"{stem}ου", f"{stem}ῳ", f"{stem}ον"])
    if lemma.endswith("ους"):
        stem = lemma[:-1]
        forms.extend([stem, f"{stem}ν"])
    return forms


def _entry_arrow_table(
    rows: Sequence[
        tuple[
            str,
            str,
            int,
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            str,
            str,
            str,
        ]
    ],
) -> pa.Table:
    return pa.table(
        {
            "entry_id": [row[0] for row in rows],
            "strongs_number": [row[1] for row in rows],
            "strongs_int": [row[2] for row in rows],
            "lemma_unicode": [row[3] for row in rows],
            "lemma_beta": [row[4] for row in rows],
            "lemma_translit": [row[5] for row in rows],
            "pronunciation": [row[6] for row in rows],
            "derivation": [row[7] for row in rows],
            "definition": [row[8] for row in rows],
            "kjv_definition": [row[9] for row in rows],
            "display_gloss": [row[10] for row in rows],
            "entry_hash": [row[11] for row in rows],
            "source_path": [row[12] for row in rows],
        }
    )


def _alias_arrow_table(rows: Sequence[tuple[str, str, str, str, str, int]]) -> pa.Table:
    return pa.table(
        {
            "alias_key": [row[0] for row in rows],
            "alias_display": [row[1] for row in rows],
            "alias_kind": [row[2] for row in rows],
            "entry_id": [row[3] for row in rows],
            "strongs_number": [row[4] for row in rows],
            "rank": [row[5] for row in rows],
        }
    )


def _collapse_ws(text: str) -> str:
    return " ".join((text or "").split())


def _none_if_empty(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
