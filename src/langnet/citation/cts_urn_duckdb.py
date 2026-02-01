"""
Updated CTSUrnMapper with DuckDB support.

This module extends the CTSUrnMapper to support both SQLite and DuckDB databases,
providing better performance with DuckDB while maintaining backward compatibility.
"""

import os
import sqlite3
import duckdb
import re
from typing import Dict, Optional, List, Tuple, Union
from pathlib import Path


class CTSUrnMapper:
    """Maps classical text references to CTS URNs with DuckDB support."""

    # Fallback mappings for when database is not available
    AUTHOR_TO_NAMESPACE: Dict[str, str] = {}

    # Fallback work mappings
    WORK_TO_CTS_ID: Dict[str, str] = {}

    def __init__(self, db_path: Optional[str] = None, use_duckdb: bool = True):
        self.db_path = db_path
        self.use_duckdb = use_duckdb
        self._db_conn: Optional[Union[sqlite3.Connection, duckdb.DuckDBPyConnection]] = None
        self._author_cache: Optional[Dict[str, Tuple[str, str]]] = None
        self._work_cache: Optional[Dict[str, Tuple[str, str, str]]] = None

        # Build reverse lookup for CTS namespace to language
        self.namespace_to_language = {
            "greekLit": "grc",
            "latinLit": "lat",
            "tlg": "grc",
            "phi": "lat",
        }

    def _get_db_path(self) -> Optional[str]:
        """Get the database path, checking common locations."""
        if self.db_path:
            return self.db_path

        # Check common locations
        candidates = [
            "/tmp/classical_refs.duckdb",  # DuckDB first
            "/tmp/classical_refs_new.db",  # SQLite fallback
            "/home/nixos/langnet-tools/langnet-cli/classical_refs.db",
            os.path.expanduser("~/.local/share/langnet/classical_refs.db"),
        ]

        for path in candidates:
            if os.path.exists(path):
                # Check if it's DuckDB or SQLite
                if path.endswith(".duckdb"):
                    return path
                elif self.use_duckdb:
                    continue  # Skip SQLite if we prefer DuckDB
                else:
                    return path

        return None

    def _get_connection(self) -> Optional[Union[sqlite3.Connection, duckdb.DuckDBPyConnection]]:
        """Get database connection, supporting both SQLite and DuckDB."""
        if self._db_conn:
            return self._db_conn

        db_path = self._get_db_path()
        if not db_path or not os.path.exists(db_path):
            return None

        try:
            if self.use_duckdb and db_path.endswith(".duckdb"):
                self._db_conn = duckdb.connect(db_path)
            else:
                self._db_conn = sqlite3.connect(db_path)
            return self._db_conn
        except Exception:
            return None

    def _load_author_cache(self) -> Dict[str, Tuple[str, str]]:
        """Load author mappings from database into cache with DuckDB optimization."""
        if self._author_cache is not None:
            return self._author_cache

        self._author_cache = {}
        conn = self._get_connection()

        if not conn:
            return self._author_cache

        try:
            if self.use_duckdb:
                # Use DuckDB's optimized query
                query = """
                SELECT author_id, author_name, cts_namespace 
                FROM author_index 
                WHERE cts_namespace IS NOT NULL
                """
                result = conn.execute(query)

                for row in result.fetchall():
                    author_id, author_name, cts_ns = row
                    normalized = author_name.lower().replace(" ", "")

                    # Add various abbreviation forms
                    self._author_cache[normalized] = (author_id, cts_ns)

                    # Add short abbreviation (first 3-4 letters)
                    if len(author_name) > 3:
                        short = author_name.split()[-1][:4].lower()
                        if short and short not in self._author_cache:
                            self._author_cache[short] = (author_id, cts_ns)
            else:
                # SQLite fallback
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT author_id, author_name, cts_namespace 
                    FROM author_index 
                    WHERE cts_namespace IS NOT NULL
                """)
                for row in cursor.fetchall():
                    author_id, author_name, cts_ns = row
                    normalized = author_name.lower().replace(" ", "")

                    # Add various abbreviation forms
                    self._author_cache[normalized] = (author_id, cts_ns)

                    # Add short abbreviation (first 3-4 letters)
                    if len(author_name) > 3:
                        short = author_name.split()[-1][:4].lower()
                        if short and short not in self._author_cache:
                            self._author_cache[short] = (author_id, cts_ns)

        except Exception:
            pass

        return self._author_cache

    def _load_work_cache(self) -> Dict[str, Tuple[str, str, str]]:
        """Load work mappings from database into cache with DuckDB optimization."""
        if self._work_cache is not None:
            return self._work_cache

        self._work_cache = {}
        conn = self._get_connection()

        if not conn:
            return self._work_cache

        try:
            if self.use_duckdb:
                # Use DuckDB's optimized query
                query = """
                SELECT canon_id, author_name, work_title, cts_urn
                FROM works 
                WHERE cts_urn IS NOT NULL
                """
                result = conn.execute(query)

                for row in result.fetchall():
                    canon_id, author_name, work_title, cts_urn = row

                    # Extract work ID from URN
                    if cts_urn and "urn:cts:" in cts_urn:
                        # urn:cts:tlg:author.canon:ref
                        parts = cts_urn.replace("urn:cts:", "").split(":")
                        if len(parts) >= 2:
                            work_id = parts[1]
                            namespace = parts[0]

                            # Normalize work title for matching
                            normalized_title = work_title.lower().replace(" ", "").replace(".", "")

                            self._work_cache[normalized_title] = (work_id, author_name, namespace)

                            # Add common abbreviations
                            words = normalized_title.split()
                            if words:
                                abbrev = "".join(w[:2] for w in words if w)
                                if abbrev and len(abbrev) >= 2:
                                    self._work_cache[abbrev] = (work_id, author_name, namespace)
            else:
                # SQLite fallback
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT canon_id, author_name, work_title, cts_urn
                    FROM works 
                    WHERE cts_urn IS NOT NULL
                """)
                for row in cursor.fetchall():
                    canon_id, author_name, work_title, cts_urn = row

                    # Extract work ID from URN
                    if cts_urn and "urn:cts:" in cts_urn:
                        # urn:cts:tlg:author.canon:ref
                        parts = cts_urn.replace("urn:cts:", "").split(":")
                        if len(parts) >= 2:
                            work_id = parts[1]
                            namespace = parts[0]

                            # Normalize work title for matching
                            normalized_title = work_title.lower().replace(" ", "").replace(".", "")

                            self._work_cache[normalized_title] = (work_id, author_name, namespace)

                            # Add common abbreviations
                            words = normalized_title.split()
                            if words:
                                abbrev = "".join(w[:2] for w in words if w)
                                if abbrev and len(abbrev) >= 2:
                                    self._work_cache[abbrev] = (work_id, author_name, namespace)

        except Exception:
            pass

        return self._work_cache

    def _normalize_abbreviation(self, abbreviation: str) -> str:
        """Normalize an abbreviation by converting to lowercase and removing periods."""
        return abbreviation.lower().replace(".", "").strip()

    def _get_namespace_from_work(self, work: str) -> Optional[str]:
        """Get namespace based on work abbreviation."""
        normalized_work = self._normalize_abbreviation(work)

        # Greek works
        greek_works = {"il", "od"}
        if normalized_work in greek_works:
            return "greekLit"

        # Latin works
        latin_works = {
            "aen",
            "georg",
            "ecl",
            "fin",
            "att",
            "phil",
            "c",
            "s",
            "nh",
            "inst",
            "tib",
            "epigr",
            "ach",
        }
        if normalized_work in latin_works:
            return "latinLit"

        return None

    def map_citation_to_urn(self, citation) -> Optional[str]:
        """
        Map a Citation to a CTS URN.

        Args:
            citation: Citation object with text reference information, or string citation

        Returns:
            CTS URN string or None if mapping not possible
        """
        from langnet.citation.models import Citation, TextReference, CitationType

        # Handle both Citation objects and string citations
        if isinstance(citation, str):
            # Convert string citation to Citation object for processing
            text_ref = TextReference(type=CitationType.LINE_REFERENCE, text=citation)
            citation = Citation(references=[text_ref])

        if not citation.references:
            return None

        text_ref = citation.references[0]

        # Extract author and work from the citation
        author = self._normalize_abbreviation(text_ref.author or "")
        work = self._normalize_abbreviation(text_ref.work or "")

        # Build location part
        location_parts = []
        if text_ref.book:
            location_parts.append(text_ref.book)
        if text_ref.line:
            location_parts.append(text_ref.line)
        location = ".".join(location_parts)

        # Try database lookup first
        urn = self._map_text_to_urn_from_database(author, work, location)
        if urn:
            return urn

        # Fall back to hardcoded mappings
        namespace = self.AUTHOR_TO_NAMESPACE.get(author)
        if not namespace:
            # Try to infer from work abbreviation
            namespace = self._get_namespace_from_work(work)

        if not namespace:
            return None

        work_id = self.WORK_TO_CTS_ID.get(work)
        if not work_id:
            return None

        # Build URN
        if location:
            return f"urn:cts:{namespace}:{work_id}:{location}"
        else:
            return f"urn:cts:{namespace}:{work_id}"

    def map_text_to_urn(self, text: str) -> Optional[str]:
        """
        Map a text reference like "Hom. Il. 1.1" or "Cic. Fin. 2, 24" to CTS URN.

        Args:
            text: Citation text to map

        Returns:
            CTS URN string or None if mapping not possible
        """
        # Parse the text to extract components
        # Handle both formats: "Hom. Il. 1.1" and "Cic. Fin. 2, 24"
        parts = text.replace(",", " ").split()
        if len(parts) < 2:
            return None

        author = self._normalize_abbreviation(parts[0])

        # Work can be multiple parts (e.g., "ab urbe condita")
        # Find the first numeric part which indicates the start of location
        location_parts = []
        work_parts = []

        for i, part in enumerate(parts[1:], 1):
            # Check if this part looks like a location (numeric or contains dot)
            if part.isdigit() or (part.replace(".", "", 1).isdigit() and "." in part):
                location_parts = parts[i:]
                work_parts = parts[1:i]
                break
        else:
            # No numeric part found, assume the rest is work
            work_parts = parts[1:]
            location_parts = []

        work = self._normalize_abbreviation(" ".join(work_parts))
        location = ".".join(location_parts) if location_parts else ""

        # Try database lookup first
        urn = self._map_text_to_urn_from_database(author, work, location)
        if urn:
            return urn

        # Fall back to hardcoded mappings
        namespace = self.AUTHOR_TO_NAMESPACE.get(author)
        if not namespace:
            # Try to infer from work abbreviation
            namespace = self._get_namespace_from_work(work)

        if not namespace:
            return None

        work_id = self.WORK_TO_CTS_ID.get(work)
        if not work_id:
            return None

        # Build URN
        if location:
            return f"urn:cts:{namespace}:{work_id}:{location}"
        else:
            return f"urn:cts:{namespace}:{work_id}"

    def _map_text_to_urn_from_database(
        self, author: str, work: str, location: str
    ) -> Optional[str]:
        """Try to map author/work to CTS URN using database."""
        conn = self._get_connection()
        if not conn:
            return None

        try:
            if self.use_duckdb:
                # Use DuckDB's optimized query
                query = """
                SELECT a.author_id, a.cts_namespace, w.cts_urn
                FROM author_index a
                JOIN works w ON a.author_id = w.author_id
                WHERE LOWER(REPLACE(a.author_name, ' ', '')) = ? 
                OR a.author_id = ?
                AND LOWER(REPLACE(w.reference, ' ', '')) = ?
                """
                result = conn.execute(query, (author, author.upper(), work))

                row = result.fetchone()
                if not row:
                    return None

                author_id, cts_namespace, cts_urn = row

                # If location is provided, append it to the URN
                if location:
                    # Append location to the existing URN
                    if cts_urn and not cts_urn.endswith(f":{location}"):
                        return f"{cts_urn}:{location}"

                return cts_urn
            else:
                # SQLite fallback
                cursor = conn.cursor()

                # First try to find author by normalized name
                cursor.execute(
                    """
                    SELECT author_id, cts_namespace 
                    FROM author_index 
                    WHERE LOWER(REPLACE(author_name, ' ', '')) = ? 
                    OR author_id = ?
                """,
                    (author, author.upper()),
                )

                author_result = cursor.fetchone()
                if not author_result:
                    return None

                author_id, cts_namespace = author_result

                # Now find work by reference and author_name
                cursor.execute(
                    """
                    SELECT cts_urn 
                    FROM works 
                    WHERE LOWER(REPLACE(reference, ' ', '')) = ? 
                    AND author_name = (
                        SELECT author_name FROM author_index WHERE author_id = ?
                    )
                """,
                    (work, author_id),
                )

                work_result = cursor.fetchone()
                if not work_result:
                    return None

                cts_urn = work_result[0]

                # If location is provided, append it to the URN
                if location:
                    # Append location to the existing URN
                    if cts_urn and not cts_urn.endswith(f":{location}"):
                        return f"{cts_urn}:{location}"

                return cts_urn

        except Exception:
            return None

    def add_urns_to_citations(self, citations):
        """
        Add CTS URNs to a list of citations.

        Args:
            citations: List of Citation objects

        Returns:
            List of Citation objects with URNs added
        """
        from langnet.citation.models import Citation

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

        # Try to parse from text
        text = text_ref.text or ""
        parts = text.replace(",", " ").split()

        if len(parts) >= 2:
            author = parts[0]
            work = parts[1]
            return author, work

        return "", ""


def get_perseus_to_cts_mapping() -> Dict[str, Optional[str]]:
    """
    Get common Perseus to CTS URN mappings.

    Returns:
        Dictionary mapping Perseus keys to CTS URNs (or None if unmapped)
    """
    mapper = CTSUrnMapper()

    return {
        # Homer
        "perseus:abo:phi,0119,001": mapper.map_text_to_urn("Hom. Il. 1"),
        "perseus:abo:phi,0119,001:1.1": mapper.map_text_to_urn("Hom. Il. 1.1"),
        "perseus:abo:phi,0120,001": mapper.map_text_to_urn("Hom. Od. 1"),
        # Virgil
        "perseus:abo:phi,0690,003": mapper.map_text_to_urn("Verg. A. 1"),
        "perseus:abo:phi,0690,003:1.1": mapper.map_text_to_urn("Verg. A. 1.1"),
        # Cicero
        "perseus:abo:phi,0956,005": mapper.map_text_to_urn("Cic. Fin. 2"),
        # Horace
        "perseus:abo:phi,0893,002": mapper.map_text_to_urn("Hor. C. 1"),
    }


def resolve_cts_urn(urn: str) -> Optional[str]:
    """
    Get the CTS API URL for a given URN.

    Args:
        urn: CTS URN string

    Returns:
        URL to resolve the URN or None if invalid
    """
    if not urn.startswith("urn:cts:"):
        return None

    # Remove "urn:cts:" prefix
    path = urn.replace("urn:cts:", "")

    # Get CTS API URL (example using Perseus CTS API)
    cts_api_base = "https://cts.perseids.org/api/cts/"

    return f"{cts_api_base}{path}"


# Example usage
if __name__ == "__main__":
    mapper = CTSUrnMapper()

    # Test mappings
    test_citations = [
        "Hom. Il. 1.1",
        "Verg. A. 1.1",
        "Cic. Fin. 2 24",
        "Hor. C. 1 17 9",
    ]

    print("CTS URN Mapping Examples:")
    print("-" * 60)

    for citation_text in test_citations:
        urn = mapper.map_text_to_urn(citation_text)
        if urn:
            print(f"{citation_text:20} -> {urn}")
        else:
            print(f"{citation_text:20} -> No URN mapping available")
        print()
