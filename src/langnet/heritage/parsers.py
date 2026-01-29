from typing import Dict, Any, List, Optional
import re
from bs4 import BeautifulSoup, Tag

from .client import HeritageAPIError


class HeritageHTMLParser:
    """Base HTML parser for Heritage Platform responses"""

    def __init__(self):
        self.soup = None

    def parse(self, html_content: str) -> Dict[str, Any]:
        """Parse HTML content and return structured data"""
        try:
            self.soup = BeautifulSoup(html_content, "html.parser")
            return self._parse_content()
        except Exception as e:
            raise HeritageAPIError(f"Failed to parse HTML: {e}")

    def _parse_content(self) -> Dict[str, Any]:
        """Override this method in subclasses"""
        return {
            "raw_html": str(self.soup),
            "title": self._get_title(),
            "content": self._get_main_content(),
        }

    def _get_title(self) -> Optional[str]:
        """Extract title from HTML"""
        if self.soup.title:
            return self.soup.title.string.strip()
        return None

    def _get_main_content(self) -> Optional[Tag]:
        """Extract main content area"""
        # Look for common content containers
        content_selectors = [
            "div.content",
            "div.main-content",
            "div.results",
            "div.output",
            "body",
        ]

        for selector in content_selectors:
            element = self.soup.select_one(selector)
            if element:
                return element

        return self.soup.body

    def _extract_tables(self) -> List[Dict[str, Any]]:
        """Extract all tables from HTML"""
        tables = []

        for table in self.soup.find_all("table"):
            table_data = {
                "headers": [],
                "rows": [],
                "html": str(table),
            }

            # Extract headers
            thead = table.find("thead")
            if thead:
                for th in thead.find_all("th"):
                    table_data["headers"].append(th.get_text(strip=True))

            # Extract rows
            tbody = table.find("tbody") or table
            for row in tbody.find_all("tr"):
                row_data = []
                for cell in row.find_all(["td", "th"]):
                    row_data.append(cell.get_text(strip=True))
                table_data["rows"].append(row_data)

            tables.append(table_data)

        return tables

    def _extract_links(self) -> List[Dict[str, str]]:
        """Extract all links from HTML"""
        links = []

        for link in self.soup.find_all("a", href=True):
            links.append(
                {
                    "text": link.get_text(strip=True),
                    "href": link["href"],
                    "title": link.get("title", ""),
                }
            )

        return links

    def _extract_forms(self) -> List[Dict[str, Any]]:
        """Extract all forms from HTML"""
        forms = []

        for form in self.soup.find_all("form"):
            form_data = {
                "action": form.get("action", ""),
                "method": form.get("method", "GET").upper(),
                "fields": [],
            }

            for field in form.find_all(["input", "select", "textarea"]):
                field_data = {
                    "type": field.get("type", "text"),
                    "name": field.get("name", ""),
                    "value": field.get("value", ""),
                    "label": self._get_field_label(field),
                }

                if field.name == "select":
                    field_data["options"] = [
                        opt.get("value", opt.get_text(strip=True))
                        for opt in field.find_all("option")
                    ]

                form_data["fields"].append(field_data)

            forms.append(form_data)

        return forms

    def _get_field_label(self, field: Tag) -> str:
        """Get label for a form field"""
        # Look for label with 'for' attribute
        if field.get("id"):
            label = self.soup.find("label", {"for": field["id"]})
            if label:
                return label.get_text(strip=True)

        # Look for label as previous sibling
        prev = field.previous_sibling
        while prev:
            if prev.name == "label":
                return prev.get_text(strip=True)
            prev = prev.previous_sibling

        return ""

    def _extract_text_content(self) -> str:
        """Extract all text content from HTML"""
        return self.soup.get_text(separator=" ", strip=True)


class MorphologyParser(HeritageHTMLParser):
    """Parser for morphological analysis responses (sktreader)"""

    def _parse_content(self) -> Dict[str, Any]:
        """Parse morphology analysis results"""
        base_data = super()._parse_content()

        # Look for solution tables
        solutions = []
        tables = self._extract_tables()

        for table in tables:
            if self._is_solution_table(table):
                solution = self._parse_solution_table(table)
                if solution:
                    solutions.append(solution)

        # Look for word-by-word analysis
        word_analyses = self._parse_word_analyses()

        return {
            **base_data,
            "solutions": solutions,
            "word_analyses": word_analyses,
            "total_solutions": len(solutions),
        }

    def _is_solution_table(self, table: Dict[str, Any]) -> bool:
        """Check if table contains morphological solutions"""
        # Look for common patterns in solution tables
        headers = table["headers"]
        rows = table["rows"]

        # Check if headers suggest morphological analysis
        morphological_indicators = ["word", "lemma", "root", "pos", "case", "gender", "number"]

        if not headers:
            # If no headers, check row content
            for row in rows[:2]:  # Check first few rows
                if row and any(
                    indicator in str(row).lower() for indicator in morphological_indicators
                ):
                    return True

        # Check headers
        if headers:
            flat_headers = " ".join(headers).lower()
            return any(indicator in flat_headers for indicator in morphological_indicators)

        return False

    def _parse_solution_table(self, table: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single solution table"""
        if not table["rows"]:
            return None

        headers = table["headers"]
        rows = table["rows"]

        solution = {
            "type": "morphological_analysis",
            "headers": headers,
            "entries": [],
        }

        for row in rows:
            entry = {}

            # Map headers to values
            for i, header in enumerate(headers):
                if i < len(row):
                    entry[header.lower()] = row[i]

            solution["entries"].append(entry)

        return solution

    def _parse_word_analyses(self) -> List[Dict[str, Any]]:
        """Parse word-by-word analysis from HTML"""
        analyses = []

        # Look for specific patterns in HTML
        # This is a simplified parser - actual implementation will depend on HTML structure

        # Look for divs with word analysis classes
        analysis_divs = self.soup.find_all("div", class_=re.compile(r"word|analysis|solution"))

        for div in analysis_divs:
            analysis = {
                "word": div.get_text(strip=True),
                "analyses": [],
            }

            # Extract sub-analyses
            sub_elements = div.find_all(["div", "span", "li"])
            for elem in sub_elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 1:  # Avoid empty or single character strings
                    analysis["analyses"].append(text)

            if analysis["analyses"]:
                analyses.append(analysis)

        return analyses


class DictionaryParser(HeritageHTMLParser):
    """Parser for dictionary search responses (sktsearch/sktindex)"""

    def _parse_content(self) -> Dict[str, Any]:
        """Parse dictionary search results"""
        base_data = super()._parse_content()

        # Look for dictionary entries
        entries = self._parse_dictionary_entries()

        # Look for pagination
        pagination = self._parse_pagination()

        return {
            **base_data,
            "entries": entries,
            "pagination": pagination,
            "total_entries": len(entries),
        }

    def _parse_dictionary_entries(self) -> List[Dict[str, Any]]:
        """Parse dictionary entries from HTML"""
        entries = []

        # Look for entry containers
        entry_selectors = [
            "div.entry",
            "div.dict-entry",
            "div.result",
            "div.item",
        ]

        for selector in entry_selectors:
            elements = self.soup.select(selector)
            for element in elements:
                entry = self._parse_single_entry(element)
                if entry:
                    entries.append(entry)

        # If no structured entries found, try text-based parsing
        if not entries:
            entries = self._parse_text_entries()

        return entries

    def _parse_single_entry(self, element: Tag) -> Optional[Dict[str, Any]]:
        """Parse a single dictionary entry"""
        entry = {
            "headword": "",
            "definitions": [],
            "etymology": "",
            "references": [],
        }

        # Extract headword (usually first bold or strong element)
        headword_elem = element.find(["b", "strong", "h3", "h4"])
        if headword_elem:
            entry["headword"] = headword_elem.get_text(strip=True)

        # Extract definitions
        definition_elems = element.find_all(["p", "div"], class_=re.compile(r"def|sense|meaning"))
        for elem in definition_elems:
            text = elem.get_text(strip=True)
            if text and len(text) > 10:  # Avoid short fragments
                entry["definitions"].append(text)

        # Extract etymology
        etymology_elems = element.find_all(text=re.compile(r"etym|root|origin", re.IGNORECASE))
        for elem in etymology_elems:
            etymology = elem.get_text(strip=True)
            if etymology and len(etymology) > 5:
                entry["etymology"] = etymology
                break

        return entry if entry["headword"] else None

    def _parse_text_entries(self) -> List[Dict[str, Any]]:
        """Parse entries from plain text content"""
        entries = []

        # Simple pattern matching for dictionary entries
        # This is a basic implementation - will need refinement
        lines = self.soup.get_text("\n").split("\n")

        current_entry = {}
        in_entry = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for headword patterns
            if len(line) < 100 and not line.endswith(".") and not line.endswith(","):
                # Potential headword
                if current_entry and "headword" in current_entry:
                    # Save previous entry
                    entries.append(current_entry)

                current_entry = {
                    "headword": line,
                    "definitions": [],
                }
                in_entry = True
            elif in_entry and line:
                # Definition or additional info
                current_entry["definitions"].append(line)

        # Add last entry
        if current_entry and "headword" in current_entry:
            entries.append(current_entry)

        return entries

    def _parse_pagination(self) -> Optional[Dict[str, Any]]:
        """Parse pagination information"""
        pagination = {}

        # Look for pagination links
        pagination_links = self.soup.find_all("a", string=re.compile(r"next|prev|first|last"))

        if pagination_links:
            pagination["has_next"] = any(
                "next" in link.get_text().lower() for link in pagination_links
            )
            pagination["has_prev"] = any(
                "prev" in link.get_text().lower() for link in pagination_links
            )

        return pagination or None
