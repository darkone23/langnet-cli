from __future__ import annotations

import contextlib
import hashlib
import logging
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

import duckdb
from bs4 import BeautifulSoup
from bs4.element import Tag
from returns.result import Failure, Success

from langnet.normalizer.utils import strip_accents

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_dico_path

logger = logging.getLogger(__name__)

LEX_ID = "DICO_FR_SAN"
DEFAULT_SOURCE = Path.home() / "langnet-tools" / "sanskrit-heritage" / "webroot" / "htdocs" / "DICO"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries_fr (
    entry_id VARCHAR NOT NULL,
    occurrence INTEGER NOT NULL,
    headword_deva VARCHAR,
    headword_roma VARCHAR,
    headword_norm VARCHAR,
    variant_num INTEGER,
    body_html TEXT,
    plain_text TEXT,
    source_page VARCHAR,
    PRIMARY KEY (entry_id, occurrence)
);

"""


@dataclass
class DicoBuildConfig:
    """
    Configuration for DicoBuilder.
    """

    source_dir: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False


def _normalize_id(entry_id: str) -> str:
    """
    Build a lowercase, accent-free key for search. Anchor names are already ASCII-like,
    but this keeps parity with other builders.
    """
    return strip_accents((entry_id or "").strip()).lower()


def _parse_variant(entry_id: str) -> int | None:
    """
    Extract variant number from anchor patterns like foo#1 or foo_2.
    """
    match = re.search(r"[#_](\d+)$", entry_id or "")
    if match:
        try:
            return int(match.group(1))
        except Exception:  # pragma: no cover - defensive
            return None
    return None


def _strip_leading_headword(text: str, headwords: Iterable[str]) -> str:
    """
    Remove a single leading occurrence of the headword (raw or normalized) from text.
    Mirrors the Gaffiot approach to keep plain_text focused on the definition.
    """
    trimmed = (text or "").lstrip()
    trimmed_lower = trimmed.lower()
    bases = [hw.lower() for hw in headwords if hw]
    for base in bases:
        for sep in ("", " ", ",", ".", ";", ":", "-", " ,", " ."):
            candidate = base + sep
            if trimmed_lower.startswith(candidate):
                cut = len(candidate)
                return trimmed[cut:].lstrip()
    return text


def _strip_variant_suffix(text: str) -> str:
    """
    Drop a trailing _N or #N suffix used for hom/variant markers.
    """
    return re.sub(r"([#_]\d+)$", "", text or "")


def _extract_plain_text(chunk_soup: BeautifulSoup) -> str:
    """
    Flatten HTML into readable text while preserving meaningful breaks.

    - Treat <br> and <p> as newlines so examples/notes stay separated.
    - Collapse other whitespace to single spaces to avoid spurious line breaks
      introduced by HTML formatting.
    """
    BREAK = "__LN__"

    for br in chunk_soup.find_all("br"):
        br.replace_with(BREAK)
    for p in chunk_soup.find_all("p"):
        p.insert_before(BREAK)

    text = chunk_soup.get_text(" ", strip=False)
    text = text.replace("\r", "")
    text = re.sub(r"\s+", " ", text)
    text = text.replace(f"{BREAK} ", f"{BREAK}")
    text = text.replace(f" {BREAK}", f"{BREAK}")
    text = text.replace(BREAK, "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


class DicoBuilder:
    """
    Build DICO French→Sanskrit index into DuckDB.
    """

    def __init__(self, config: DicoBuildConfig) -> None:
        self.source_dir = (config.source_dir or DEFAULT_SOURCE).expanduser()
        self.output_path = config.output_path or default_dico_path()
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if not self.source_dir.exists():
                raise FileNotFoundError(f"DICO source directory not found at {self.source_dir}")

            if self.output_path.exists():
                if self.wipe_existing:
                    logger.info("Deleting existing DICO index at %s", self.output_path)
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    logger.info("DICO index already exists; skipping rebuild")
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            logger.info(
                "Building DICO index",
                extra={
                    "source": str(self.source_dir),
                    "output": str(self.output_path),
                    "batch_size": self.batch_size,
                    "limit": self.limit,
                },
            )
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            for stmt in SCHEMA_SQL.strip().split(";"):
                sql_stmt = stmt.strip()
                if sql_stmt:
                    self._conn.execute(sql_stmt)

            processed = self._load_entries()
            stats = replace(self.get_stats(), entry_count=processed)
            logger.info(
                "Finished DICO index",
                extra={
                    "output": str(self.output_path),
                    "processed": processed,
                    "size_mb": stats.size_mb,
                },
            )
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to build DICO index: %s", exc)
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
        start_time = time.perf_counter()
        total = 0
        entries_batch = []

        for idx, entry in enumerate(self._iter_entries(), start=1):
            entries_batch.append(entry)

            if self.limit is not None and total + len(entries_batch) >= self.limit:
                # Trim to respect limit and flush.
                remaining = self.limit - total
                entries_batch = entries_batch[:remaining]
                self._flush_entries(entries_batch)
                total += len(entries_batch)
                entries_batch.clear()
                break

            if len(entries_batch) >= self.batch_size:
                batch_size = len(entries_batch)
                self._flush_entries(entries_batch)
                total += batch_size
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.info(
                    "Inserted DICO batch: %s entries (total=%s, elapsed_ms=%s)",
                    batch_size,
                    total,
                    elapsed_ms,
                )
                entries_batch.clear()

        if entries_batch:
            batch_size = len(entries_batch)
            self._flush_entries(entries_batch)
            total += batch_size
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                "Inserted final DICO batch: %s entries (total=%s, elapsed_ms=%s)",
                batch_size,
                total,
                elapsed_ms,
            )

        return total

    def _flush_entries(self, entries_batch) -> None:
        assert self._conn is not None
        if entries_batch:
            self._conn.executemany(
                """
                INSERT INTO entries_fr (
                    entry_id,
                    occurrence,
                    headword_deva,
                    headword_roma,
                    headword_norm,
                    variant_num,
                    body_html,
                    plain_text,
                    source_page
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                entries_batch,
            )

    def _iter_entries(self):
        seen_bodies: dict[str, set[str]] = {}
        for html_path in self._iter_source_files():
            page = html_path.stem
            html = html_path.read_text(encoding="utf-8", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            yield from self._parse_page(soup, page, seen_bodies)

    def _iter_source_files(self):
        def _sort_key(path: Path):
            if path.stem.isdigit():
                return (0, int(path.stem))
            return (1, path.stem)

        return sorted(self.source_dir.glob("*.html"), key=_sort_key)

    def _parse_page(self, soup: BeautifulSoup, page: str, seen_bodies: dict[str, set[str]]):
        deva_spans = soup.find_all("span", class_="deva")
        for idx, span in enumerate(deva_spans):
            headword_deva = span.get_text(strip=True)
            chunk_nodes = self._collect_chunk(
                span, deva_spans[idx + 1] if idx + 1 < len(deva_spans) else None
            )
            chunk_html = "".join(str(node) for node in chunk_nodes)
            chunk_soup = BeautifulSoup(chunk_html, "lxml")
            anchor = chunk_soup.find("a", class_="navy", attrs={"name": True})
            if anchor is None:
                logger.warning(
                    "Skipping entry without anchor on page %s (deva=%s)", page, headword_deva
                )
                continue
            entry_id = anchor["name"].strip()
            body_hash = hashlib.sha1(chunk_html.encode("utf-8")).hexdigest()
            seen_set = seen_bodies.setdefault(entry_id, set())
            if body_hash in seen_set:
                continue
            occurrence = len(seen_set)
            seen_set.add(body_hash)

            headword_roma_raw = anchor.get_text(strip=True)
            headword_roma = _strip_variant_suffix(headword_roma_raw)
            variant_num = _parse_variant(entry_id)
            base_entry_id = _strip_variant_suffix(entry_id)
            headword_norm = _normalize_id(base_entry_id)
            plain_text = _extract_plain_text(chunk_soup)
            plain_text = _strip_leading_headword(
                plain_text, [headword_roma, base_entry_id, headword_deva]
            )
            yield (
                entry_id,
                occurrence,
                headword_deva,
                headword_roma,
                headword_norm,
                variant_num,
                chunk_html,
                plain_text,
                page,
            )

    def _collect_chunk(self, start_span: Tag, next_span: Tag | None):
        nodes = [start_span]
        cursor = start_span.next_sibling
        while cursor is not None and cursor is not next_span:
            if isinstance(cursor, Tag) and next_span is not None and cursor is next_span:
                break
            nodes.append(cursor)
            cursor = cursor.next_sibling
        return nodes

    def get_stats(self) -> LexiconStats:
        size_mb = None
        entry_count = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3)
        try:
            conn = duckdb.connect(str(self.output_path))
            result = conn.execute("SELECT COUNT(*) FROM entries_fr").fetchone()
            entry_count = result[0] if result else 0
        except Exception:
            entry_count = None
        finally:
            with contextlib.suppress(Exception):
                conn.close()
        return LexiconStats(
            lex_id=LEX_ID,
            path=str(self.output_path),
            entry_count=entry_count,
            size_mb=size_mb,
        )

    def cleanup(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
