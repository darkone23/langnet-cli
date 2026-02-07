"""
CTS URN Mapping for Citation System.

This module provides functionality to map classical text references to CTS URNs
(Canonical Text Service Uniform Resource Names) for standardized referencing.

CTS URN Format:
    cts:namespace.work.section.subdivision

Example mappings:
    "Hom. Il. 1.1" -> "urn:cts:greekLit:tlg0012.tlg001:1.1"
    "Verg. A. 1.1" -> "urn:cts:latinLit:phi1290.phi004:1.1"
    "perseus:abo:tlg,0011,001:911" -> "urn:cts:greekLit:tlg0011.tlg001:911"

The mapper uses the DuckDB CTS URN indexer database for authoritative mappings.
"""

import logging
import os
import unicodedata

import duckdb

from langnet.heritage.abbr import HERITAGE_ABBR_MAP

logger = logging.getLogger(__name__)

MIN_AUTHOR_NAME_LENGTH = 3
MIN_WORK_TITLE_LENGTH = 4
MIN_ABBREV_LENGTH = 2

# Allowlisted non-CTS abbreviations for dictionary citations, scoped by language.
# Keys inside each map are normalized (lowercase, alphanumeric) forms.
NON_CTS_ABBREVIATIONS: dict[str, dict[str, dict[str, str]]] = {
    "grc": {
        "lsj": {"display": "LSJ", "long_name": "Liddell-Scott-Jones Greek-English Lexicon"},
        "dge": {"display": "DGE", "long_name": "Diccionario Griego-Espanol"},
        "lfgre": {"display": "LfgrE", "long_name": "Lexikon des fruhgriechischen Epos"},
    },
    "lat": {
        "old": {"display": "OLD", "long_name": "Oxford Latin Dictionary"},
        "ls": {"display": "Lewis & Short", "long_name": "Lewis and Short Latin Dictionary"},
        "lewisandshort": {
            "display": "Lewis & Short",
            "long_name": "Lewis and Short Latin Dictionary",
        },
        "l": {"display": "Livy", "long_name": "Titus Livius"},
    },
    "san": {
        "mw": {"display": "MW", "long_name": "Monier-Williams Sanskrit-English Dictionary"},
        "monierwilliams": {
            "display": "MW",
            "long_name": "Monier-Williams Sanskrit-English Dictionary",
        },
        "apte": {"display": "Apte", "long_name": "Apte Practical Sanskrit-English Dictionary"},
        "boehtlingkroth": {
            "display": "Boehtlingk-Roth",
            "long_name": "Sanskrit-Worterbuch (Boehtlingk & Roth)",
        },
        "susr": {"display": "Susr.", "long_name": "Susruta Samhita"},
        "un": {"display": "Un.", "long_name": "Unadisastra"},
        "apsr": {"display": "ApSr.", "long_name": "Apastamba Srauta Sutra"},
        "katantra": {"display": "Katantra", "long_name": "Katantra grammar"},
        "garhapatya": {"display": "Gārhapatya", "long_name": "Gārhapatya sacred fire"},
        "ahavaniya": {"display": "Āhavanīya", "long_name": "Āhavanīya sacred fire"},
        "dakshina": {"display": "Dakṣiṇa", "long_name": "Dakṣiṇa sacred fire"},
        "suryas": {"display": "Sūryas.", "long_name": "Sūryas collection"},
        "sun": {"display": "Sūryas.", "long_name": "Sūryas collection"},
    },
}


class CTSUrnMapper:
    """Maps classical text references to CTS URNs."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        self._db_conn = None
        self._author_cache: dict[str, tuple[str, str]] | None = None
        self._work_cache: dict[str, tuple[str, str, str]] | None = None

        self.namespace_to_language = {
            "greekLit": "grc",
            "latinLit": "lat",
            "tlg": "grc",
            "phi": "lat",
        }

    def _get_db_path(self) -> str | None:
        """Get the database path, checking common locations."""
        if self.db_path:
            return self.db_path

        candidates = [
            os.path.expanduser("~/.local/share/langnet/cts_urn.duckdb"),
            "/home/nixos/.local/share/langnet/cts_urn.duckdb",
            "/tmp/classical_refs.db",
        ]

        for path in candidates:
            if os.path.exists(path):
                return path

        return None

    def _get_connection(self):
        """Get database connection, lazy-loading."""
        if self._db_conn:
            return self._db_conn

        db_path = self._get_db_path()
        if db_path and os.path.exists(db_path):
            try:
                self._db_conn = duckdb.connect(db_path)
                return self._db_conn
            except Exception as e:
                logger.debug(f"Could not connect to DuckDB: {e}")

        return None

    def _load_author_cache(self) -> dict[str, tuple[str, str]]:
        """Load author mappings from database into cache."""
        if self._author_cache is not None:
            return self._author_cache

        self._author_cache = {}

        conn = self._get_connection()
        if not conn:
            return self._author_cache

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT author_id, author_name, namespace
                FROM author_index
                ORDER BY LENGTH(author_id), author_id
            """)
            for row in cursor.fetchall():
                author_id, author_name, namespace = row
                normalized = author_name.lower().replace(" ", "")

                self._author_cache[normalized] = (author_id, namespace)

                if len(author_name) > MIN_AUTHOR_NAME_LENGTH:
                    short = author_name.split()[-1][:4].lower()
                    if short and short not in self._author_cache:
                        self._author_cache[short] = (author_id, namespace)

        except Exception as e:
            logger.debug(f"Error loading author cache: {e}")

        return self._author_cache

    def _load_work_cache(self) -> dict[str, tuple[str, str, str]]:
        """Load work mappings from database into cache."""
        if self._work_cache is not None:
            return self._work_cache

        self._work_cache = {}

        conn = self._get_connection()
        if not conn:
            return self._work_cache

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT canon_id, work_title, author_id, namespace "
                "FROM works WHERE cts_urn IS NOT NULL"
            )
            for row in cursor.fetchall():
                canon_id, work_title, author_id, namespace = row

                if canon_id:
                    normalized_title = work_title.lower().replace(" ", "").replace(".", "")
                    self._work_cache[normalized_title] = (canon_id, author_id, namespace)

                    words = normalized_title.split()
                    if words:
                        abbrev = "".join(w[:2] for w in words if w)
                        if abbrev and len(abbrev) >= MIN_ABBREV_LENGTH:
                            self._work_cache[abbrev] = (canon_id, author_id, namespace)

        except Exception as e:
            logger.debug(f"Error loading work cache: {e}")

        return self._work_cache

    def _normalize_abbreviation(self, abbreviation: str) -> str:
        """Normalize an abbreviation by converting to lowercase and removing periods and spaces."""
        # return abbreviation.lower().replace(".", "").replace(" ", "").strip()
        return abbreviation

    @staticmethod
    def _normalize_abbrev_key(text: str | None) -> str:
        """Normalize arbitrary citation text into an abbreviation key."""
        if not text:
            return ""
        decomposed = unicodedata.normalize("NFD", text)
        stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
        return "".join(ch for ch in stripped.lower() if ch.isalnum())

    def map_citation_to_urn(self, citation) -> str | None:
        """
        Map a Citation to a CTS URN.

        Args:
            citation: Citation object with text reference information, or string citation

        Returns:
            CTS URN string or None if mapping not possible
        """
        from langnet.citation.models import Citation, CitationType, TextReference  # noqa: PLC0415

        if isinstance(citation, str):
            text_ref = TextReference(type=CitationType.LINE_REFERENCE, text=citation)
            citation = Citation(references=[text_ref])

        if not citation.references:
            return None

        text_ref = citation.references[0]

        author = self._normalize_abbreviation(text_ref.author or "")
        work = self._normalize_abbreviation(text_ref.work or "")

        location_parts = []
        if text_ref.book:
            location_parts.append(text_ref.book)
        if text_ref.line:
            location_parts.append(text_ref.line)
        location = ".".join(location_parts)

        urn = self._map_text_to_urn_from_database(author, work, location)
        return urn

    def map_text_to_urn(self, text: str) -> str | None:
        """
        Map a text reference to CTS URN.

        Handles multiple formats:
        1. Perseus format: "perseus:abo:tlg,0011,001:911" → "urn:cts:greekLit:tlg0011.tlg001:911"

        Args:
            text: Citation text to map

        Returns:
            CTS URN string or None if mapping not possible
        """
        if not text:
            return None

        if text.startswith("perseus:abo:"):
            # diogenes response mapping
            return self.map_perseus_to_urn(text)

        return None

    @staticmethod
    def map_perseus_to_urn(perseus_ref: str) -> str | None:
        """
        Map Perseus canonical reference to CTS URN.

        Format: perseus:abo:{collection},{author_id},{work_id}:{location}
        Examples:
            perseus:abo:tlg,0011,001:911      → urn:cts:greekLit:tlg0011.tlg001:911
            perseus:abo:phi,0690,003:1:2      → urn:cts:latinLit:phi0690.phi003:1.2
            perseus:abo:phi,0474,043:2:3:6    → urn:cts:latinLit:phi0474.phi043:2.3.6

        Args:
            perseus_ref: Perseus canonical reference string

        Returns:
            CTS URN string or None if parsing fails
        """
        try:
            prefix = "perseus:abo:"
            if not perseus_ref.startswith(prefix):
                return None

            core = perseus_ref[len(prefix) :]

            if ":" in core:
                location_part = core.split(":")[-1]
                work_part = core.rsplit(":", 1)[0]
            else:
                location_part = ""
                work_part = core

            parts = work_part.split(",")

            collection, author_id, work_id = parts

            if collection == "tlg":
                namespace = "greekLit"
                prefix_type = "tlg"
            elif collection == "phi":
                namespace = "latinLit"
                prefix_type = "phi"
            elif collection == "stoa":
                namespace = "latinLit"
                prefix_type = "stoa"
            else:
                return None

            author_num = author_id.zfill(4)
            work_num = work_id.zfill(3)

            # TODO; better stoa mappings
            # if prefix_type == "stoa":
            #     work_num += ".opp-lat1"

            if location_part:
                work_urn = f"{prefix_type}{author_num}.{prefix_type}{work_num}"
                urn = f"urn:cts:{namespace}:{work_urn}:{location_part}"
                return urn
            else:
                return f"urn:cts:{namespace}:{prefix_type}{author_num}.{prefix_type}{work_num}"

        except Exception:
            return None

    def _map_text_to_urn_from_database(self, author: str, work: str, location: str) -> str | None:
        """Try to map author/work to CTS URN using database."""
        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT author_id, namespace
                FROM author_index
                WHERE LOWER(REPLACE(author_name, ' ', '')) = ?
                OR LOWER(author_id) = ?
                ORDER BY LENGTH(author_id), author_id
                LIMIT 1
            """,
                (author.lower(), author.lower()),
            )

            author_result = cursor.fetchone()

            if not author_result:
                cursor.execute(
                    """
                    SELECT author_id, namespace
                    FROM author_index
                    WHERE REPLACE(LOWER(author_name), ' ', '') LIKE ?
                    OR LOWER(author_id) LIKE ?
                    ORDER BY 
                        CASE WHEN namespace = 'greekLit' THEN 0 ELSE 1 END,
                        LENGTH(author_id), 
                        author_id
                    LIMIT 1
                    """,
                    (f"{author.lower()}%", f"{author.lower()}%"),
                )
                author_result = cursor.fetchone()

            if not author_result:
                return None

            author_id, cts_namespace = author_result

            normalized_work = work.lower().replace(" ", "").replace(".", "")

            cursor.execute(
                """
                SELECT cts_urn, work_title
                FROM works
                WHERE author_id = ?
                AND (
                    LOWER(REPLACE(work_title, ' ', '')) = ?
                    OR LOWER(REPLACE(work_title, ' ', '')) LIKE ? || '%'
                )
                ORDER BY work_reference
                LIMIT 1
            """,
                (author_id, normalized_work, normalized_work),
            )

            work_result = cursor.fetchone()
            if not work_result:
                return None

            cts_urn = work_result[0]

            if location and cts_urn and not cts_urn.endswith(f":{location}"):
                return f"{cts_urn}:{location}"

            return cts_urn

        except Exception as e:
            logger.debug(f"Database lookup error: {e}")
            return None

    def get_urn_metadata(self, urn: str) -> dict[str, str] | None:
        """
        Look up author/work metadata for a CTS URN using the local index.

        Returns a dict with author_name and work_title when available.
        """
        if not urn:
            return None

        conn = self._get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            # Exact match first
            row = cursor.execute(
                """
                SELECT a.author_name, w.work_title
                FROM works w
                JOIN author_index a ON w.author_id = a.author_id
                WHERE w.cts_urn = ?
                LIMIT 1
                """,
                (urn,),
            ).fetchone()

            # Fallback: allow urn with location component (prefix match)
            if not row:
                row = cursor.execute(
                    """
                    SELECT a.author_name, w.work_title
                    FROM works w
                    JOIN author_index a ON w.author_id = a.author_id
                    WHERE ? LIKE w.cts_urn || '%'
                    ORDER BY LENGTH(w.cts_urn) DESC
                    LIMIT 1
                    """,
                    (urn,),
                ).fetchone()

            if not row:
                return None

            author_name, work_title = row
            return {"author": author_name, "work": work_title}
        except Exception as e:
            logger.debug(f"URN metadata lookup failed: {e}")
            return None

    def get_abbreviation_metadata(
        self, citation_id: str | None, citation_text: str | None = None, language: str | None = None
    ) -> dict[str, str] | None:
        """
        Get metadata for non-CTS abbreviation-based citations using the local allowlist.

        Returns display/long_name when available while preserving the original id/text.
        """
        keys = []
        for raw in (citation_id, citation_text):
            norm = self._normalize_abbrev_key(raw)
            if norm:
                keys.append(norm)

        scopes = []
        if language:
            scopes.append(language)
        scopes.append("global")

        # Merge in Heritage ABBR map for Sanskrit
        if language == "san":
            scopes.insert(0, "heritage")

        for scope in scopes:
            scope_map = NON_CTS_ABBREVIATIONS.get(scope, {})
            if scope == "heritage":
                scope_map = HERITAGE_ABBR_MAP
            for key in keys:
                meta = scope_map.get(key)
                if meta:
                    enriched = {**meta, "kind": "abbreviation", "language": language or scope}
                    if citation_text and "display" not in enriched:
                        enriched["display"] = citation_text
                    return enriched

        return None

    def add_urns_to_citations(self, citations):
        """
        Add CTS URNs to a list of citations.

        Args:
            citations: List of Citation objects

        Returns:
            List of Citation objects with URNs added
        """

        for citation in citations:
            if citation.references:
                urn = self.map_citation_to_urn(citation)
                if urn and not citation.references[0].cts_urn:
                    citation.references[0].cts_urn = urn
        return citations

    def extract_author_work_from_citation(self, citation) -> tuple:
        """
        Extract author and work from a citation.

        Args:
            citation: Citation object

        Returns:
            Tuple of (author, work) strings
        """
        if not citation.references:
            return "", ""

        text_ref = citation.references[0]

        text = text_ref.text or ""
        parts = text.replace(",", " ").split()

        if len(parts) >= MIN_ABBREV_LENGTH:
            author = parts[0]
            work = parts[1]
            return author, work

        return "", ""
