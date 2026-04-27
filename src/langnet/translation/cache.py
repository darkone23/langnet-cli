from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, dataclass

import duckdb


def text_hash(text: str) -> str:
    """Stable hash for source text, prompts, and translation hints."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TranslationCacheKey:
    source_lexicon: str
    entry_id: str
    occurrence: int
    headword_norm: str
    source_text_hash: str
    source_lang: str
    target_lang: str
    model: str
    prompt_hash: str
    hint_hash: str

    @property
    def translation_id(self) -> str:
        material = "\x1f".join(str(value) for value in asdict(self).values())
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
        return f"tr:{self.source_lexicon}:{self.entry_id}:{digest}"


@dataclass(frozen=True, slots=True)
class TranslationRecord:
    key: TranslationCacheKey
    translated_text: str | None
    status: str
    error: str | None = None
    duration_ms: int | None = None


def build_translation_key(  # noqa: PLR0913
    *,
    source_lexicon: str,
    entry_id: str,
    occurrence: int,
    headword_norm: str,
    source_text: str,
    source_lang: str = "fr",
    target_lang: str = "en",
    model: str,
    prompt: str,
    hint: str,
) -> TranslationCacheKey:
    return TranslationCacheKey(
        source_lexicon=source_lexicon,
        entry_id=entry_id,
        occurrence=occurrence,
        headword_norm=headword_norm,
        source_text_hash=text_hash(source_text),
        source_lang=source_lang,
        target_lang=target_lang,
        model=model,
        prompt_hash=text_hash(prompt),
        hint_hash=text_hash(hint),
    )


def apply_translation_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entry_translations (
          translation_id TEXT PRIMARY KEY,
          source_lexicon TEXT NOT NULL,
          entry_id TEXT NOT NULL,
          occurrence INTEGER NOT NULL,
          headword_norm TEXT,
          source_text_hash TEXT NOT NULL,
          source_lang TEXT NOT NULL,
          target_lang TEXT NOT NULL,
          model TEXT NOT NULL,
          prompt_hash TEXT NOT NULL,
          hint_hash TEXT NOT NULL,
          translated_text TEXT,
          status TEXT NOT NULL,
          error TEXT,
          duration_ms INTEGER,
          created_at DOUBLE NOT NULL,
          updated_at DOUBLE NOT NULL
        )
        """
    )


class TranslationCache:
    """DuckDB-backed cache for derived lexicon translations."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, read_only: bool = False) -> None:
        self.conn = conn
        self.read_only = read_only
        self._schema_applied = False

    def _ensure_schema(self) -> None:
        if not self._schema_applied:
            if not self.read_only:
                apply_translation_schema(self.conn)
            self._schema_applied = True

    def get(self, key: TranslationCacheKey) -> TranslationRecord | None:
        self._ensure_schema()
        try:
            row = self.conn.execute(
                """
                SELECT translated_text, status, error, duration_ms
                FROM entry_translations
                WHERE translation_id = ?
                """,
                [key.translation_id],
            ).fetchone()
        except duckdb.CatalogException:
            if self.read_only:
                return None
            raise
        if row is None:
            return None
        return TranslationRecord(
            key=key,
            translated_text=row[0],
            status=row[1],
            error=row[2],
            duration_ms=row[3],
        )

    def upsert(self, record: TranslationRecord) -> str:
        self._ensure_schema()
        now = time.time()
        key = record.key
        self.conn.execute(
            """
            INSERT OR REPLACE INTO entry_translations
            (translation_id, source_lexicon, entry_id, occurrence, headword_norm,
             source_text_hash, source_lang, target_lang, model, prompt_hash, hint_hash,
             translated_text, status, error, duration_ms, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE(
                      (SELECT created_at FROM entry_translations WHERE translation_id = ?),
                      ?
                    ),
                    ?)
            """,
            [
                key.translation_id,
                key.source_lexicon,
                key.entry_id,
                key.occurrence,
                key.headword_norm,
                key.source_text_hash,
                key.source_lang,
                key.target_lang,
                key.model,
                key.prompt_hash,
                key.hint_hash,
                record.translated_text,
                record.status,
                record.error,
                record.duration_ms,
                key.translation_id,
                now,
                now,
            ],
        )
        return key.translation_id
