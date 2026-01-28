import os
import structlog
import sqlite3
from pathlib import Path
from decimal import Decimal
from typing import Optional, cast, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import time

import duckdb
from indic_transliteration import sanscript
from indic_transliteration.detect import detect
from indic_transliteration.sanscript import transliterate, SLP1, DEVANAGARI

from .models import (
    CdslQueryResult,
    SanskritDictionaryLookup,
    SanskritDictionaryEntry,
    SanskritTransliteration,
    SanskritDictionaryResponse,
)
from .parser import parse_xml_entry, extract_headwords, parse_grammatical_info

logger = structlog.get_logger(__name__)


def get_cdsl_db_dir() -> Path:
    from langnet.config import config

    return config.cdsl_db_dir


def get_cdsl_dict_dir() -> Path:
    from langnet.config import config

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


def to_slp1(text: str) -> str:
    from indic_transliteration.detect import detect
    from indic_transliteration.sanscript import transliterate, SLP1

    src = detect(text)
    return transliterate(text, src, SLP1).lower()


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
                headwords_data.append(
                    (dict_id, entry.key2, hw_norm2, str(lnum_str), False)
                )

    return entries_data, headwords_data


class CdslIndexBuilder:
    @staticmethod
    def build(
        dict_dir: Path,
        output_db: Path,
        dict_id: str,
        limit: Optional[int] = None,
        batch_size: Optional[int] = None,
        num_workers: Optional[int] = None,
    ) -> int:
        sqlite_path = dict_dir / "web" / "sqlite" / f"{dict_id.lower()}.sqlite"
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite file not found: {sqlite_path}")

        output_db.parent.mkdir(parents=True, exist_ok=True)

        if output_db.exists():
            output_db.unlink()

        conn = duckdb.connect(str(output_db))

        try:
            for stmt in CdslSchema.get_sql().split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)

            logger.info("indexing_start", dict_id=dict_id, limit=limit)

            sqlite_conn = sqlite3.connect(str(sqlite_path))
            try:
                cursor = sqlite_conn.execute(f"SELECT key, lnum, data FROM {dict_id}")
                all_rows = list(cursor)
            finally:
                sqlite_conn.close()

            if limit:
                all_rows = all_rows[:limit]

            logger.info("rows_loaded", dict_id=dict_id, total=len(all_rows))

            if batch_size:
                actual_batch_size = batch_size
            else:
                actual_batch_size = max(
                    100, len(all_rows) // (num_workers or mp.cpu_count())
                )

            batches = [
                all_rows[i : i + actual_batch_size]
                for i in range(0, len(all_rows), actual_batch_size)
            ]

            num_workers = num_workers or mp.cpu_count()
            logger.info(
                "processing_batches",
                dict_id=dict_id,
                batches=len(batches),
                workers=num_workers,
                batch_size=actual_batch_size,
            )

            all_entries = []
            all_headwords = []

            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {
                    executor.submit(parse_batch, (sqlite_path, dict_id, batch)): idx
                    for idx, batch in enumerate(batches)
                }
                completed = 0
                total_batches = len(batches)
                batch_start_time = time.perf_counter()
                for future in as_completed(futures):
                    batch_idx = futures[future]
                    batch_num = batch_idx + 1
                    entries, headwords = future.result()
                    all_entries.extend(entries)
                    all_headwords.extend(headwords)
                    completed += 1
                    elapsed = time.perf_counter() - batch_start_time
                    logger.info(
                        "batch_progress",
                        dict_id=dict_id,
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
                    dict_id=dict_id,
                    total_batches=total_batches,
                    total_entries=len(all_entries),
                    total_headwords=len(all_headwords),
                    elapsed_seconds=round(time.perf_counter() - batch_start_time, 2),
                )

            logger.info(
                "indexing_bulk_insert",
                dict_id=dict_id,
                entries=len(all_entries),
                headwords=len(all_headwords),
            )

            if all_entries:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO entries (dict_id, key, key_normalized, key2, key2_normalized, lnum, data, body, page_ref)
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
                dict_id=dict_id,
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
        limit: Optional[int] = None,
        skip_english: bool = True,
        num_workers: Optional[int] = None,
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

    def prefix_search(
        self, dict_id: str, prefix: str, limit: int = 20
    ) -> list[tuple[str, str]]:
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
    limit: Optional[int] = None,
    num_workers: Optional[int] = None,
) -> int:
    return CdslIndexBuilder.build(dict_dir, output_db, dict_id, limit, num_workers)


def batch_build(
    dict_root: Path,
    output_dir: Path,
    limit: Optional[int] = None,
    skip_english: bool = True,
    num_workers: Optional[int] = None,
) -> dict[str, int]:
    return CdslIndexBuilder.build_all(
        dict_root, output_dir, limit, skip_english, num_workers
    )


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
            self._connections[dict_id_upper] = duckdb.connect(
                str(db_path), read_only=True
            )
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

        # Create transliteration object
        slp1_term = to_slp1(data)
        try:
            deva_term = transliterate(slp1_term, SLP1, DEVANAGARI)
        except Exception:
            deva_term = data

        transliteration = SanskritTransliteration(
            input=data,
            iast=slp1_term,
            hk=slp1_term,
            devanagari=deva_term,
        )

        return {
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

    def _serialize_entry(self, entry: SanskritDictionaryEntry) -> dict[str, Any]:
        result: dict[str, Any] = {
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
            result["references"] = entry.references
        if entry.page_ref is not None:
            result["page_ref"] = entry.page_ref

        return result

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

        entries = []
        for row in rows:
            entry_id = str(int(float(row[1]))) if "." in str(row[1]) else str(row[1])
            subid = None
            id_parts = entry_id.split(".")
            if len(id_parts) == 2:
                entry_id = id_parts[0]
                subid = id_parts[1]

            # Parse grammatical information from XML
            grammatical = parse_grammatical_info(row[2])

            entries.append(
                SanskritDictionaryEntry(
                    id=entry_id,
                    meaning=grammatical.get("meaning", row[3] or row[2][:200]),
                    subid=subid,
                    pos=grammatical.get("pos"),
                    gender=grammatical.get("gender"),
                    sanskrit_form=grammatical.get("sanskrit_form"),
                    etymology=grammatical.get("etymology"),
                    grammar_tags=grammatical.get("grammar_tags"),
                    references=grammatical.get("references"),
                    page_ref=row[4],
                )
            )

        return entries
