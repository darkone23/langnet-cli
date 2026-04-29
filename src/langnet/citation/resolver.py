from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from langnet.databuild.paths import default_cts_path
from langnet.storage.db import connect_duckdb_ro

logger = logging.getLogger(__name__)

MIN_HINT_TOKENS = 2
MIN_HINT_LENGTH = 2
PERSEUS_REF_PARTS = 3

NON_CTS_ABBREVIATIONS: dict[str, dict[str, dict[str, str]]] = {
    "grc": {
        "lsj": {"display": "LSJ", "long_name": "Liddell-Scott-Jones Greek-English Lexicon"},
    },
    "lat": {
        "ls": {"display": "Lewis & Short", "long_name": "Lewis and Short Latin Dictionary"},
        "old": {"display": "OLD", "long_name": "Oxford Latin Dictionary"},
    },
    "san": {
        "mw": {"display": "MW", "long_name": "Monier-Williams Sanskrit-English Dictionary"},
        "apte": {"display": "Apte", "long_name": "Apte Practical Sanskrit-English Dictionary"},
    },
}


@dataclass(frozen=True, slots=True)
class CitationResolution:
    citation_ref: str
    citation_text: str
    resolved: bool
    cts_urn: str | None = None
    author: str | None = None
    work: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


def _local_share_cts_path() -> Path:
    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "langnet/cts_urn.duckdb"


def find_default_cts_db() -> Path | None:
    candidates = [
        Path(os.getenv("LANGNET_CTS_DB", "")).expanduser() if os.getenv("LANGNET_CTS_DB") else None,
        default_cts_path(),
        _local_share_cts_path(),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def perseus_ref_to_cts_urn(perseus_ref: str) -> str | None:
    prefix = "perseus:abo:"
    if not perseus_ref.startswith(prefix):
        return None

    core = perseus_ref[len(prefix) :]
    work_part, separator, location = core.partition(":")
    parts = work_part.split(",")
    if len(parts) != PERSEUS_REF_PARTS:
        return None

    collection, author_id, work_id = parts
    if collection == "tlg":
        namespace = "greekLit"
        id_prefix = "tlg"
    elif collection == "phi":
        namespace = "latinLit"
        id_prefix = "phi"
    else:
        return None

    work_urn = f"urn:cts:{namespace}:{id_prefix}{author_id.zfill(4)}.{id_prefix}{work_id.zfill(3)}"
    if separator and location:
        return f"{work_urn}:{location.replace(':', '.')}"
    return work_urn


def _normalize_key(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in stripped.lower() if ch.isalnum())


def _hint_from_citation_text(citation_text: str) -> str:
    tokens = [token for token in re.split(r"[\s,.;:()]+", citation_text) if token]
    if len(tokens) < MIN_HINT_TOKENS:
        return ""
    hint = _normalize_key(tokens[1])
    if len(hint) < MIN_HINT_LENGTH or hint.isdigit() or hint in {"ib", "ibid", "id", "idem"}:
        return ""
    return hint


class CtsCitationResolver:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path).expanduser() if db_path else find_default_cts_db()

    def resolve(
        self,
        citation_ref: str,
        *,
        citation_text: str | None = None,
        language: str | None = None,
    ) -> CitationResolution:
        display_text = citation_text or citation_ref
        cts_urn = citation_ref if citation_ref.startswith("urn:cts:") else None
        if cts_urn is None:
            cts_urn = perseus_ref_to_cts_urn(citation_ref)

        if cts_urn:
            metadata = self.get_urn_metadata(cts_urn, citation_text=display_text) or {}
            return CitationResolution(
                citation_ref=citation_ref,
                citation_text=display_text,
                resolved=True,
                cts_urn=cts_urn,
                author=metadata.get("author"),
                work=metadata.get("work"),
                metadata=metadata,
            )

        abbreviation = self.get_abbreviation_metadata(citation_ref, display_text, language)
        if abbreviation:
            return CitationResolution(
                citation_ref=citation_ref,
                citation_text=display_text,
                resolved=False,
                metadata=abbreviation,
            )

        return CitationResolution(
            citation_ref=citation_ref,
            citation_text=display_text,
            resolved=False,
        )

    def get_urn_metadata(
        self, urn: str, *, citation_text: str | None = None
    ) -> dict[str, str] | None:
        if not self.db_path or not self.db_path.exists():
            return None

        try:
            with connect_duckdb_ro(self.db_path) as conn:
                row = conn.execute(
                    """
                    SELECT a.author_name, w.work_title
                    FROM works w
                    JOIN author_index a ON w.author_id = a.author_id
                    WHERE ? = w.cts_urn OR ? LIKE w.cts_urn || ':%'
                    ORDER BY (? = w.cts_urn) DESC, LENGTH(w.cts_urn) DESC
                    LIMIT 1
                    """,
                    (urn, urn, urn),
                ).fetchone()
                if row and citation_text:
                    hinted = self._lookup_work_by_hint(conn, urn, citation_text)
                    if hinted:
                        row = hinted
                if not row:
                    return None
                return {"author": str(row[0]), "work": str(row[1])}
        except Exception as exc:  # noqa: BLE001
            logger.debug("CTS metadata lookup failed for %s: %s", urn, exc)
            return None

    def _lookup_work_by_hint(self, conn, urn: str, citation_text: str) -> tuple[str, str] | None:
        hint = _hint_from_citation_text(citation_text)
        author_match = re.search(r"urn:cts:[^:]+:(?:phi|tlg)(\d{4})\.", urn)
        if not hint or not author_match:
            return None

        author_ids = [f"phi{author_match.group(1)}", f"tlg{author_match.group(1)}"]
        try:
            rows = conn.execute(
                """
                SELECT a.author_name, w.work_title
                FROM works w
                JOIN author_index a ON w.author_id = a.author_id
                WHERE w.author_id IN (?, ?)
                ORDER BY LENGTH(w.work_title), w.work_title
                """,
                author_ids,
            ).fetchall()
        except Exception as exc:  # noqa: BLE001
            logger.debug("CTS hint lookup failed for %s: %s", urn, exc)
            return None

        for author_name, work_title in rows:
            normalized_title = _normalize_key(str(work_title))
            if hint in normalized_title or normalized_title.startswith(hint):
                return str(author_name), str(work_title)
        return None

    def get_abbreviation_metadata(
        self,
        citation_ref: str | None,
        citation_text: str | None = None,
        language: str | None = None,
    ) -> dict[str, str] | None:
        keys = [_normalize_key(citation_ref), _normalize_key(citation_text)]
        scopes = [language] if language else []
        for scope in scopes:
            if not scope:
                continue
            scope_map = NON_CTS_ABBREVIATIONS.get(scope, {})
            for key in keys:
                if key in scope_map:
                    return {
                        **scope_map[key],
                        "kind": "abbreviation",
                        "language": scope,
                    }
        return None
