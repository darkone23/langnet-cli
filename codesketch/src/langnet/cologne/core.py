import multiprocessing as mp
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import cast

import duckdb
import structlog
from indic_transliteration.detect import detect
from indic_transliteration.sanscript import DEVANAGARI, HK, IAST, SLP1, transliterate

from langnet.config import config
from langnet.types import JSONMapping

from .models import (
    CdslQueryResult,
    SanskritDictionaryEntry,
    SanskritTransliteration,
)
from .parser import parse_grammatical_info, parse_xml_entry

logger = structlog.get_logger(__name__)

ENTRY_ID_SUBID_SEPARATOR = "."
ENTRY_ID_MAX_PARTS = 2


def get_cdsl_db_dir() -> Path:
    return config.cdsl_db_dir


def get_cdsl_dict_dir() -> Path:
    return config.cdsl_dict_dir


class CdslSchema:
    _sql_cache: str | None = None

    @staticmethod
    def get_sql() -> str:
        if CdslSchema._sql_cache is None:
            sql_path = Path(__file__).parent / "sql" / "schema.sql"
            if sql_path.exists():
                CdslSchema._sql_cache = sql_path.read_text()
            else:
                raise FileNotFoundError(f"Schema SQL file not found: {sql_path}")
        return CdslSchema._sql_cache


def normalize_key(key: str) -> str:
    return key.lower().strip()


def _velthuis_to_slp1_direct(text: str) -> str:
    """Convert Velthuis to SLP1 using Heritage conventions.

    Heritage VH: z=ś, .s=ṣ, .m=ṃ, .h=ḥ, ~n=ñ, .t=ṭ, .d=ḍ, .n=ṇ
    """
    if not text:
        return text

    result = text

    # Fix library artifacts: "s should be z (Heritage's ś)
    result = result.replace('"s', "z")
    result = result.replace('"S', "z")

    # Process longest sequences first to avoid partial replacements
    # Long vowels
    result = result.replace("aa", "A")
    result = result.replace("ii", "I")
    result = result.replace("uu", "U")

    # Vocalic liquids (long forms first)
    result = result.replace(".rr", "RR")
    result = result.replace(".r", "R")
    result = result.replace(".ll", "LL")
    result = result.replace(".l", "L")

    # Anusvara/visarga
    result = result.replace(".m", "M")
    result = result.replace(".h", "H")

    # Sibilants: z=ś, .s=ṣ -> SLP1 z, S
    result = result.replace(".s", "S")

    # Other dotted consonants
    result = result.replace(".t", "w")  # ṭ
    result = result.replace(".d", "q")  # ḍ
    result = result.replace(".n", "R")  # ṇ (retroflex n)

    # Nasals
    result = result.replace("~n", "Y")  # ñ (palatal)
    result = result.replace('"n', "N")  # ṅ (velar)

    # Avagraha
    result = result.replace(".a", "'")

    return result


def _slp1_safe_lower(text: str) -> str:
    """
    Lowercase text while preserving SLP1 encoding.

    SLP1 uses uppercase letters for special sounds that should not be lowercased:
    A=ā, I=ī, U=ū, R=ṛ, M=ṃ, H=ḥ, S=ṣ (retroflex), z=ś (palatal), etc.

    Only lowercase if the text doesn't contain SLP1-specific characters.
    """
    # SLP1-specific characters that should remain uppercase
    slp1_specific = "AIURMHSz"
    if any(ch in text for ch in slp1_specific):
        return text
    return text.lower()


def _try_transliterate_from_scheme(text: str, scheme: str) -> str | None:
    """Try to transliterate text from a specific scheme to SLP1."""
    scheme_map = {
        "hk": HK,
        "iast": IAST,
        "devanagari": DEVANAGARI,
        "deva": DEVANAGARI,
    }
    src_scheme = scheme_map.get(scheme)
    if src_scheme:
        try:
            result = transliterate(text, src_scheme, SLP1)
            return _slp1_safe_lower(result)
        except Exception:
            return _slp1_safe_lower(text)
    return None


def _is_slp1_format(text: str) -> bool:
    """Check if text appears to already be in SLP1 format."""
    # SLP1 uses: A=ā, I=ī, U=ū, R=ṛ, M=ṃ, H=ḥ, z=ś, S=ṣ
    # But z and S could be other schemes, so we look for the capital letters
    return any(ch in text for ch in "AIURMH")


def _is_velthuis_format(text: str) -> bool:
    """Check if text appears to be in Velthuis format."""
    # Velthuis uses: z=ś, aa=ā, ii=ī, uu=ū, .m=ṃ, .h=ḥ, ~n=ñ, etc.
    return any(ch in text for ch in ".~") or any(
        substr in text for substr in ["aa", "ii", "uu", "z"]
    )


def _try_auto_detect_and_convert(text: str) -> str:
    """Try to auto-detect encoding and convert to SLP1."""
    try:
        src = detect(text)
        if src and src != "slp1":
            result = transliterate(text, src, SLP1)
            return _slp1_safe_lower(result)
    except Exception:
        pass
    return _slp1_safe_lower(text)


def to_slp1(text: str, source_encoding: str | None = None) -> str:
    """
    Convert text to SLP1 encoding.

    Args:
        text: The text to convert
        source_encoding: Optional source encoding (e.g., 'velthuis', 'hk', 'iast', 'devanagari').
                        If provided, uses explicit conversion instead of auto-detection.
                        Use this when you know the encoding (e.g., Heritage returns Velthuis).

    Returns:
        Text in SLP1 encoding (lowercase)
    """
    if not text or _is_slp1_format(text):
        return text

    # If source encoding is explicitly specified, use it
    if source_encoding:
        source_encoding_lower = source_encoding.lower()

        # Use our custom Velthuis converter to avoid library bugs
        if source_encoding_lower in ("velthuis", "vh"):
            return _velthuis_to_slp1_direct(text)

        result = _try_transliterate_from_scheme(text, source_encoding_lower)
        if result is not None:
            return result

    # Check if it's Velthuis (Heritage Platform format)
    if _is_velthuis_format(text):
        return _velthuis_to_slp1_direct(text)

    # Fall back to auto-detection for other schemes
    return _try_auto_detect_and_convert(text)


def parse_batch(args) -> tuple[list, list]:
    sqlite_path, dict_id, batch = args
    entries_data = []
    headwords_data = []

    for key, lnum_str, xml_data in batch:
        entry = parse_xml_entry(xml_data)
        if entry:
            key_norm = normalize_key(key)
            entries_data.append(
                (
                    dict_id,
                    key,
                    key_norm,
                    entry.key2,
                    entry.key2_normalized,
                    str(lnum_str),
                    entry.data,
                    entry.body,
                    entry.page_ref,
                )
            )

            headwords_data.append((dict_id, key, key_norm, str(lnum_str), True))

            if entry.key2:
                hw_norm2 = entry.key2_normalized or normalize_key(entry.key2)
                headwords_data.append((dict_id, entry.key2, hw_norm2, str(lnum_str), False))

    return entries_data, headwords_data


class CdslIndexBuildConfig:
    """Configuration for CDSL index building."""

    def __init__(  # noqa: PLR0913
        self,
        dict_dir: Path,
        output_db: Path,
        dict_id: str,
        limit: int | None = None,
        batch_size: int | None = None,
        num_workers: int | None = None,
    ):
        self.dict_dir = dict_dir
        self.output_db = output_db
        self.dict_id = dict_id
        self.limit = limit
        self.batch_size = batch_size
        self.num_workers = num_workers


class CdslIndexBuilder:
    @staticmethod
    def build(  # noqa: PLR0913
        dict_dir: Path,
        output_db: Path,
        dict_id: str,
        limit: int | None = None,
        batch_size: int | None = None,
        num_workers: int | None = None,
    ) -> int:
        config = CdslIndexBuildConfig(
            dict_dir=dict_dir,
            output_db=output_db,
            dict_id=dict_id,
            limit=limit,
            batch_size=batch_size,
            num_workers=num_workers,
        )
        return CdslIndexBuilder._build_with_config(config)

    @staticmethod
    def _build_with_config(config: CdslIndexBuildConfig) -> int:  # noqa: PLR0915
        """Build index with configuration."""
        sqlite_path = config.dict_dir / "web" / "sqlite" / f"{config.dict_id.lower()}.sqlite"
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        config.output_db.parent.mkdir(parents=True, exist_ok=True)

        if config.output_db.exists():
            config.output_db.unlink()

        conn = duckdb.connect(str(config.output_db))

        try:
            for sql_stmt in CdslSchema.get_sql().split(";"):
                stmt = sql_stmt.strip()
                if stmt:
                    conn.execute(stmt)

            logger.info("indexing_start", dict_id=config.dict_id, limit=config.limit)

            sqlite_conn = sqlite3.connect(str(sqlite_path))
            try:
                cursor = sqlite_conn.execute(f"SELECT key, lnum, data FROM {config.dict_id}")
                all_rows = list(cursor)
            finally:
                sqlite_conn.close()

            if config.limit:
                all_rows = all_rows[: config.limit]

            logger.info("rows_loaded", dict_id=config.dict_id, total=len(all_rows))

            if config.batch_size:
                actual_batch_size = config.batch_size
            else:
                actual_batch_size = max(
                    100, len(all_rows) // (config.num_workers or mp.cpu_count())
                )

            batches = [
                all_rows[i : i + actual_batch_size]
                for i in range(0, len(all_rows), actual_batch_size)
            ]

            num_workers = config.num_workers or mp.cpu_count()
            logger.info(
                "processing_batches",
                dict_id=config.dict_id,
                batches=len(batches),
                workers=num_workers,
                batch_size=actual_batch_size,
            )

            all_entries = []
            all_headwords = []

            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {
                    executor.submit(parse_batch, (sqlite_path, config.dict_id, batch)): idx
                    for idx, batch in enumerate(batches)
                }
                total_batches = len(batches)
                batch_start_time = time.perf_counter()
                for completed, future in enumerate(as_completed(futures), start=1):
                    batch_idx = futures[future]
                    batch_num = batch_idx + 1
                    entries, headwords = future.result()
                    all_entries.extend(entries)
                    all_headwords.extend(headwords)
                    elapsed = time.perf_counter() - batch_start_time
                    logger.info(
                        "batch_progress",
                        dict_id=config.dict_id,
                        batch=batch_num,
                        total=total_batches,
                        entries=len(entries),
                        headwords=len(headwords),
                        progress=f"{completed}/{total_batches}",
                        pct_complete=round(completed / total_batches * 100, 1),
                        elapsed_seconds=round(elapsed, 2),
                    )
                logger.info(
                    "all_batches_complete",
                    dict_id=config.dict_id,
                    total_batches=total_batches,
                    total_entries=len(all_entries),
                    total_headwords=len(all_headwords),
                    elapsed_seconds=round(time.perf_counter() - batch_start_time, 2),
                )

            logger.info(
                "indexing_bulk_insert",
                dict_id=config.dict_id,
                entries=len(all_entries),
                headwords=len(all_headwords),
            )

            if all_entries:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO entries (
                        dict_id, key, key_normalized, key2, key2_normalized,
                        lnum, data, body, page_ref
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    all_entries,
                )

            if all_headwords:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO headwords (dict_id, key, key_normalized, lnum, is_primary)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    all_headwords,
                )

            logger.info(
                "indexing_complete",
                dict_id=config.dict_id,
                entries=len(all_entries),
                headwords=len(all_headwords),
            )
            return len(all_entries)
        finally:
            conn.close()

    @staticmethod
    def build_all(
        dict_root: Path,
        output_dir: Path,
        limit: int | None = None,
        skip_english: bool = True,
        num_workers: int | None = None,
    ) -> dict[str, int]:
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {}
        skip_dicts = {"MWE", "AE"} if skip_english else set()

        for subdir in sorted(dict_root.iterdir()):
            if not subdir.is_dir():
                continue
            dict_id = subdir.name.upper()
            if dict_id in skip_dicts:
                logger.info("skipping_english_dict", dict_id=dict_id)
                continue
            output_db = output_dir / f"{dict_id.lower()}.db"
            try:
                count = CdslIndexBuilder.build(
                    subdir, output_db, dict_id, limit=limit, num_workers=num_workers
                )
                results[dict_id] = count
            except Exception as e:
                logger.error("build_failed", dict_id=dict_id, error=str(e))
                results[dict_id] = -1
        return results


class CdslIndex:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._conn: duckdb.DuckDBPyConnection | None = None

    def __enter__(self):
        # Use read-only by default for safety and concurrency
        self._conn = duckdb.connect(str(self.db_path), read_only=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_connection(self, read_only: bool = True):
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path), read_only=read_only)

    def lookup(self, dict_id: str, key: str) -> list[CdslQueryResult]:
        self._ensure_connection(read_only=True)
        normalized = to_slp1(key).lower()

        rows = (
            cast(duckdb.DuckDBPyConnection, self._conn)
            .execute(
                """
            SELECT key, lnum, data, body, page_ref
            FROM entries
            WHERE dict_id = ? AND key_normalized = ?
            ORDER BY lnum
            """,
                [dict_id.upper(), normalized],
            )
            .fetchall()
        )

        results = []
        for row in rows:
            results.append(
                CdslQueryResult(
                    dict_id=dict_id.upper(),
                    key=row[0],
                    lnum=str(row[1]),
                    data=row[2],
                    body=row[3],
                    page_ref=row[4],
                )
            )
        return results

    def prefix_search(self, dict_id: str, prefix: str, limit: int = 20) -> list[tuple[str, str]]:
        self._ensure_connection()
        normalized_prefix = to_slp1(prefix).lower()

        rows = (
            cast(duckdb.DuckDBPyConnection, self._conn)
            .execute(
                """
            SELECT key, lnum
            FROM headwords
            WHERE dict_id = ? AND key_normalized LIKE ? || '%'
            ORDER BY lnum
            LIMIT ?
            """,
                [dict_id.upper(), normalized_prefix, limit],
            )
            .fetchall()
        )

        return [(row[0], str(row[1])) for row in rows]

    def get_info(self, dict_id: str) -> dict:
        self._ensure_connection()

        count_result = (
            cast(duckdb.DuckDBPyConnection, self._conn)
            .execute(
                "SELECT COUNT(*) FROM entries WHERE dict_id = ?",
                [dict_id.upper()],
            )
            .fetchone()
        )
        count = count_result[0] if count_result else 0

        hw_result = (
            cast(duckdb.DuckDBPyConnection, self._conn)
            .execute(
                "SELECT COUNT(*) FROM headwords WHERE dict_id = ?",
                [dict_id.upper()],
            )
            .fetchone()
        )
        hw_count = hw_result[0] if hw_result else 0

        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "dict_id": dict_id.upper(),
            "entry_count": count,
            "headword_count": hw_count,
            "db_size_bytes": db_size,
            "db_path": str(self.db_path),
        }

    def list_dicts(self) -> list[str]:
        if not self.db_path.exists():
            return []
        self._ensure_connection()
        rows = (
            cast(duckdb.DuckDBPyConnection, self._conn)
            .execute("SELECT DISTINCT dict_id FROM entries ORDER BY dict_id")
            .fetchall()
        )
        return [row[0] for row in rows]


def build_dict(
    dict_dir: Path,
    output_db: Path,
    dict_id: str,
    limit: int | None = None,
    num_workers: int | None = None,
) -> int:
    return CdslIndexBuilder.build(
        dict_dir, output_db, dict_id, limit=limit, num_workers=num_workers
    )


def batch_build(
    dict_root: Path,
    output_dir: Path,
    limit: int | None = None,
    skip_english: bool = True,
    num_workers: int | None = None,
) -> dict[str, int]:
    return CdslIndexBuilder.build_all(dict_root, output_dir, limit, skip_english, num_workers)


def get_default_db_dir() -> Path:
    return get_cdsl_db_dir()


class SanskritCologneLexicon:
    _singleton_instance: "SanskritCologneLexicon | None" = None
    _initialized: bool = False

    def __new__(cls):
        if cls._singleton_instance is None:
            cls._singleton_instance = super().__new__(cls)
        return cls._singleton_instance

    def __init__(self):
        if not SanskritCologneLexicon._initialized:
            self._db_dir = get_default_db_dir()
            self._connections: dict[str, duckdb.DuckDBPyConnection] = {}
            SanskritCologneLexicon._initialized = True

    def _get_conn(self, dict_id: str) -> duckdb.DuckDBPyConnection:
        dict_id_upper = dict_id.upper()
        if dict_id_upper not in self._connections:
            db_path = self._db_dir / f"{dict_id.lower()}.db"
            if not db_path.exists():
                raise FileNotFoundError(f"Dictionary not indexed: {dict_id}")
            self._connections[dict_id_upper] = duckdb.connect(str(db_path), read_only=True)
        return self._connections[dict_id_upper]

    def _lookup_dict(self, dict_id: str, slp1_key: str) -> list[dict]:
        dict_id_upper = dict_id.upper()
        try:
            conn = self._get_conn(dict_id_upper)
        except FileNotFoundError:
            return []

        rows = conn.execute(
            """
            SELECT key, lnum, data, body, page_ref
            FROM entries
            WHERE dict_id = ? AND key_normalized = ?
            ORDER BY lnum
            """,
            [dict_id_upper, slp1_key],
        ).fetchall()

        return [
            {
                "dict_id": dict_id_upper,
                "key": row[0],
                "lnum": str(row[1]),
                "data": row[2],
                "body": row[3],
                "page_ref": row[4],
            }
            for row in rows
        ]

    def lookup_ascii(self, data: str) -> dict:
        slp1_key = to_slp1(data).lower()

        mw_entries = self._lookup_dict_formatted("MW", slp1_key, data)
        ap90_entries = self._lookup_dict_formatted("AP90", slp1_key, data)

        all_entries = mw_entries + ap90_entries
        root = None
        for entry in all_entries:
            if entry.etymology and entry.etymology.get("type") == "verb_root":
                root = {
                    "type": "verb_root",
                    "root": entry.etymology.get("root"),
                }
                if entry.etymology.get("meaning"):
                    root["meaning"] = entry.etymology.get("meaning")
                break

        # Convert to SLP1 for consistent internal representation
        slp1_term = to_slp1(data)

        # The indic_transliteration library has z and S swapped in SLP1.
        # Standard: z=ś (palatal), S=ṣ (retroflex)
        # Library:   z=ṣ (retroflex), S=ś (palatal)
        # We need to swap them for correct display conversion.
        def _swap_slp1_zS(text: str) -> str:
            """Swap z and S to work around library's swapped mapping."""
            # Use temporary placeholder to avoid double-swapping
            return text.replace("z", "\x00").replace("S", "z").replace("\x00", "S")

        slp1_for_display = _swap_slp1_zS(slp1_term)

        try:
            deva_term = transliterate(slp1_for_display, SLP1, DEVANAGARI)
        except Exception:
            deva_term = data

        # Generate proper IAST and HK representations from SLP1
        try:
            iast_term = transliterate(slp1_for_display, SLP1, IAST)
        except Exception:
            iast_term = data

        try:
            hk_term = transliterate(slp1_for_display, SLP1, HK)
        except Exception:
            hk_term = data

        transliteration = SanskritTransliteration(
            input=data,
            iast=iast_term,
            hk=hk_term,
            devanagari=deva_term,
        )

        result: dict = {
            "transliteration": {
                "input": transliteration.input,
                "iast": transliteration.iast,
                "hk": transliteration.hk,
                "devanagari": transliteration.devanagari,
            },
            "dictionaries": {
                "mw": [self._serialize_entry(e) for e in mw_entries],
                "ap90": [self._serialize_entry(e) for e in ap90_entries],
            },
        }
        if root:
            result["root"] = root

        return result

    def _serialize_entry(self, entry: SanskritDictionaryEntry) -> JSONMapping:
        result: JSONMapping = {
            "id": entry.id,
            "meaning": entry.meaning,
        }

        if entry.subid is not None:
            result["subid"] = entry.subid
        if entry.pos is not None:
            result["pos"] = entry.pos
        if entry.gender is not None:
            result["gender"] = entry.gender
        if entry.sanskrit_form is not None:
            result["sanskrit_form"] = entry.sanskrit_form
        if entry.etymology is not None:
            result["etymology"] = entry.etymology
        if entry.grammar_tags is not None:
            result["grammar_tags"] = entry.grammar_tags
        if entry.references is not None:
            # Simplify references to avoid noise
            result["references"] = self._simplify_references(entry.references)
        # Omit page_ref as requested - not useful for educational/analysis purposes
        # if entry.page_ref is not None:
        #     result["page_ref"] = entry.page_ref

        return result

    def _simplify_references(self, references) -> list[str] | dict:
        """Simplify references to avoid noise in CDSL tool output."""
        if not references:
            return []

        if isinstance(references, list):
            return references

        abbreviations: list[str] = []
        if hasattr(references, "citations"):
            abbreviations.extend(self._collect_abbreviations_from_objects(references.citations))
        elif isinstance(references, dict) and "citations" in references:
            abbreviations.extend(
                self._collect_abbreviations_from_dicts(references.get("citations"))
            )

        if abbreviations:
            return sorted(set(abbreviations))
        return []

    @staticmethod
    def _collect_abbreviations_from_objects(citations) -> list[str]:
        abbreviations: list[str] = []
        for citation in citations:
            if getattr(citation, "abbreviation", None):
                abbreviations.append(citation.abbreviation)
                continue
            for ref in getattr(citation, "references", []) or []:
                work = getattr(ref, "work", None)
                if work:
                    abbreviations.append(work)
        return abbreviations

    @staticmethod
    def _collect_abbreviations_from_dicts(citations) -> list[str]:
        abbreviations: list[str] = []
        if not isinstance(citations, list):
            return abbreviations
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            abbreviation = citation.get("abbreviation")
            if abbreviation:
                abbreviations.append(abbreviation)
                continue
            for ref in citation.get("references") or []:
                if isinstance(ref, dict) and ref.get("work"):
                    abbreviations.append(ref["work"])
        return abbreviations

    def _lookup_dict_formatted(
        self, dict_id: str, slp1_key: str, original_term: str
    ) -> list[SanskritDictionaryEntry]:
        dict_id_upper = dict_id.upper()
        try:
            conn = self._get_conn(dict_id_upper)
        except FileNotFoundError:
            return []

        rows = conn.execute(
            """
            SELECT key, lnum, data, body, page_ref
            FROM entries
            WHERE dict_id = ? AND key_normalized = ?
            ORDER BY lnum
            """,
            [dict_id_upper, slp1_key],
        ).fetchall()

        if not rows:
            return []

        return [self._build_entry_from_row(row) for row in rows]

    def _build_entry_from_row(self, row: tuple) -> SanskritDictionaryEntry:
        entry_id = str(int(float(row[1]))) if "." in str(row[1]) else str(row[1])
        subid = None
        id_parts = entry_id.split(ENTRY_ID_SUBID_SEPARATOR)
        if len(id_parts) == ENTRY_ID_MAX_PARTS:
            entry_id = id_parts[0]
            subid = id_parts[1]

        grammatical = parse_grammatical_info(row[2])
        references = self._extract_references(grammatical)

        return SanskritDictionaryEntry(
            id=entry_id,
            meaning=grammatical.get("meaning", row[3] or row[2][:200]),
            subid=subid,
            pos=grammatical.get("pos"),
            gender=grammatical.get("gender"),
            sanskrit_form=grammatical.get("sanskrit_form"),
            etymology=grammatical.get("etymology"),
            grammar_tags=grammatical.get("grammar_tags"),
            references=references,
            page_ref=row[4],
        )

    @staticmethod
    def _extract_references(grammatical: dict | None) -> list[str] | None:
        if not grammatical:
            return None
        raw_refs = grammatical.get("references")
        if not (raw_refs and isinstance(raw_refs, list)):
            return None
        abbreviations = []
        for ref_dict in raw_refs:
            if isinstance(ref_dict, dict) and "source" in ref_dict:
                abbreviations.append(ref_dict["source"])
        if not abbreviations:
            return None
        seen = set()
        dedup_abbreviations = []
        for abbr in abbreviations:
            if abbr not in seen:
                seen.add(abbr)
                dedup_abbreviations.append(abbr)
        return dedup_abbreviations
