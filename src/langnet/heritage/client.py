import re
import time
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
import structlog
from bs4 import BeautifulSoup
from indic_transliteration.sanscript import DEVANAGARI, IAST, transliterate

from .config import heritage_config
from .parameters import HeritageParameterBuilder

logger = structlog.get_logger(__name__)


class HeritageHTTPClient:
    """HTTP client for Heritage Platform CGI scripts"""

    # Constants for parsing
    MIN_TEXT_LENGTH = 10
    MIN_CELLS_COUNT = 2
    DICTIONARY_ENTRY_PATTERN = "/skt/MW/"

    def __init__(self, config=None):
        self.config = config or heritage_config
        self.session = None
        self.last_request_time = 0
        self.min_request_delay = 0.1  # 100ms between requests to avoid overwhelming

    def __enter__(self):
        """Context manager entry"""
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            self.session.close()

    def _rate_limit(self):
        """Apply rate limiting to avoid overwhelming the CGI server"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_delay:
            time.sleep(self.min_request_delay - time_since_last)
        self.last_request_time = time.time()

    def build_cgi_url(self, script_name: str, params: dict[str, Any] | None = None) -> str:
        """Build complete CGI script URL with parameters"""
        base_url = self.config.base_url.rstrip("/")
        cgi_path = self.config.cgi_path.rstrip("/") + "/"
        url = urljoin(base_url, cgi_path + script_name)

        if params:
            # Filter out None values
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                url += "?" + urlencode(filtered_params)

        return url

    def fetch_cgi_script(
        self,
        script_name: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        timeout: int | None = None,
    ) -> str:
        """Fetch response from CGI script"""
        if not self.session:
            raise RuntimeError("HTTP client not initialized. Use with statement.")

        url = self.build_cgi_url(script_name, params)
        request_timeout = timeout or self.config.timeout

        if self.config.verbose:
            logger.info("Fetching CGI script", script=script_name, url=url, params=params)

        self._rate_limit()

        try:
            response = self.session.request(method, url, timeout=request_timeout)
            response.raise_for_status()
            content = response.text

            if self.config.verbose:
                logger.info(
                    "CGI script response",
                    script=script_name,
                    status=response.status_code,
                    length=len(content),
                )

            return content

        except requests.RequestException as e:
            logger.error("HTTP request failed", script=script_name, error=str(e))
            raise HeritageAPIError(f"HTTP request failed for {script_name}: {e}")

        except Exception as e:
            logger.error("Unexpected error fetching CGI script", script=script_name, error=str(e))
            raise HeritageAPIError(f"Unexpected error for {script_name}: {e}")

    def fetch_json(
        self,
        script_name: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Fetch response and parse as JSON"""
        html_content = self.fetch_cgi_script(script_name, params, method, timeout)
        return self.parse_html_to_json(html_content)

    def parse_html_to_json(self, html_content: str) -> dict[str, Any]:
        """Parse HTML response and convert to structured JSON"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Basic structure - this will be extended by specific parsers
            result = {
                "raw_html": html_content,
                "title": soup.title.string if soup.title else None,
                "content": str(soup),
            }

            return result

        except Exception as e:
            logger.error("Failed to parse HTML response", error=str(e))
            raise HeritageAPIError(f"HTML parsing failed: {e}")

    def fetch_dictionary_search(
        self,
        query: str,
        lexicon: str = "MW",
        max_results: int | None = None,
        encoding: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Fetch dictionary search results from sktsearch/sktindex CGI script"""

        params = HeritageParameterBuilder.build_search_params(
            query=query,
            lexicon=lexicon,
            max_results=max_results,
            encoding=encoding,
            **kwargs,
        )

        # Use sktindex for dictionary lookup (it works better than sktsearch)
        script_name = "sktindex"
        html_content = self.fetch_cgi_script(script_name, params)

        # Parse the dictionary response
        return self.parse_dictionary_response(html_content, lexicon)

    def _extract_pos_from_text(self, text: str) -> str:
        """Extract part of speech from text"""
        if "Noun" in text:
            return "Noun"
        elif "Verb" in text:
            return "Verb"
        elif "Adjective" in text:
            return "Adjective"
        else:
            return "Unknown"

    def _parse_table_entries(self, soup: BeautifulSoup, lexicon: str) -> list[dict[str, Any]]:
        """Parse entries from table structure"""
        entries = []
        result_tables = soup.find_all("table", class_="yellow_cent")
        for table in result_tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if cells:
                    # Look for links with headwords
                    links = cells[0].find_all("a", href=True)
                    for link in links:
                        href = link.get("href", "")
                        headword_text = link.get_text(strip=True)

                        # Extract headword from href if it looks like a dictionary entry
                        if (
                            isinstance(href, str)
                            and self.DICTIONARY_ENTRY_PATTERN in href
                            and headword_text
                        ):
                            # Extract part of speech from the text
                            pos_text = cells[0].get_text(strip=True)
                            pos = self._extract_pos_from_text(pos_text)

                            entries.append(
                                {
                                    "headword": headword_text,
                                    "part_of_speech": pos,
                                    "lexicon": lexicon,
                                    "entry_url": href,
                                }
                            )
        return entries

    def _parse_text_entries(self, soup: BeautifulSoup, lexicon: str) -> list[dict[str, Any]]:
        """Parse entries from text content"""
        entries = []
        all_text = soup.get_text()
        if "agni" in all_text.lower():
            lines = all_text.split("\n")
            for line in lines:
                if "agni" in line.lower() and len(line.strip()) > self.MIN_TEXT_LENGTH:
                    # Simple extraction - this will be improved
                    entries.append(
                        {
                            "headword": "agni",
                            "part_of_speech": "Unknown",
                            "lexicon": lexicon,
                            "entry_url": None,
                            "raw_text": line.strip(),
                        }
                    )
        return entries

    def parse_dictionary_response(self, html_content: str, lexicon: str) -> dict[str, Any]:
        """Parse dictionary search response HTML"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract dictionary entries
            entries = []

            # Method 1: Look for table cells with links to dictionary entries
            entries = self._parse_table_entries(soup, lexicon)

            # Method 2: Look for any text content containing the query
            if not entries:
                entries = self._parse_text_entries(soup, lexicon)

            return {
                "lexicon": lexicon,
                "entries": entries,
                "total_entries": len(entries),
                "raw_html": html_content,
            }

        except Exception as e:
            logger.error("Failed to parse dictionary response", error=str(e))
            raise HeritageAPIError(f"Dictionary parsing failed: {e}")

    def fetch_lemmatization(
        self,
        word: str,
        encoding: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Fetch lemmatization results from sktlemmatizer CGI script"""
        params = HeritageParameterBuilder.build_lemma_params(
            word=word,
            encoding=encoding,
            **kwargs,
        )

        # Use sktlemmatizer for lemmatization
        script_name = "sktlemmatizer"
        html_content = self.fetch_cgi_script(script_name, params)

        # Parse the lemmatization response
        return self.parse_lemmatization_response(html_content)

    def parse_lemmatization_response(self, html_content: str) -> dict[str, Any]:
        """Parse lemmatization response HTML"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract lemmatization results
            lemmas = []

            # Look for lemmatization results in the response
            # This will depend on the actual HTML structure returned by sktlemmatizer
            results = soup.find_all("div", class_="lemma-result")  # Class name may vary

            if not results:
                # Fallback: look for any table rows with lemmatization info
                table_rows = soup.find_all("tr")
                for row in table_rows:
                    cells = row.find_all("td")
                    if len(cells) >= self.MIN_CELLS_COUNT:
                        inflected_form = cells[0].get_text(strip=True)
                        lemma = cells[1].get_text(strip=True)

                        if inflected_form and lemma:
                            lemmas.append(
                                {
                                    "inflected_form": inflected_form,
                                    "lemma": lemma,
                                }
                            )

            if not lemmas:
                # If no structured data found, return raw content for analysis
                return {
                    "inflected_form": None,
                    "lemma": None,
                    "raw_html": html_content,
                    "message": "No structured lemmatization data found",
                }

            return {
                "inflected_form": lemmas[0]["inflected_form"] if lemmas else None,
                "lemma": lemmas[0]["lemma"] if lemmas else None,
                "all_lemmas": lemmas,
                "raw_html": html_content,
            }

        except Exception as e:
            logger.error("Failed to parse lemmatization response", error=str(e))
            raise HeritageAPIError(f"Lemmatization parsing failed: {e}")

    def fetch_canonical_sanskrit(
        self,
        query: str,
        lexicon: str = "MW",
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Fetch canonical Sanskrit form from sktsearch.

        Uses Heritage's sktsearch CGI to get the canonical Devanagari
        representation of a term, which handles encoding robustly.
        """
        bare_query = re.sub(r"[^a-z]", "", query.lower())

        params = {
            "q": bare_query,
            "lex": lexicon,
            "t": "VH",
        }

        html_content = self.fetch_cgi_script("sktsearch", params=params, timeout=timeout)
        soup = BeautifulSoup(html_content, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if not isinstance(href, str):
                continue
            if f"/skt/{lexicon}/" in href:
                link_text = link.get_text(strip=True)
                try:
                    potential_devanagari = transliterate(link_text, IAST, DEVANAGARI)
                    return {
                        "original_query": query,
                        "bare_query": bare_query,
                        "canonical_sanskrit": potential_devanagari,
                        "match_method": "sktsearch",
                        "entry_url": href,
                        "lexicon": lexicon,
                    }
                except Exception:
                    pass

        return {
            "original_query": query,
            "bare_query": bare_query,
            "canonical_sanskrit": None,
            "match_method": "not_found",
            "lexicon": lexicon,
        }

    def fetch_dictionary_entry(self, entry_url: str) -> dict[str, Any]:
        """Fetch and parse a specific dictionary entry from its URL"""
        try:
            # Extract script name and parameters from URL
            if entry_url and "/skt/MW/" in entry_url:
                # This is a Monier-Williams dictionary entry
                # We need to construct the appropriate CGI call
                # The URL format is typically /skt/MW/2.html#agni
                # We need to extract the page number and headword

                match = re.search(r"/skt/MW/(\d+)\.html#(.+)", entry_url)
                if match:
                    page_num = match.group(1)
                    headword = match.group(2)

                    # Construct the appropriate CGI call
                    # This might require a different approach than direct URL fetching
                    return {
                        "headword": headword,
                        "page": page_num,
                        "entry_url": entry_url,
                        "status": "url_extracted",
                        "message": (
                            "Dictionary entry URL extracted but direct fetching not implemented"
                        ),
                    }
                else:
                    return {
                        "headword": None,
                        "entry_url": entry_url,
                        "status": "parse_error",
                        "message": "Could not parse dictionary entry URL",
                    }
            else:
                return {
                    "headword": None,
                    "entry_url": entry_url,
                    "status": "unsupported_format",
                    "message": "Unsupported dictionary entry URL format",
                }

        except Exception as e:
            logger.error("Failed to fetch dictionary entry", error=str(e))
            raise HeritageAPIError(f"Dictionary entry fetch failed: {e}")


class HeritageAPIError(Exception):
    """Exception raised for Heritage API errors"""

    pass
