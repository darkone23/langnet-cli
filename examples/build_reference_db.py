#!/usr/bin/env python3
"""
Build a DuckDB database of classical texts reference data.

This script parses TEI XML files, PHI/TLG author index files, and TLG canon files
from the Classics-Data directory to create a comprehensive reference database.
"""

import os
import re
import glob
import sqlite3
from pathlib import Path
from xml.etree import ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ClassicalText:
    """Represents a classical text with its metadata."""

    text_id: str
    title: str
    author: Optional[str]
    author_normalized: Optional[str]
    work_type: Optional[str]
    language: str
    publisher: Optional[str]
    pub_place: Optional[str]
    pub_date: Optional[str]
    source: str
    file_path: str
    full_name: str

    def to_dict(self) -> Dict:
        return {
            "text_id": self.text_id,
            "title": self.title,
            "author": self.author,
            "author_normalized": self.author_normalized,
            "work_type": self.work_type,
            "language": self.language,
            "publisher": self.publisher,
            "pub_place": self.pub_place,
            "pub_date": self.pub_date,
            "source": self.source,
            "file_path": self.file_path,
            "full_name": self.full_name,
        }


@dataclass
class AuthorEntry:
    """Represents an author entry from PHI/TLG index files."""

    author_id: str
    author_name: str
    alternate_name: Optional[str]
    genre: Optional[str]
    language: str
    source: str


@dataclass
class CanonEntry:
    """Represents a work entry from TLG canon files."""

    canon_id: str
    author_name: str
    work_title: str
    reference: Optional[str]
    word_count: Optional[str]
    work_type: Optional[str]
    source: str


class TEIXMLParser:
    """Parser for TEI XML files from digilibLT and similar sources."""

    # Common Latin author name variations for normalization
    AUTHOR_VARIANTS = {
        # Cicero
        "cicero": "Cicero",
        "m. tullius cicero": "Cicero",
        "marcus tullius cicero": "Cicero",
        # Virgil
        "vergilius": "Vergil",
        "p. vergilius maro": "Vergil",
        "publius vergilius maro": "Vergil",
        # Horace
        "horatius": "Horace",
        "q. horatius flaccus": "Horace",
        "quintus horatius flaccus": "Horace",
        # Ovid
        "ovidius": "Ovid",
        "p. ovidius naso": "Ovid",
        "publius ovidius naso": "Ovid",
        # Livy
        "livius": "Livy",
        "t. livius": "Livy",
        "titus livius": "Livy",
        # Pliny the Elder
        "plinius major": "Pliny the Elder",
        "c. plinius secundus": "Pliny the Elder",
        "gaius plinius secundus": "Pliny the Elder",
        # Pliny the Younger
        "plinius minor": "Pliny the Younger",
        "c. plinius caecilius secundus": "Pliny the Younger",
        # Quintilian
        "quintilianus": "Quintilian",
        "m. fabius quintilianus": "Quintilian",
        "marcus fabius quintilianus": "Quintilian",
        # Suetonius
        "suetonius": "Suetonius",
        "c. suetonius tranquillus": "Suetonius",
        "gaius suetonius tranquillus": "Suetonius",
        # Tacitus
        "tacitus": "Tacitus",
        "cornelius tacitus": "Tacitus",
        # Sallust
        "sallustius": "Sallust",
        "c. sallustius crispus": "Sallust",
        "gaius sallustius crispus": "Sallust",
        # Catullus
        "catullus": "Catullus",
        "c. valerius catullus": "Catullus",
        "gaius valerius catullus": "Catullus",
        # Lucretius
        "lucretius": "Lucretius",
        "t. lucretius carus": "Lucretius",
        "titus lucretius carus": "Lucretius",
    }

    # Work type patterns
    WORK_TYPE_PATTERNS = {
        "oratio": "Speech",
        "orationes": "Speeches",
        "epistula": "Letter",
        "epistulae": "Letters",
        "carmen": "Poem",
        "carmina": "Poems",
        "liber": "Book",
        "libri": "Books",
        "historia": "History",
        "historiae": "Histories",
        "de": "Treatise",
        " dialogues": "Dialogue",
        "dialogi": "Dialogues",
        "satira": "Satire",
        "satirae": "Satires",
        "elegia": "Elegy",
        "elegiae": "Elegies",
    }

    def normalize_author_name(self, author: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """
        Normalize an author name and return (normalized_name, standard_form).

        Returns tuple of (normalized_name, standard_form) where:
        - normalized_name: lowercase, simplified version for matching
        - standard_form: proper display name
        """
        if not author:
            return None, None

        # Clean up the author name
        author_clean = author.strip()
        author_lower = author_clean.lower()

        # Check for known variants
        if author_lower in self.AUTHOR_VARIANTS:
            standard = self.AUTHOR_VARIANTS[author_lower]
            return author_lower, standard

        # Try partial matching for common patterns
        for variant, standard in self.AUTHOR_VARIANTS.items():
            if variant in author_lower or author_lower in variant:
                return author_lower, standard

        # Return as-is if no match found
        return author_lower, author_clean

    def parse_file(self, file_path: str) -> Optional[ClassicalText]:
        """Parse a single TEI XML file and extract metadata."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Handle TEI namespace
            ns = {"tei": "http://www.tei-c.org/ns/1.0"}

            # Extract title
            title_elem = root.find(".//tei:titleStmt/tei:title", ns)
            title = (
                title_elem.text if title_elem is not None and title_elem.text else "Unknown Title"
            )

            # Extract author
            author_elem = root.find(".//tei:titleStmt/tei:author", ns)
            author_raw = author_elem.text if author_elem is not None and author_elem.text else None
            author_lower, author_standard = self.normalize_author_name(author_raw)

            # Extract language
            lang_elem = root.find(".//tei:langUsage/tei:language", ns)
            language = lang_elem.get("ident", "la") if lang_elem is not None else "la"

            # Extract publication info
            publisher_elem = root.find(".//tei:publicationStmt/tei:publisher", ns)
            publisher = publisher_elem.text if publisher_elem is not None else None

            pub_place_elem = root.find(".//tei:publicationStmt/tei:pubPlace", ns)
            pub_place = pub_place_elem.text if pub_place_elem is not None else None

            date_elem = root.find(".//tei:publicationStmt/tei:date", ns)
            pub_date = date_elem.get("when", date_elem.text) if date_elem is not None else None

            # Extract ID
            idno_elem = root.find(".//tei:publicationStmt/tei:idno", ns)
            text_id = (
                idno_elem.text if idno_elem is not None and idno_elem.text else Path(file_path).stem
            )

            # Determine source collection
            parent_dir = Path(file_path).parent.name
            source = parent_dir if parent_dir in ["digiliblt", "phi-latin", "tlg_e"] else "unknown"

            # Create full name (Author - Title)
            if author_standard:
                full_name = f"{author_standard} - {title}"
            else:
                full_name = title

            # Try to determine work type from title
            work_type = None
            title_lower = title.lower()
            for pattern, work_type_name in self.WORK_TYPE_PATTERNS.items():
                if pattern in title_lower:
                    work_type = work_type_name
                    break

            return ClassicalText(
                text_id=text_id,
                title=title,
                author=author_standard,
                author_normalized=author_lower,
                work_type=work_type,
                language=language,
                publisher=publisher,
                pub_place=pub_place,
                pub_date=pub_date,
                source=source,
                file_path=file_path,
                full_name=full_name,
            )

        except ET.ParseError as e:
            logger.error("xml_parse_error", file=file_path, error=str(e))
            return None
        except Exception as e:
            logger.error("parse_error", file=file_path, error=str(e))
            return None


class AuthTabParser:
    """Parser for PHI/TLG authtab.dir author index files.

    Format patterns observed:
    - PHI: `LAT0448 Gaius Iulius &1Caesar&Caesarl` (ID, name, alternate, language)
    - TLG: `TLG0012 &1Herodotus& Hist.` (ID, author, genre)
    - Language codes: l=Latin, g=Greek, h=Hebrew, c=Coptic
    """

    LANGUAGE_CODES = {
        "l": "la",
        "g": "grc",
        "h": "he",
        "c": "cop",
    }

    # PHI prefix to TLG namespace mapping
    PHI_PREFIX_MAP = {
        "LAT": "phi",
        "TLG": "tlg",
    }

    def parse_file(self, file_path: str) -> List[AuthorEntry]:
        """Parse an authtab.dir file and extract author entries."""
        try:
            # Parse the binary format with 0xFF delimiters
            content = self._read_binary_file(file_path)
            if not content:
                logger.warning("could_not_read", file=file_path)
                return []

            # Determine source from file path
            if "phi-latin" in file_path:
                source = "phi-latin"
            elif "tlg_e" in file_path:
                source = "tlg_e"
            else:
                source = "unknown"

            authors = self.parse_content(content, source)
            logger.info("parsed_authors", file=file_path, count=len(authors))

            return authors

        except Exception as e:
            logger.error("parse_error", file=file_path, error=str(e))
            return []

    def _read_binary_file(self, file_path: str) -> str:
        """Read binary authtab file and decode content."""
        try:
            # Read binary file
            with open(file_path, "rb") as f:
                data = f.read()

            # Split by 0xFF delimiter
            parts = data.split(b"\xff")

            # Find the header part (contains PHI or TLG)
            header_part = None
            for part in parts:
                if b"PHI" in part or b"TLG" in part:
                    header_part = part
                    break

            if not header_part:
                # Try to find part with author markers
                for part in parts:
                    if b"&1" in part:
                        header_part = part
                        break

            if not header_part:
                return ""

            # Try different encodings for the header
            for encoding in ["latin-1", "cp437", "utf-8", "iso-8859-1"]:
                try:
                    content = header_part.decode(encoding, errors="replace")
                    if "&1" in content:
                        return content
                except:
                    continue

            return header_part.decode("latin-1", errors="replace")

        except Exception as e:
            logger.error("file_read_error", file=file_path, error=str(e))
            return ""

    def get_cts_namespace(self, author_id: str) -> str:
        """Convert author ID to CTS namespace."""
        if author_id.startswith("TLG"):
            return "tlg"
        elif author_id.startswith("LAT") or author_id.startswith("PHI"):
            return "phi"
        return "unknown"

    def parse_content(self, content: str, source: str) -> List[AuthorEntry]:
        """Parse authtab content and return all author entries."""
        authors = []

        # Clean up the content - remove control characters but keep &1 markers
        content = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", content)

        # Split into lines by newlines
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for patterns like "LAT0448 Gaius Iulius &1Caesar&Caesarl"
            # or "TLG0012 &1Herodotus& Hist."
            pattern = re.compile(r"([A-Z]+)(\d+)\s+[^&]*?&1([^&]+)&([a-z]?)")
            match = pattern.search(line)

            if match:
                prefix, num, author, lang = match.groups()
                author_id = f"{prefix}{num}"

                genre = None
                lang_code = None

                if lang and lang in self.LANGUAGE_CODES:
                    lang_code = lang
                elif lang:  # Any remaining lang code might be genre info
                    # Check if it looks like a genre
                    genre_patterns = [
                        "Hist",
                        "Rhet",
                        "Phil",
                        "Trag",
                        "Epic",
                        "Lyr",
                        "Eleg",
                        "Comic",
                        "Biogr",
                        "Med",
                        "Geogr",
                        "Orat",
                        "Poet",
                        "Soph",
                        "Gramm",
                        "Theol",
                        "Myth",
                    ]
                    if lang in genre_patterns:
                        genre = lang

                if lang_code:
                    language = self.LANGUAGE_CODES.get(lang_code, "unknown")
                elif source == "phi-latin":
                    language = "la"
                elif source == "tlg_e":
                    language = "grc"
                else:
                    language = "unknown"

                authors.append(
                    AuthorEntry(
                        author_id=author_id,
                        author_name=author.strip(),
                        alternate_name=None,
                        genre=genre,
                        language=language,
                        source=source,
                    )
                )

        return authors


class CanonParser:
    """Parser for TLG canon files (doccan1.txt format).

    Format: Each entry shows ID, author, work, reference info
    Example:
        0001  �&1APOLLONIUS RHODIUS& Epic.  �(3 B.C.: Alexandrinus, Rhodius)  �...
        0001 001 �&1Argonautica&, ed. H. Fraenkel...
    """

    def parse_file(self, file_path: str) -> List[CanonEntry]:
        """Parse a canon file and extract work entries."""
        entries = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            source = "tlg_e" if "tlg_e" in file_path else "unknown"

            # Split into entries (each starts with a 4-digit ID)
            # Handle the unicode formatting character � as separator
            entry_pattern = re.compile(r"(\d{4})\s+[^\u0080-\uFFFF]+", re.DOTALL)

            for match in entry_pattern.finditer(content):
                canon_id = match.group(1)
                entry_text = match.group(0)[5:].strip()  # Remove the 4-digit ID and spaces

                # Remove unicode formatting characters
                entry_text = re.sub(r"[\u0080-\uFFFF]", "", entry_text).strip()

                if not entry_text:
                    continue

                canon = self._parse_entry(entry_text, canon_id, source)
                if canon:
                    entries.append(canon)

            logger.info("parsed_canon", file=file_path, count=len(entries))

        except Exception as e:
            logger.error("parse_error", file=file_path, error=str(e))

        return entries

    def _parse_entry(self, entry_text: str, canon_id: str, source: str) -> Optional[CanonEntry]:
        """Parse a single canon entry."""

        if not entry_text:
            return None

        # Clean up the text
        entry_text = re.sub(r"[\x00-\x1f\x7f-\x9f\u0080-\uFFFF]", "", entry_text).strip()

        # Find author name - look for &1AUTHOR& pattern
        author_match = re.search(r"&1([^&]+)&", entry_text)

        if author_match:
            author_name = author_match.group(1).strip()
        else:
            # Try to get first word as author
            parts = entry_text.split()
            if parts:
                author_name = parts[0]
            else:
                return None

        # Find work title - after the author
        if author_match:
            work_text = entry_text[author_match.end() :]
        else:
            work_text = entry_text

        # Clean up work info
        work_title = None
        reference = None
        word_count = None
        work_type = None

        # Look for work patterns in the remaining text
        # Pattern: "Title&, ed. ..." or just look for next meaningful text
        work_match = re.search(r"&1([^&]+)&", work_text)
        if work_match:
            work_title = work_match.group(1).strip()
        else:
            # Take the first substantial part as work title
            words = work_text.split()
            if words:
                # Filter out common non-title words
                meaningful_words = [
                    w
                    for w in words
                    if w.lower() not in ["ed", "ed.", "repr", "(", ")", ":", ";", ",", "cod"]
                ]
                if meaningful_words:
                    work_title = " ".join(meaningful_words[:3])  # Take first 3 words
                else:
                    work_title = words[0]

        # Look for reference patterns like "001" (work ID within author)
        ref_match = re.search(r"\b(\d{3})\s+", work_text)
        if ref_match:
            reference = ref_match.group(1)

        # Look for work type indicators
        type_patterns = [
            (" Hist", "History"),
            (" Phil", "Philosophy"),
            (" Trag", "Tragedy"),
            (" Epic", "Epic"),
            (" Lyr", "Lyric"),
            (" Eleg", "Elegy"),
            (" Comic", "Comedy"),
            (" Biogr", "Biography"),
            (" Med", "Medicine"),
            (" Geogr", "Geography"),
            (" Orat", "Oratory"),
            (" Poet", "Poetry"),
            (" Soph", "Sophist"),
            (" Gramm", "Grammar"),
            (" Theol", "Theology"),
            (" Myth", "Mythology"),
        ]

        # Search in original entry text for type indicators
        for pattern, type_name in type_patterns:
            if re.search(pattern, entry_text):
                work_type = type_name
                break

        return CanonEntry(
            canon_id=canon_id,
            author_name=author_name,
            work_title=work_title or entry_text[:50],
            reference=reference,
            word_count=word_count,
            work_type=work_type,
            source=source,
        )


class ReferenceDatabaseBuilder:
    """Builds a DuckDB database of classical texts reference data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.parser = TEIXMLParser()
        self.auth_tab_parser = AuthTabParser()
        self.canon_parser = CanonParser()
        self.texts: List[ClassicalText] = []
        self.authors: List[AuthorEntry] = []
        self.canons: List[CanonEntry] = []

    def scan_directory(self, base_path: str) -> List[ClassicalText]:
        """Scan a directory for TEI XML files and parse them."""
        logger.info("scanning_directory", path=base_path)

        all_texts = []

        # Find all XML files in the directory and subdirectories
        xml_files = glob.glob(f"{base_path}/**/*.xml", recursive=True)
        logger.info("found_xml_files", count=len(xml_files))

        for file_path in xml_files:
            text = self.parser.parse_file(file_path)
            if text:
                all_texts.append(text)
                logger.debug("parsed_text", text_id=text.text_id, title=text.title[:50])

        return all_texts

    def build_database(
        self,
        texts: List[ClassicalText],
        authors: List[AuthorEntry],
        canons: List[CanonEntry],
    ) -> None:
        """Build DuckDB database with classical texts reference data."""
        logger.info(
            "building_database",
            path=self.db_path,
            texts=len(texts),
            authors=len(authors),
            canons=len(canons),
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create texts table (from TEI XML)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS texts (
                text_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT,
                author_normalized TEXT,
                work_type TEXT,
                language TEXT,
                publisher TEXT,
                pub_place TEXT,
                pub_date TEXT,
                source TEXT,
                file_path TEXT,
                full_name TEXT
            )
        """)

        # Create author index table (from authtab.dir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS author_index (
                author_id TEXT PRIMARY KEY,
                author_name TEXT NOT NULL,
                alternate_name TEXT,
                genre TEXT,
                language TEXT,
                source TEXT,
                cts_namespace TEXT
            )
        """)

        # Create works table (from canon files)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS works (
                canon_id TEXT,
                author_name TEXT,
                work_title TEXT,
                reference TEXT,
                word_count TEXT,
                work_type TEXT,
                source TEXT,
                cts_urn TEXT,
                UNIQUE(canon_id, reference)
            )
        """)

        # Create unified search table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unified_index (
                id TEXT NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                author TEXT,
                work_title TEXT,
                language TEXT,
                source TEXT,
                cts_urn TEXT,
                PRIMARY KEY (id, type)
            )
        """)

        # Insert texts
        for text in texts:
            cursor.execute(
                """
                INSERT OR REPLACE INTO texts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    text.text_id,
                    text.title,
                    text.author,
                    text.author_normalized,
                    text.work_type,
                    text.language,
                    text.publisher,
                    text.pub_place,
                    text.pub_date,
                    text.source,
                    text.file_path,
                    text.full_name,
                ),
            )

        # Insert authors from authtab
        for author in authors:
            cts_ns = self.auth_tab_parser.get_cts_namespace(author.author_id)
            cursor.execute(
                """
                INSERT OR REPLACE INTO author_index VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    author.author_id,
                    author.author_name,
                    author.alternate_name,
                    author.genre,
                    author.language,
                    author.source,
                    cts_ns,
                ),
            )

        # Insert works from canon
        for canon in canons:
            cts_urn = None
            if canon.canon_id and canon.reference:
                # Build CTS URN: urn:cts:lang:text_id.work:reference
                cts_ns = "tlg" if canon.source == "tlg_e" else "phi"
                author_slug = re.sub(r"[^a-z]", "", canon.author_name.lower())[:8]
                cts_urn = f"urn:cts:{cts_ns}:{author_slug}.{canon.canon_id}:{canon.reference}"

            cursor.execute(
                """
                INSERT OR REPLACE INTO works VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    canon.canon_id,
                    canon.author_name,
                    canon.work_title,
                    canon.reference,
                    canon.word_count,
                    canon.work_type,
                    canon.source,
                    cts_urn,
                ),
            )

        # Build unified index - only for entries with valid id
        cursor.execute("""
            INSERT OR REPLACE INTO unified_index
            SELECT
                text_id as id,
                'text' as type,
                full_name as name,
                author,
                title as work_title,
                language,
                source,
                NULL as cts_urn
            FROM texts
            WHERE text_id IS NOT NULL AND text_id != ''
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO unified_index
            SELECT
                author_id as id,
                'author' as type,
                author_name as name,
                author_name as author,
                NULL as work_title,
                language,
                source,
                'urn:cts:' || cts_namespace || ':' || author_id as cts_urn
            FROM author_index
            WHERE author_id IS NOT NULL AND author_id != ''
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO unified_index
            SELECT
                canon_id || '-' || reference as id,
                'work' as type,
                work_title as name,
                author_name as author,
                work_title as work_title,
                'grc' as language,
                source,
                cts_urn
            FROM works
            WHERE canon_id IS NOT NULL AND canon_id != ''
                   AND reference IS NOT NULL AND reference != ''
        """)

        conn.commit()
        conn.close()

        logger.info(
            "database_built",
            texts_count=len(texts),
            authors_count=len(authors),
            works_count=len(canons),
            db_path=self.db_path,
            db_size_mb=os.path.getsize(self.db_path) / 1024 / 1024,
        )

        # Insert texts
        for text in texts:
            cursor.execute(
                """
                INSERT OR REPLACE INTO texts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    text.text_id,
                    text.title,
                    text.author,
                    text.author_normalized,
                    text.work_type,
                    text.language,
                    text.publisher,
                    text.pub_place,
                    text.pub_date,
                    text.source,
                    text.file_path,
                    text.full_name,
                ),
            )

        # Update author index
        cursor.execute("""
            INSERT OR REPLACE INTO author_index 
            SELECT author_normalized, author, COUNT(*) as text_count
            FROM texts 
            WHERE author_normalized IS NOT NULL
            GROUP BY author_normalized
        """)

        # Update source stats
        cursor.execute("""
            INSERT OR REPLACE INTO source_stats
            SELECT source, COUNT(*) as text_count
            FROM texts
            WHERE source IS NOT NULL
            GROUP BY source
        """)

        conn.commit()
        conn.close()

        logger.info(
            "database_built",
            texts_count=len(texts),
            db_path=self.db_path,
            db_size_mb=os.path.getsize(self.db_path) / 1024 / 1024,
        )

    def search_texts(self, query: str) -> List[Dict]:
        """Search the database for texts matching a query."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Search in title, author, and full_name
        search_term = f"%{query}%"
        cursor.execute(
            """
            SELECT * FROM texts 
            WHERE title LIKE ? OR author LIKE ? OR full_name LIKE ?
            ORDER BY author, title
        """,
            (search_term, search_term, search_term),
        )

        results = []
        for row in cursor.fetchall():
            columns = [
                "text_id",
                "title",
                "author",
                "author_normalized",
                "work_type",
                "language",
                "publisher",
                "pub_place",
                "pub_date",
                "source",
                "file_path",
                "full_name",
            ]
            results.append(dict(zip(columns, row)))

        conn.close()
        return results

    def get_authors(self) -> List[Dict]:
        """Get list of all authors in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM author_index ORDER BY standard_name
        """)

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "author_normalized": row[0],
                    "standard_name": row[1],
                    "text_count": row[2],
                }
            )

        conn.close()
        return results

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM texts")
        stats["total_texts"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT author) FROM texts WHERE author IS NOT NULL")
        stats["total_authors"] = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM source_stats")
        stats["by_source"] = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT author, COUNT(*) as count FROM texts 
            WHERE author IS NOT NULL 
            GROUP BY author 
            ORDER BY count DESC 
            LIMIT 5
        """)
        stats["top_authors"] = [{"author": row[0], "count": row[1]} for row in cursor.fetchall()]

        conn.close()
        return stats


def main():
    """Main function to build the reference database."""
    import argparse

    parser = argparse.ArgumentParser(description="Build classical texts reference database")
    parser.add_argument(
        "--data-dir",
        "-d",
        default="/home/nixos/Classics-Data",
        help="Base directory containing classical texts",
    )
    parser.add_argument(
        "--output", "-o", default="classical_refs.db", help="Output database file path"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(0))

    # Build the database
    builder = ReferenceDatabaseBuilder(args.output)

    # Scan TEI XML files
    all_texts = []
    for subdir in ["digiliblt", "phi-latin", "tlg_e"]:
        dir_path = Path(args.data_dir) / subdir
        if dir_path.exists():
            texts = builder.scan_directory(str(dir_path))
            all_texts.extend(texts)
            logger.info("completed_subdir", subdir=subdir, texts_count=len(texts))

    # Parse PHI authtab.dir
    all_authors = []
    phi_auth_path = Path(args.data_dir) / "phi-latin" / "authtab.dir"
    if phi_auth_path.exists():
        phi_authors = builder.auth_tab_parser.parse_file(str(phi_auth_path))
        all_authors.extend(phi_authors)
        logger.info("parsed_phi_authors", count=len(phi_authors))

    # Parse TLG authtab.dir
    tlg_auth_path = Path(args.data_dir) / "tlg_e" / "authtab.dir"
    if tlg_auth_path.exists():
        tlg_authors = builder.auth_tab_parser.parse_file(str(tlg_auth_path))
        all_authors.extend(tlg_authors)
        logger.info("parsed_tlg_authors", count=len(tlg_authors))

    # Parse TLG canon file
    all_works = []
    canon_path = Path(args.data_dir) / "tlg_e" / "doccan1.txt"
    if canon_path.exists():
        works = builder.canon_parser.parse_file(str(canon_path))
        all_works.extend(works)
        logger.info("parsed_canon_works", count=len(works))

    # Build the database
    builder.build_database(all_texts, all_authors, all_works)

    # Print statistics
    stats = builder.get_statistics()
    print("\n📊 Reference Database Statistics:")
    print(f"   Total texts: {stats['total_texts']}")
    print(f"   Total authors: {stats['total_authors']}")
    print(f"   By source:")
    for source, count in stats.get("by_source", {}).items():
        print(f"      {source}: {count} texts")
    print(f"\n📚 Top authors:")
    for author_info in stats.get("top_authors", []):
        print(f"   {author_info['author']}: {author_info['count']} texts")

    print(f"\n✅ Database saved to: {args.output}")

    # Example search
    print("\n🔍 Example searches:")
    cicero_texts = builder.search_texts("cicero")
    print(f"   Cicero texts: {len(cicero_texts)} found")
    if cicero_texts:
        for text in cicero_texts[:3]:
            print(f"      - {text['full_name'][:60]}...")

    vergil_texts = builder.search_texts("vergilius")
    print(f"   Vergil texts: {len(vergil_texts)} found")
    if vergil_texts:
        for text in vergil_texts[:3]:
            print(f"      - {text['full_name'][:60]}...")


if __name__ == "__main__":
    main()
