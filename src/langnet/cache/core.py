import duckdb
import json
import os
from pathlib import Path
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

SUPPORTED_LANGS = {"lat", "grc", "san"}

CACHE_TABLE_NAME = "query_cache"


def _get_db_path(cache_dir: Path, lang: str) -> Path:
    return cache_dir / f"langnet_{lang}.duckdb"


@dataclass
class QueryCache:
    cache_dir: Path

    def __post_init__(self):
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for lang in SUPPORTED_LANGS:
            self._ensure_db_exists(lang)
        logger.debug("cache_initialized", cache_dir=str(self.cache_dir))

    def _ensure_db_exists(self, lang: str):
        db_path = _get_db_path(self.cache_dir, lang)
        conn = duckdb.connect(str(db_path))
        try:
            conn.execute(f"""
                CREATE SEQUENCE IF NOT EXISTS cache_id_seq
            """)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {CACHE_TABLE_NAME} (
                    id INTEGER PRIMARY KEY DEFAULT nextval('cache_id_seq'),
                    query VARCHAR NOT NULL,
                    result VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_query_{lang} ON {CACHE_TABLE_NAME}(query)
            """)
        finally:
            conn.close()

    def _get_conn(self, lang: str):
        return duckdb.connect(str(_get_db_path(self.cache_dir, lang)))

    def get(self, lang: str, query: str) -> dict | None:
        if lang not in SUPPORTED_LANGS:
            return None
        conn = self._get_conn(lang)
        try:
            result = conn.execute(
                f"""
                SELECT result FROM {CACHE_TABLE_NAME}
                WHERE query = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
                [query],
            ).fetchone()
            if result:
                logger.debug("cache_hit", lang=lang, query=query)
                return json.loads(result[0])
            logger.debug("cache_miss", lang=lang, query=query)
            return None
        finally:
            conn.close()

    def put(self, lang: str, query: str, result: dict) -> None:
        if lang not in SUPPORTED_LANGS:
            return
        conn = self._get_conn(lang)
        try:
            result_json = json.dumps(result)
            conn.execute(
                f"""
                INSERT INTO {CACHE_TABLE_NAME} (query, result)
                VALUES (?, ?)
            """,
                [query, result_json],
            )
            logger.debug("cache_stored", lang=lang, query=query)
        finally:
            conn.close()

    def clear(self) -> int:
        total = 0
        for lang in SUPPORTED_LANGS:
            conn = self._get_conn(lang)
            try:
                conn.execute(f"TRUNCATE TABLE {CACHE_TABLE_NAME}")
            finally:
                conn.close()
        logger.debug("cache_cleared")
        return total

    def clear_by_lang(self, lang: str) -> int:
        if lang not in SUPPORTED_LANGS:
            return 0
        conn = self._get_conn(lang)
        try:
            count_result = conn.execute(
                f"SELECT COUNT(*) FROM {CACHE_TABLE_NAME}"
            ).fetchone()
            count = count_result[0] if count_result else 0
            conn.execute(f"TRUNCATE TABLE {CACHE_TABLE_NAME}")
            logger.debug("cache_cleared_by_lang", lang=lang, count=count)
            return count
        finally:
            conn.close()

    def clear_by_key(self, lang: str, query: str) -> int:
        if lang not in SUPPORTED_LANGS:
            return 0
        conn = self._get_conn(lang)
        try:
            count_result = conn.execute(
                f"SELECT COUNT(*) FROM {CACHE_TABLE_NAME} WHERE query = ?",
                [query],
            ).fetchone()
            count = count_result[0] if count_result else 0
            conn.execute(
                f"DELETE FROM {CACHE_TABLE_NAME} WHERE query = ?",
                [query],
            )
            logger.debug("cache_cleared_by_key", lang=lang, query=query, count=count)
            return count
        finally:
            conn.close()

    def get_stats(self) -> dict:
        total = 0
        by_lang = {}
        lang_details = []
        for lang in SUPPORTED_LANGS:
            db_path = _get_db_path(self.cache_dir, lang)
            conn = self._get_conn(lang)
            try:
                count_result = conn.execute(
                    f"SELECT COUNT(*) FROM {CACHE_TABLE_NAME}"
                ).fetchone()
                count = count_result[0] if count_result else 0
                by_lang[lang] = count
                total += count
                db_size = int(db_path.stat().st_size) if db_path.exists() else 0
                lang_details.append(
                    {
                        "lang": lang,
                        "entries": count,
                        "size_bytes": db_size,
                        "size_human": self._human_size(db_size),
                    }
                )
            finally:
                conn.close()
        total_size = sum(d["size_bytes"] for d in lang_details)
        return {
            "total_entries": total,
            "by_language": by_lang,
            "languages": lang_details,
            "total_size_bytes": total_size,
            "total_size_human": self._human_size(total_size),
        }

    def _human_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size = int(size / 1024)
        return f"{size:.1f}TB"

    def close(self) -> None:
        pass


class NoOpCache:
    cache_dir = Path("/dev/null")

    def get(self, lang: str, query: str) -> dict | None:
        return None

    def put(self, lang: str, query: str, result: dict) -> None:
        pass

    def clear(self) -> None:
        pass

    def clear_by_lang(self, lang: str) -> int:
        return 0

    def clear_by_key(self, lang: str, query: str) -> int:
        return 0

    def get_stats(self) -> dict:
        return {
            "total_entries": 0,
            "by_language": {},
            "languages": [],
            "total_size_bytes": 0,
            "total_size_human": "0.0B",
        }

    def close(self) -> None:
        pass


def get_cache_path() -> Path:
    default_path = Path(
        os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    )
    cache_dir = default_path / "langnet"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def create_cache(cache_enabled: bool = True) -> QueryCache | NoOpCache:
    if not cache_enabled:
        return NoOpCache()
    return QueryCache(cache_dir=get_cache_path())
