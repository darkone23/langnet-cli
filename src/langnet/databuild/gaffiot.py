from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, replace
from itertools import islice
from pathlib import Path
from typing import TypedDict

import duckdb
from lxml import etree as ET  # type: ignore[import-untyped]
from pylatexenc.latex2text import LatexNodes2Text
from returns.result import Failure, Success

from langnet.normalizer.utils import strip_accents

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_gaffiot_path

logger = logging.getLogger(__name__)

LEX_ID = "GAFFIOT_FR_LAT"


class _SeenHashRecord(TypedDict):
    canonical_id: str
    heads: set[str]


# Use the JSON export as default (cleaner and more reliable than TEI or EBWING).
DEFAULT_SOURCE = Path.home() / "digital-gaffiot-json" / "gaffiot.json"
# Fallback to TEI XML if JSON not available
DEFAULT_SOURCE_TEI = Path.home() / "digital-gaffiot-json" / "gaffiot-unicode.xml"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries_fr (
    entry_id VARCHAR PRIMARY KEY,
    headword_raw VARCHAR,
    headword_norm VARCHAR,
    variant_num INTEGER,
    tei_xml TEXT NOT NULL,
    plain_text TEXT,
    entry_hash VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass
class GaffiotBuildConfig:
    """
    Configuration for GaffiotBuilder.
    """

    source_path: Path | None = None
    output_path: Path | None = None
    limit: int | None = None
    batch_size: int = 500
    wipe_existing: bool = True
    force_rebuild: bool = False


def _strip_latex(text: str) -> str:
    """
    Strip LaTeX markup from text, preserving content and structure.
    Handles Gaffiot's custom commands like \\gen{}, \\aut{}, \\lat{}, etc.
    Converts \\par to ¶ (pilcrow) for paragraph marking.
    """
    if not text:
        return ""

    # Pre-process: convert \par to pilcrow marker (used in translation scripts)
    text = text.replace("\\par", " ¶ ")

    # Create a converter that strips LaTeX commands
    converter = LatexNodes2Text()
    try:
        # Clean the text
        clean = converter.latex_to_text(text)
        # Normalize whitespace but preserve paragraph markers
        clean = re.sub(r"[ \t]+", " ", clean)
        # Clean up spacing around pilcrow
        clean = re.sub(r"\s*¶\s*", " ¶ ", clean)
        # Remove any duplicate pilcrows
        clean = re.sub(r"¶\s*¶+", "¶", clean)
        return clean.strip()
    except Exception as e:
        logger.warning(f"Failed to strip LaTeX from text, using fallback: {e}")
        # Fallback: simple regex-based stripping
        clean = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
        clean = re.sub(r"\\[a-zA-Z]+", "", text)
        clean = re.sub(r"\s+", " ", clean)
        clean = re.sub(r"\s*¶\s*", " ¶ ", clean)
        return clean.strip()


def _normalize_headword(raw: str) -> str:
    """
    Normalize headword to lowercase ASCII, strip leading numbering, and remove accents.
    """
    stripped = (raw or "").strip()
    if "," in stripped:
        stripped = stripped.split(",", 1)[0]
    # drop leading numeric marker like "1 a" -> "a"
    stripped = stripped.lstrip("0123456789. ").strip()
    # Expand common ligatures before accent stripping.
    ligature_expanded = (
        stripped.replace("æ", "ae").replace("Æ", "ae").replace("œ", "oe").replace("Œ", "oe")
    )
    lowered = ligature_expanded.lower()
    return strip_accents(lowered)


def _try_strip_with_separators(trimmed: str, trimmed_lower: str, base: str) -> str | None:
    """Try stripping base with various separators. Returns None if no match."""
    for sep in ("", " ", ",", ".", ";", ":", "-", " ,", " ."):
        candidate = base + sep
        if trimmed_lower.startswith(candidate):
            cut = len(candidate)
            return trimmed[cut:].lstrip()
    return None


def _strip_leading_headword(text: str, head_clean: str, head_raw: str) -> str:
    """
    Remove a single leading occurrence of the headword from the text.
    Uses simple prefix checks (raw and cleaned) to handle numbered variants.
    """
    if not head_clean and not head_raw:
        return text
    trimmed = text.lstrip()
    trimmed_lower = trimmed.lower()
    bases = []
    if head_raw:
        bases.append(head_raw.lower())
    if head_clean:
        bases.append(head_clean.lower())

    for base in bases:
        # Include variants that start with digits in the raw head.
        result = _try_strip_with_separators(trimmed, trimmed_lower, base)
        if result is not None:
            return result

        # If the base starts with digits, also try stripping just the numeric prefix.
        numeric_prefix = ""
        for ch in base:
            if ch.isdigit():
                numeric_prefix += ch
            else:
                break
        if numeric_prefix:
            base_no_num = base[len(numeric_prefix) :].lstrip(" .")
            result = _try_strip_with_separators(trimmed, trimmed_lower, base_no_num)
            if result is not None:
                return result
    return text


def _collect_text_with_breaks(
    elem: ET.Element, break_tags: set[str] | tuple[str, ...] = ("lb",)
) -> str:
    """
    Collect text content while translating specific break-like tags to newlines.
    """
    parts: list[str] = []

    for node in elem.iter():
        tag = node.tag if isinstance(node.tag, str) else None
        if node is not elem and tag in break_tags:
            parts.append("\n")
        if node.text:
            parts.append(node.text)
        if node is not elem and node.tail:
            parts.append(node.tail)

    text = "".join(parts)
    text = re.sub(r"[ \t]+", " ", text)  # normalize intra-line spacing
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)  # trim spaces around newlines
    return text.strip()


def _build_plain_text(elem: ET.Element, headword_clean: str) -> str:
    """
    Build plain_text from <def> content when present; fallback to full entry text.
    Strip one leading headword occurrence and leading punctuation remnants.
    """
    def_el = elem.find("def")
    source = def_el if def_el is not None else elem
    raw_text = _collect_text_with_breaks(source)

    stripped = _strip_leading_headword(raw_text, headword_clean, elem.findtext("orth") or "")
    stripped = stripped.lstrip(" ,;:.")  # remove leftover punctuation
    if not stripped:
        stripped = raw_text.strip()
    return stripped


def _iter_batches(iterable, size: int):
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


class GaffiotBuilder:
    """
    Build French→Latin Gaffiot index (TEI-ish) into DuckDB.
    """

    def __init__(self, config: GaffiotBuildConfig) -> None:
        # Auto-detect JSON vs XML source
        if config.source_path:
            self.source_path = config.source_path.expanduser()
        elif DEFAULT_SOURCE.exists():
            self.source_path = DEFAULT_SOURCE
        elif DEFAULT_SOURCE_TEI.exists():
            self.source_path = DEFAULT_SOURCE_TEI
        else:
            self.source_path = DEFAULT_SOURCE

        self.output_path = config.output_path or default_gaffiot_path()
        self.limit = config.limit
        self.batch_size = config.batch_size
        self.wipe_existing = config.wipe_existing
        self.force_rebuild = config.force_rebuild
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Gaffiot XML not found at {self.source_path}")

            if self.output_path.exists():
                if self.wipe_existing:
                    logger.info("Deleting existing Gaffiot index at %s", self.output_path)
                    self.output_path.unlink()
                elif not self.force_rebuild:
                    logger.info("Gaffiot index already exists; skipping rebuild")
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            logger.info(
                "Building Gaffiot index",
                extra={
                    "lex_id": LEX_ID,
                    "source": str(self.source_path),
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
                "Finished Gaffiot index",
                extra={
                    "lex_id": LEX_ID,
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
            logger.exception("Failed to build Gaffiot index: %s", exc)
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
        seen_hash_to_id: dict[str, _SeenHashRecord] = {}
        for idx, entry in enumerate(self._iter_entry_elements(), start=1):
            entry_id = f"gaffiot_{idx}"
            headword_raw = entry["headword_raw"]
            headword_norm = _normalize_headword(entry["headword_clean"])
            variant_num = entry.get("variant_num")
            entry_hash = entry["entry_hash"]

            record = seen_hash_to_id.get(entry_hash)
            if record is None:
                new_record: _SeenHashRecord = {
                    "canonical_id": entry_id,
                    "heads": {headword_raw},
                }
                seen_hash_to_id[entry_hash] = new_record
                entries_batch.append(
                    (
                        entry_id,
                        headword_raw,
                        headword_norm,
                        variant_num,
                        entry["tei_xml"],
                        entry["plain_text"],
                        entry_hash,
                        None,
                    )
                )
            else:
                # Duplicate body: keep the canonical entry, drop the duplicate.
                continue

            if self.limit is not None:
                remaining = self.limit - total
                if remaining <= 0:
                    break
                if len(entries_batch) >= remaining:
                    # Trim to remaining and flush immediately.
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
                    "Inserted Gaffiot batch: %s entries (total=%s, elapsed_ms=%s)",
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
                "Inserted final Gaffiot batch: %s entries (total=%s, elapsed_ms=%s)",
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
                INSERT INTO entries_fr VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                entries_batch,
            )

    def _iter_entry_elements(self):
        """
        Stream entries from JSON or XML source.
        """
        # Detect format by extension
        if self.source_path.suffix.lower() == ".json":
            yield from self._iter_json_entries()
        else:
            yield from self._iter_xml_entries()

    def _iter_json_entries(self):
        """
        Stream entries from gaffiot.json.
        """
        logger.info(f"Loading JSON entries from {self.source_path}")
        with open(self.source_path, encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            yield self._parse_json_entry(entry)

    def _iter_xml_entries(self):
        """
        Stream entryFree elements from TEI XML to keep memory bounded.
        """
        logger.info(f"Loading XML entries from {self.source_path}")
        context = ET.iterparse(self.source_path, events=("end",), huge_tree=True)
        for _, elem in context:
            if elem.tag != "entryFree":
                continue
            yield self._parse_entry(elem)
            elem.clear()

    def _parse_json_entry(self, entry: dict) -> dict:
        """
        Parse a JSON entry from gaffiot.json format.
        Entry structure: {id, latin_raw, latin, french}
        """
        headword_raw = entry.get("latin_raw", "").strip()
        headword_clean = entry.get("latin", "").strip()
        french_text = entry.get("french", "")

        # Extract variant number from headword
        variant_num = None
        if headword_raw:
            prefix_match = re.match(r"^\s*(\d+)", headword_raw)
            if prefix_match:
                try:
                    variant_num = int(prefix_match.group(1))
                except Exception:
                    variant_num = None
            # Strip leading numeric markers for clean headword
            headword_clean = re.sub(r"^\s*\d+[\s.]*", "", headword_raw).strip()

        # Strip LaTeX markup from French definition
        plain_text = _strip_latex(french_text)

        # Remove leading headword repetition if present
        plain_text = _strip_leading_headword(plain_text, headword_clean, headword_raw)
        plain_text = plain_text.lstrip(" ,;:.")

        # Use original entry as "TEI XML" for compatibility
        tei_xml = json.dumps(entry, ensure_ascii=False)

        digest = hashlib.sha1(plain_text.encode("utf-8")).hexdigest()
        return {
            "headword_raw": headword_raw,
            "headword_clean": headword_clean,
            "variant_num": variant_num,
            "plain_text": plain_text,
            "tei_xml": tei_xml,
            "entry_hash": digest,
        }

    def _parse_entry(self, elem: ET.Element) -> dict:
        """
        Parse a TEI XML entry element.
        """
        headword_raw = ""
        headword_clean = ""
        variant_num = None
        orths = [orth.text.strip() for orth in elem.findall("orth") if orth.text]
        if orths:
            headword_raw = orths[0].strip()
        if headword_raw:
            prefix_match = re.match(r"^\s*(\d+)", headword_raw)
            if prefix_match:
                try:
                    variant_num = int(prefix_match.group(1))
                except Exception:
                    variant_num = None
            # Strip leading numeric markers like "1 ab" -> "ab" for normalization/stripping use.
            headword_clean = re.sub(r"^\s*\d+[\s.]*", "", headword_raw).strip()
        else:
            headword_clean = headword_raw

        plain_text = _build_plain_text(elem, headword_clean)
        tei_xml = ET.tostring(elem, encoding="unicode").strip()
        digest = hashlib.sha1(plain_text.encode("utf-8")).hexdigest()
        return {
            "headword_raw": headword_raw,
            "headword_clean": headword_clean,
            "variant_num": variant_num,
            "plain_text": plain_text,
            "tei_xml": tei_xml,
            "entry_hash": digest,
        }

    def _clean_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        return " ".join(normalized.split())

    def get_stats(self) -> LexiconStats:
        size_mb = None
        entry_count = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 3)
        conn = duckdb.connect(str(self.output_path))
        try:
            result = conn.execute("SELECT COUNT(*) FROM entries_fr").fetchone()
            entry_count = result[0] if result else 0
        finally:
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
