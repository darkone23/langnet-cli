from __future__ import annotations

import hashlib
import html
import logging
import os
import re
import time
import unicodedata
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, NamedTuple

import duckdb
import pyarrow as pa
import requests
from bs4 import BeautifulSoup
from returns.result import Failure, Success

from langnet.execution.handlers.diogenes import _parse_diogenes_html
from langnet.normalizer.utils import normalize_greekish_token, strip_accents

from .base import BuildErrorStats, BuildResult, BuildStatus, LexiconStats
from .paths import default_diogenes_path, project_root

logger = logging.getLogger(__name__)

DiogenesLanguage = Literal["lat", "grc"]
DiogenesBuildMode = Literal["auto", "direct", "crawl"]
DiogenesFetch = Callable[[str, Mapping[str, str]], tuple[int, str, str]]

DEFAULT_ENDPOINT = "http://localhost:8888/Perseus.cgi"
DEFAULT_SEEDS = {"lat": "amo", "grc": "apo"}
HTTP_BAD_REQUEST = 400

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    language VARCHAR NOT NULL,
    dictionary VARCHAR NOT NULL,
    entry_offset BIGINT PRIMARY KEY,
    headword VARCHAR NOT NULL,
    headword_norm VARCHAR NOT NULL,
    lookup VARCHAR NOT NULL,
    sort_key VARCHAR NOT NULL,
    plain_text TEXT,
    html TEXT,
    entry_hash VARCHAR,
    previous_offset BIGINT,
    next_offset BIGINT,
    fetched_url VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS entries_language_sort_idx ON entries(language, sort_key, entry_offset);
CREATE INDEX IF NOT EXISTS entries_headword_norm_idx ON entries(headword_norm);
"""


@dataclass(frozen=True)
class DiogenesBuildConfig:
    language: DiogenesLanguage
    mode: DiogenesBuildMode = "auto"
    endpoint: str = DEFAULT_ENDPOINT
    source_path: Path | None = None
    output_path: Path | None = None
    seed_word: str | None = None
    max_entries: int | None = 1000
    batch_size: int = 5000
    request_timeout_s: float = 10.0
    polite_delay_s: float = 0.0
    wipe_existing: bool = True
    force_rebuild: bool = False


@dataclass(frozen=True)
class DiogenesIndexEntry:
    language: DiogenesLanguage
    dictionary: str
    offset: int
    headword: str
    headword_norm: str
    lookup: str
    sort_key: str
    plain_text: str
    html: str
    entry_hash: str
    previous_offset: int | None
    next_offset: int | None
    fetched_url: str


class DiogenesNavigation(NamedTuple):
    current_offset: int | None
    previous_offset: int | None
    next_offset: int | None


class DiogenesFetchedPage(NamedTuple):
    status_code: int
    text: str
    url: str


class DiogenesBuilder:
    """
    Crawl Diogenes dictionary entries by following previous/next byte offsets.
    """

    def __init__(self, config: DiogenesBuildConfig, fetch: DiogenesFetch | None = None) -> None:
        self.language = _normalize_language(config.language)
        self.config = replace(config, language=self.language)
        self.output_path = config.output_path or default_diogenes_path(self.language)
        self.source_path = config.source_path or default_diogenes_source_path(self.language)
        self.seed_word = config.seed_word or DEFAULT_SEEDS[self.language]
        self._fetch = fetch or self._requests_fetch
        self._conn: duckdb.DuckDBPyConnection | None = None

    def build(self) -> BuildResult[LexiconStats | BuildErrorStats]:
        try:
            if self.output_path.exists():
                if self.config.wipe_existing:
                    logger.info("Deleting existing Diogenes index at %s", self.output_path)
                    self.output_path.unlink()
                elif not self.config.force_rebuild:
                    return BuildResult(
                        status=BuildStatus.SKIPPED,
                        output_path=self.output_path,
                        stats=Success(self.get_stats()),
                        message="Index already exists; use --wipe or --force to rebuild",
                    )

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.output_path))
            self._conn.execute(SCHEMA_SQL)
            processed = self._build_entries()
            self._conn.execute("CHECKPOINT")
            stats = self._get_open_stats(processed)
            mode = self._resolved_mode()
            return BuildResult(
                status=BuildStatus.SUCCESS,
                output_path=self.output_path,
                stats=Success(stats),
                message=f"Built {processed} Diogenes {self.language} entries via {mode}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Diogenes index build failed")
            return BuildResult(
                status=BuildStatus.FAILED,
                output_path=self.output_path,
                stats=Failure(BuildErrorStats(error=f"{type(exc).__name__}: {exc}")),
                message=str(exc),
            )
        finally:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def get_stats(self) -> LexiconStats:
        entry_count = None
        headword_count = None
        size_mb = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 2)
            try:
                with duckdb.connect(str(self.output_path), read_only=True) as conn:
                    entry_count, headword_count = _read_counts(conn)
            except Exception:  # noqa: BLE001
                entry_count = None
                headword_count = None
        return LexiconStats(
            lex_id=f"DIOGENES_{self.language.upper()}",
            path=str(self.output_path),
            entry_count=entry_count,
            headword_count=headword_count,
            size_mb=size_mb,
        )

    def _get_open_stats(self, processed: int) -> LexiconStats:
        if self._conn is None:
            return replace(self.get_stats(), entry_count=processed)
        entry_count, headword_count = _read_counts(self._conn)
        size_mb = None
        if self.output_path.exists():
            size_mb = round(self.output_path.stat().st_size / (1024 * 1024), 2)
        return LexiconStats(
            lex_id=f"DIOGENES_{self.language.upper()}",
            path=str(self.output_path),
            entry_count=entry_count,
            headword_count=headword_count,
            size_mb=size_mb,
        )

    def _resolved_mode(self) -> DiogenesBuildMode:
        if self.config.mode != "auto":
            return self.config.mode
        return "direct" if self.source_path.exists() else "crawl"

    def _build_entries(self) -> int:
        mode = self._resolved_mode()
        if mode == "direct":
            if not self.source_path.exists():
                raise FileNotFoundError(f"Diogenes source file not found: {self.source_path}")
            return self._import_source_file()
        return self._crawl()

    def _import_source_file(self) -> int:
        if self._conn is None:
            raise RuntimeError("DiogenesBuilder connection is not open")
        processed = 0
        pending: list[DiogenesIndexEntry] = []
        previous_entry: DiogenesIndexEntry | None = None
        with self.source_path.open("rb") as source:
            while not _limit_reached(processed, self.config.max_entries):
                offset = source.tell()
                line = source.readline()
                if not line:
                    break
                entry = extract_diogenes_xml_index_entry(
                    line.decode("utf-8", errors="ignore"),
                    language=self.language,
                    offset=offset,
                    source_path=self.source_path,
                )
                if entry is None:
                    continue
                if previous_entry is not None:
                    pending.append(replace(previous_entry, next_offset=entry.offset))
                    processed += 1
                    if len(pending) >= self.config.batch_size:
                        self._insert_entries(pending)
                        pending.clear()
                previous_offset = previous_entry.offset if previous_entry else None
                previous_entry = replace(entry, previous_offset=previous_offset)
        if previous_entry is not None and not _limit_reached(processed, self.config.max_entries):
            pending.append(previous_entry)
            processed += 1
        if pending:
            self._insert_entries(pending)
        return processed

    def _crawl(self) -> int:
        if self._conn is None:
            raise RuntimeError("DiogenesBuilder connection is not open")
        seed = self._fetch_page("parse", self.seed_word)
        seed_entry = extract_diogenes_index_entry(
            seed.text,
            language=self.language,
            fetched_url=seed.url,
        )
        if seed.status_code >= HTTP_BAD_REQUEST or seed_entry is None:
            raise RuntimeError(
                f"Could not seed Diogenes crawl from {self.seed_word!r} (status {seed.status_code})"
            )

        queue: deque[tuple[str, int]] = deque()
        seen_offsets: set[int] = set()
        requested_edges: set[tuple[str, int]] = set()
        processed = 0

        processed += self._insert_entries([seed_entry])
        seen_offsets.add(seed_entry.offset)
        _enqueue_edge(queue, requested_edges, "prev_entry", seed_entry.offset)
        _enqueue_edge(queue, requested_edges, "next_entry", seed_entry.offset)

        while queue and not _limit_reached(processed, self.config.max_entries):
            action, offset = queue.popleft()
            page = self._fetch_page(action, str(offset))
            entry = extract_diogenes_index_entry(
                page.text,
                language=self.language,
                fetched_url=page.url,
            )
            if page.status_code >= HTTP_BAD_REQUEST or entry is None:
                logger.warning(
                    "Skipping Diogenes %s/%s status=%s", action, offset, page.status_code
                )
                continue
            if entry.offset in seen_offsets:
                continue
            processed += self._insert_entries([entry])
            seen_offsets.add(entry.offset)
            _enqueue_edge(queue, requested_edges, action, entry.offset)
            if self.config.polite_delay_s > 0:
                time.sleep(self.config.polite_delay_s)
        return processed

    def _insert_entries(self, entries: list[DiogenesIndexEntry]) -> int:
        if self._conn is None or not entries:
            return 0
        table = pa.table(
            {
                "language": [entry.language for entry in entries],
                "dictionary": [entry.dictionary for entry in entries],
                "entry_offset": [entry.offset for entry in entries],
                "headword": [entry.headword for entry in entries],
                "headword_norm": [entry.headword_norm for entry in entries],
                "lookup": [entry.lookup for entry in entries],
                "sort_key": [entry.sort_key for entry in entries],
                "plain_text": [entry.plain_text for entry in entries],
                "html": [entry.html for entry in entries],
                "entry_hash": [entry.entry_hash for entry in entries],
                "previous_offset": [entry.previous_offset for entry in entries],
                "next_offset": [entry.next_offset for entry in entries],
                "fetched_url": [entry.fetched_url for entry in entries],
            }
        )
        self._conn.register("diogenes_entry_batch", table)
        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO entries (
                    language, dictionary, entry_offset, headword, headword_norm, lookup, sort_key,
                    plain_text, html, entry_hash, previous_offset, next_offset, fetched_url
                )
                SELECT
                    language, dictionary, entry_offset, headword, headword_norm, lookup, sort_key,
                    plain_text, html, entry_hash, previous_offset, next_offset, fetched_url
                FROM diogenes_entry_batch
                """
            )
        finally:
            self._conn.unregister("diogenes_entry_batch")
        return len(entries)

    def _fetch_page(self, action: str, query: str) -> DiogenesFetchedPage:
        status_code, text, url = self._fetch(
            self.config.endpoint,
            {"do": action, "lang": _diogenes_language(self.language), "q": query},
        )
        return DiogenesFetchedPage(status_code=status_code, text=text, url=url)

    def _requests_fetch(self, endpoint: str, params: Mapping[str, str]) -> tuple[int, str, str]:
        response = requests.get(
            endpoint, params=dict(params), timeout=self.config.request_timeout_s
        )
        return (response.status_code, response.text if response.ok else "", response.url)


def extract_diogenes_navigation(html: str) -> DiogenesNavigation:
    """
    Extract Diogenes dictionary byte offsets from prevEntry*/nextEntry* onclicks.
    """
    previous_offset: int | None = None
    next_offset: int | None = None
    current_offset: int | None = None
    soup = BeautifulSoup(html or "", "html.parser")
    for anchor in soup.find_all("a"):
        onclick = str(anchor.attrs.get("onclick", ""))
        match = re.search(r"\b(prevEntry|nextEntry|getEntry)(?:grk|lat|eng)?\((\d+)\)", onclick)
        if not match:
            continue
        offset = int(match.group(2))
        current_offset = offset
        if match.group(1) == "prevEntry":
            previous_offset = offset
        elif match.group(1) == "nextEntry":
            next_offset = offset
    return DiogenesNavigation(
        current_offset=current_offset,
        previous_offset=previous_offset,
        next_offset=next_offset,
    )


def extract_diogenes_index_entry(
    html: str,
    *,
    language: DiogenesLanguage,
    fetched_url: str = "",
) -> DiogenesIndexEntry | None:
    navigation = extract_diogenes_navigation(html)
    if navigation.current_offset is None:
        return None
    headword = _extract_headword(html)
    if not headword:
        return None
    plain_text = _entry_plain_text(html)
    headword_norm = _normalize_headword(headword, language)
    lookup = _lookup_value(headword, language)
    dictionary = "lsj" if language == "grc" else "lewis_short"
    return DiogenesIndexEntry(
        language=language,
        dictionary=dictionary,
        offset=navigation.current_offset,
        headword=headword,
        headword_norm=headword_norm,
        lookup=lookup,
        sort_key=headword_norm,
        plain_text=plain_text,
        html=html,
        entry_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
        previous_offset=navigation.previous_offset,
        next_offset=navigation.next_offset,
        fetched_url=fetched_url,
    )


def extract_diogenes_xml_index_entry(
    xml: str,
    *,
    language: DiogenesLanguage,
    offset: int,
    source_path: Path,
) -> DiogenesIndexEntry | None:
    headword = _extract_xml_headword(xml, language)
    if not headword:
        return None
    headword_norm = _normalize_headword(headword, language)
    lookup = _lookup_value(headword, language)
    dictionary = "lsj" if language == "grc" else "lewis_short"
    return DiogenesIndexEntry(
        language=language,
        dictionary=dictionary,
        offset=offset,
        headword=headword,
        headword_norm=headword_norm,
        lookup=lookup,
        sort_key=headword_norm,
        plain_text="",
        html="",
        entry_hash=hashlib.sha256(xml.encode("utf-8")).hexdigest(),
        previous_offset=None,
        next_offset=None,
        fetched_url=str(source_path),
    )


def default_diogenes_source_path(language: DiogenesLanguage) -> Path:
    filename = "grc.lsj.xml" if language == "grc" else "lat.ls.perseus-eng1.xml"
    env_dir = os.getenv("DIOGENES_PERSEUS_DIR")
    sibling_path = project_root().parent / "diogenes" / "dependencies" / "data" / filename
    candidates: list[Path] = [
        sibling_path,
        Path.home() / "langnet-tools" / "diogenes" / "dependencies" / "data" / filename,
    ]
    if env_dir:
        candidates.insert(0, Path(env_dir).expanduser() / filename)
    return next((path for path in candidates if path.exists()), sibling_path)


def _read_counts(conn: duckdb.DuckDBPyConnection) -> tuple[int, int]:
    row = conn.execute("SELECT COUNT(*), COUNT(DISTINCT headword_norm) FROM entries").fetchone()
    if row is None:
        return (0, 0)
    return (int(row[0]), int(row[1]))


def _enqueue_edge(
    queue: deque[tuple[str, int]],
    requested_edges: set[tuple[str, int]],
    action: str,
    offset: int,
) -> None:
    edge = (action, offset)
    if edge in requested_edges:
        return
    requested_edges.add(edge)
    queue.append(edge)


def _limit_reached(processed: int, max_entries: int | None) -> bool:
    return max_entries is not None and max_entries > 0 and processed >= max_entries


def _normalize_language(language: str) -> DiogenesLanguage:
    if language.lower() in {"grc", "grk", "greek"}:
        return "grc"
    if language.lower() in {"lat", "la", "latin"}:
        return "lat"
    raise ValueError("Diogenes index language must be lat or grc.")


def _diogenes_language(language: DiogenesLanguage) -> str:
    return "grk" if language == "grc" else "lat"


def _extract_headword(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    h2 = soup.find("h2")
    if h2 is not None:
        span = h2.find("span")
        text = span.get_text(" ", strip=True) if span is not None else h2.get_text(" ", strip=True)
        headword = _clean_headword(text)
        if headword:
            return headword
    parsed = _parse_diogenes_html(html)
    for chunk in parsed.get("chunks", []):
        if not isinstance(chunk, Mapping):
            continue
        definitions = chunk.get("definitions")
        if not isinstance(definitions, Mapping):
            continue
        term = definitions.get("term")
        if isinstance(term, str):
            headword = _clean_headword(term)
            if headword:
                return headword
    return ""


def _extract_xml_headword(xml: str, language: DiogenesLanguage) -> str:
    head_match = re.search(r"<head\b([^>]*)>(.*?)</head>", xml or "", flags=re.DOTALL)
    if head_match:
        attrs = head_match.group(1)
        text = _strip_xml_tags(head_match.group(2))
        orth_match = re.search(r'\borth_orig="([^"]*)"', attrs)
        orth_text = html.unescape(orth_match.group(1)) if orth_match else ""
        if language == "grc" and text:
            return _clean_headword(text)
        return _clean_headword(orth_text or text)
    root_match = re.search(
        r"<(?:entryFree|entryfree|div1|div2)\b[^>]*(?:key|id)=\"([^\"]*)\"",
        xml or "",
    )
    if root_match:
        return _clean_headword(html.unescape(root_match.group(1)))
    return ""


def _clean_headword(text: str) -> str:
    return re.split(r"[,;:]", text.strip(), maxsplit=1)[0].strip()


def _entry_plain_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_xml_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text).strip())


def _normalize_headword(headword: str, language: DiogenesLanguage) -> str:
    if language == "grc":
        ascii_key = _greek_to_betacode_ascii(headword)
        if ascii_key:
            return ascii_key
        greekish = normalize_greekish_token(headword)
        if greekish:
            normalized = greekish.lower().replace("w", "o")
            return re.sub(r"[^a-z0-9]+", "", normalized)
        lowered = strip_accents(headword).lower().replace("ς", "σ")
        return re.sub(r"\s+", " ", lowered).strip()
    normalized = strip_accents(headword).lower()
    normalized = normalized.replace("æ", "ae").replace("œ", "oe")
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _lookup_value(headword: str, language: DiogenesLanguage) -> str:
    if language == "grc":
        romanized = _greek_to_betacode_ascii(headword)
        return romanized or headword
    return _normalize_headword(headword, language) or headword


def _greek_to_betacode_ascii(headword: str) -> str:
    try:
        import betacode  # type: ignore[import-untyped]  # noqa: PLC0415

        converter = getattr(betacode, "conv", None)
        if converter and hasattr(converter, "uni_to_beta"):
            beta = converter.uni_to_beta(headword)
        else:
            beta = headword
    except Exception:  # noqa: BLE001
        beta = headword
    normalized = unicodedata.normalize("NFKD", beta)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().replace("w", "o")
    return re.sub(r"[^a-z]+", "", ascii_text)
