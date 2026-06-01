from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import duckdb
import orjson

from langnet.databuild.paths import build_dir
from langnet.word_of_day import WORD_OF_DAY_SCHEMA_VERSION, WordCandidate

SUPPORTED_MOTD_POOL_LANGUAGES = ("san", "grc", "lat")


@dataclass(frozen=True, slots=True)
class MotdPoolCard:
    language: str
    query: str
    level: str
    didactic_score: int
    didactic_rationale: str
    item: dict[str, Any]
    source: str
    source_ref: str

    @property
    def key(self) -> str:
        return f"{self.language}:{self.query}"


@dataclass(frozen=True, slots=True)
class MotdCandidateMetadata:
    language: str
    query: str
    didactic_score: int
    didactic_rationale: str
    source_ref: str = ""


@dataclass(frozen=True, slots=True)
class MotdCandidateSet:
    pools: dict[str, list[WordCandidate]]
    metadata: dict[str, MotdCandidateMetadata]
    source_ref: str = ""


def default_motd_pool_path() -> Path:
    return build_dir() / "motd_pool.duckdb"


def load_motd_candidate_json(path: Path) -> MotdCandidateSet:
    payload = orjson.loads(path.read_bytes())
    items = payload.get("items") if isinstance(payload, Mapping) else None
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise ValueError("MOTD candidate JSON must contain an items[] array.")
    return motd_candidate_set_from_items(items, source_ref=str(path))


def motd_candidate_set_from_items(
    items: Sequence[object],
    *,
    source_ref: str = "",
) -> MotdCandidateSet:
    pools: dict[str, list[WordCandidate]] = {
        language: [] for language in SUPPORTED_MOTD_POOL_LANGUAGES
    }
    metadata: dict[str, MotdCandidateMetadata] = {}
    seen: set[str] = set()
    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        item = cast(Mapping[str, Any], raw_item)
        language = str(item.get("language") or "").strip().lower()
        query = str(item.get("query") or "").strip()
        if language not in SUPPORTED_MOTD_POOL_LANGUAGES or not query:
            continue
        key = _candidate_key(language, query)
        if key in seen:
            continue
        seen.add(key)
        difficulty = str(item.get("difficulty") or "beginner").strip().lower()
        if difficulty not in {"beginner", "intermediate", "deep"}:
            difficulty = "beginner"
        summary_hint = str(item.get("summary_hint") or item.get("summary") or "").strip()
        pools[language].append(
            WordCandidate(
                language=language,
                query=query,
                difficulty=difficulty,
                mnemonic=str(item.get("mnemonic") or "").strip(),
                summary_hint=summary_hint,
                didactic_score=_bounded_score(item.get("didactic_score")),
                didactic_rationale=str(item.get("didactic_rationale") or "").strip(),
            )
        )
        metadata[key] = MotdCandidateMetadata(
            language=language,
            query=query,
            didactic_score=_bounded_score(item.get("didactic_score")),
            didactic_rationale=str(item.get("didactic_rationale") or "").strip(),
            source_ref=source_ref,
        )
    return MotdCandidateSet(
        pools={language: candidates for language, candidates in pools.items() if candidates},
        metadata=metadata,
        source_ref=source_ref,
    )


def cards_from_word_of_day_payload(
    payload: Mapping[str, object],
    *,
    candidate_metadata: Mapping[str, MotdCandidateMetadata],
    source: str,
    source_ref: str = "",
    level: str = "beginner",
) -> list[MotdPoolCard]:
    items = payload.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return []
    cards: list[MotdPoolCard] = []
    for raw_item in items:
        if not isinstance(raw_item, Mapping):
            continue
        item = dict(raw_item)
        language = str(item.get("language") or "").strip().lower()
        query = str(item.get("query") or "").strip()
        if language not in SUPPORTED_MOTD_POOL_LANGUAGES or not query:
            continue
        metadata = candidate_metadata.get(_candidate_key(language, query))
        cards.append(
            MotdPoolCard(
                language=language,
                query=query,
                level=str(item.get("level") or level),
                didactic_score=metadata.didactic_score if metadata else 50,
                didactic_rationale=metadata.didactic_rationale if metadata else "",
                item=item,
                source=source,
                source_ref=source_ref or (metadata.source_ref if metadata else ""),
            )
        )
    return cards


def build_motd_pool(
    db_path: Path,
    cards: list[MotdPoolCard],
    *,
    replace: bool = False,
) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    try:
        if replace:
            conn.execute("DROP TABLE IF EXISTS motd_pool_cards")
        _ensure_schema(conn)
        for card in cards:
            conn.execute(
                """
                INSERT OR REPLACE INTO motd_pool_cards
                (card_key, language, query, level, didactic_score, didactic_rationale,
                 item_json, source, source_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    card.key,
                    card.language,
                    card.query,
                    card.level,
                    card.didactic_score,
                    card.didactic_rationale,
                    orjson.dumps(card.item).decode("utf-8"),
                    card.source,
                    card.source_ref,
                ],
            )
    finally:
        conn.close()
    validation = validate_motd_pool(db_path)
    return {
        "schema_version": "langnet.motd_pool.build.v1",
        "db_path": str(db_path),
        "inserted": len(cards),
        "ok": validation["ok"],
        "language_counts": validation["language_counts"],
        "issues": validation["issues"],
        "validation": validation,
    }


def validate_motd_pool(db_path: Path, *, per_language: int = 1) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "schema_version": "langnet.motd_pool.validation.v1",
            "db_path": str(db_path),
            "ok": False,
            "language_counts": {},
            "issues": [{"code": "missing_db", "message": "MOTD pool database does not exist."}],
        }
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT language, count(*)::INTEGER
            FROM motd_pool_cards
            GROUP BY language
            ORDER BY language
            """
        ).fetchall()
        duplicate_rows = conn.execute(
            """
            SELECT card_key, count(*)::INTEGER
            FROM motd_pool_cards
            GROUP BY card_key
            HAVING count(*) > 1
            ORDER BY card_key
            """
        ).fetchall()
    finally:
        conn.close()

    language_counts = {str(language): int(count) for language, count in rows}
    issues: list[dict[str, Any]] = []
    for language in SUPPORTED_MOTD_POOL_LANGUAGES:
        count = language_counts.get(language, 0)
        if count < per_language:
            issues.append(
                {
                    "code": "low_language_count",
                    "language": language,
                    "message": f"{language} has {count} cards; expected at least {per_language}.",
                }
            )
    for card_key, count in duplicate_rows:
        issues.append(
            {
                "code": "duplicate_card",
                "card_key": card_key,
                "message": f"{card_key} appears {count} times.",
            }
        )
    return {
        "schema_version": "langnet.motd_pool.validation.v1",
        "db_path": str(db_path),
        "ok": not issues,
        "language_counts": {
            language: language_counts.get(language, 0) for language in SUPPORTED_MOTD_POOL_LANGUAGES
        },
        "issues": issues,
    }


def sample_motd_pool(  # noqa: PLR0913
    db_path: Path,
    *,
    language: str = "all",
    count: int = 1,
    level: str = "beginner",
    seed: str | None = None,
    avoid: tuple[str, ...] = (),
) -> dict[str, Any]:
    if not db_path.exists():
        return _empty_pool_payload(
            db_path=db_path,
            language=language,
            level=level,
            seed=seed,
            count=count,
            warning="MOTD pool database does not exist.",
        )
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT card_key, language, query, level, didactic_score, didactic_rationale,
                   item_json, source, source_ref
            FROM motd_pool_cards
            WHERE (? = 'all' OR language = ?)
              AND level = ?
            ORDER BY language, didactic_score DESC, query
            """,
            [language, language, level],
        ).fetchall()
    finally:
        conn.close()

    avoided = {value.casefold() for value in avoid if value}
    cards = [
        _row_to_card(row)
        for row in rows
        if row[0].casefold() not in avoided and row[2].casefold() not in avoided
    ]
    selected = (
        _sample_balanced_cards(cards, count=count, seed=seed)
        if language == "all"
        else _sample_cards(cards, count=count, seed=seed)
    )
    return {
        "schema_version": WORD_OF_DAY_SCHEMA_VERSION,
        "mode": "recommend",
        "generated_at": datetime.now(UTC).isoformat(),
        "suggested_ttl_seconds": 86400,
        "items": [card.item for card in selected],
        "warnings": [],
        "exhaustion": [],
        "generator": {
            "mode": "precomputed-pool",
            "db_path": str(db_path),
            "language": language,
            "level": level,
            "seed": seed,
            "count": count,
        },
    }


def _empty_pool_payload(  # noqa: PLR0913
    *,
    db_path: Path,
    language: str,
    level: str,
    seed: str | None,
    count: int,
    warning: str,
) -> dict[str, Any]:
    return {
        "schema_version": WORD_OF_DAY_SCHEMA_VERSION,
        "mode": "recommend",
        "generated_at": datetime.now(UTC).isoformat(),
        "suggested_ttl_seconds": 300,
        "items": [],
        "warnings": [{"message": warning, "source": "motd-pool"}],
        "exhaustion": {
            "fresh_requested": False,
            "fresh_satisfied": False,
            "reason": warning,
        },
        "generator": {
            "mode": "precomputed-pool",
            "db_path": str(db_path),
            "language": language,
            "level": level,
            "seed": seed,
            "count": count,
        },
    }


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS motd_pool_cards (
          card_key TEXT PRIMARY KEY,
          language TEXT NOT NULL,
          query TEXT NOT NULL,
          level TEXT NOT NULL,
          didactic_score INTEGER NOT NULL,
          didactic_rationale TEXT NOT NULL,
          item_json TEXT NOT NULL,
          source TEXT NOT NULL,
          source_ref TEXT NOT NULL
        )
        """
    )


def _row_to_card(row: tuple[Any, ...]) -> MotdPoolCard:
    item = orjson.loads(str(row[6]))
    if not isinstance(item, dict):
        item = {}
    return MotdPoolCard(
        language=str(row[1]),
        query=str(row[2]),
        level=str(row[3]),
        didactic_score=int(row[4]),
        didactic_rationale=str(row[5]),
        item=item,
        source=str(row[7]),
        source_ref=str(row[8]),
    )


def _sample_cards(cards: list[MotdPoolCard], *, count: int, seed: str | None) -> list[MotdPoolCard]:
    ranked = sorted(
        cards,
        key=lambda card: (
            _stable_sample_rank(seed, card),
            -card.didactic_score,
            card.language,
            card.query,
        ),
    )
    return ranked[:count]


def _sample_balanced_cards(
    cards: list[MotdPoolCard],
    *,
    count: int,
    seed: str | None,
) -> list[MotdPoolCard]:
    groups = {
        language: _sample_cards(
            [card for card in cards if card.language == language],
            count=len(cards),
            seed=seed,
        )
        for language in SUPPORTED_MOTD_POOL_LANGUAGES
    }
    selected: list[MotdPoolCard] = []
    while len(selected) < count:
        before = len(selected)
        for language in SUPPORTED_MOTD_POOL_LANGUAGES:
            if groups[language]:
                selected.append(groups[language].pop(0))
                if len(selected) >= count:
                    break
        if len(selected) == before:
            break
    return selected


def _stable_sample_rank(seed: str | None, card: MotdPoolCard) -> int:
    material = orjson.dumps(
        {"seed": seed or "", "card": asdict(card)},
        option=orjson.OPT_SORT_KEYS,
    )
    return int(hashlib.sha256(material).hexdigest()[:16], 16)


def _candidate_key(language: str, query: str) -> str:
    return f"{language.strip().lower()}:{query.strip().lower()}"


def _bounded_score(value: object) -> int:
    if isinstance(value, bool):
        return 50
    if isinstance(value, int):
        score = value
    elif isinstance(value, str):
        try:
            score = int(value)
        except ValueError:
            return 50
    else:
        return 50
    return min(100, max(0, score))
