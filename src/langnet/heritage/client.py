import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from indic_transliteration.sanscript import DEVANAGARI, IAST, transliterate

from .config import heritage_config
from .parameters import HeritageParameterBuilder

logger = logging.getLogger(__name__)


class HeritageHTTPClient:
    """HTTP client for Heritage Platform CGI scripts"""

    # Constants for parsing
    MIN_TEXT_LENGTH = 10
    MIN_CELLS_COUNT = 2

    def __init__(self, config=None):
        self.config = config or heritage_config
        self.last_request_time = 0
        self.min_request_delay = 0.1  # 100ms between requests to avoid overwhelming

    def __enter__(self):
        """Context manager entry - no-op for now"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no-op for now"""
        pass

    def _rate_limit(self):
        """Apply rate limiting to avoid overwhelming the CGI server"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_delay:
            time.sleep(self.min_request_delay - time_since_last)
        self.last_request_time = time.time()

    def build_cgi_url(self, script_name: str, params: dict[str, Any] | None = None) -> str:
        """Build complete CGI script URL with semicolon-separated parameters"""
        base_url = self.config.base_url.rstrip("/")
        cgi_path = self.config.cgi_path.rstrip("/") + "/"
        url = urljoin(base_url, cgi_path + script_name)

        if params:
            # Filter out None values
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                # Use semicolon separation instead of ampersand for Heritage CGI
                param_string = ";".join([f"{k}={v}" for k, v in filtered_params.items()])
                url += "?" + param_string

        return url

    def fetch_cgi_script(
        self,
        script_name: str,
        params: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> str:
        """Fetch response from CGI script"""

        url = self.build_cgi_url(script_name, params)
        request_timeout = timeout or self.config.timeout

        if self.config.verbose:
            logger.info(
                f"Fetching CGI script - script: {script_name}, url: {url}, params: {params}"
            )

        self._rate_limit()

        try:
            response = requests.get(url, timeout=request_timeout)
            response.raise_for_status()
            content = response.text

            if self.config.verbose:
                status = response.status_code
                content_len = len(content)
                logger.info(
                    f"CGI script response - script: {script_name}, "
                    f"status: {status}, length: {content_len}"
                )

            return content

        except requests.RequestException as e:
            logger.error(f"HTTP request failed - script: {script_name}, error: {str(e)}")
            raise HeritageAPIError(f"HTTP request failed for {script_name}: {e}")

        except Exception as e:
            logger.error(
                f"Unexpected error fetching CGI script - script: {script_name}, error: {str(e)}"
            )
            raise HeritageAPIError(f"Unexpected error for {script_name}: {e}")

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

            # Look for the main lemmatization result
            # The structure is: <span class="red">yogena</span> lemmatizes as:<br>[<a href="..."><i>yoga</i></a>]{m. sg. i.}
            red_span = soup.find("span", class_="red")

            if red_span:
                inflected_form = red_span.get_text(strip=True)

                # Look for the lemma in navy links
                navy_link = soup.find("a", class_="navy")
                if navy_link:
                    # Get the lemma from the <i> tag inside the link
                    lemma_tag = navy_link.find("i")
                    lemma = (
                        lemma_tag.get_text(strip=True)
                        if lemma_tag
                        else navy_link.get_text(strip=True)
                    )

                    # Extract grammatical info from the text after the link
                    # The pattern is: [link]{grammatical info}
                    # We need to find the text containing {...}
                    navy_link_parent = navy_link.parent
                    grammar = ""
                    if navy_link_parent:
                        parent_text = navy_link_parent.get_text()
                        # Extract everything between {} after the link
                        import re

                        grammar_match = re.search(r"\{(.+?)\}", parent_text)
                        if grammar_match:
                            grammar = grammar_match.group(1)

                    lemmas.append(
                        {"inflected_form": inflected_form, "lemma": lemma, "grammar": grammar}
                    )

            if not lemmas:
                # If no structured data found, return minimal diagnostic info
                return {
                    "inflected_form": None,
                    "lemma": None,
                    "message": "No structured lemmatization data found",
                }

            return {
                "inflected_form": lemmas[0]["inflected_form"] if lemmas else None,
                "lemma": lemmas[0]["lemma"] if lemmas else None,
                "grammar": lemmas[0].get("grammar", "") if lemmas else "",
                "all_lemmas": lemmas,
            }

        except Exception as e:
            logger.error(f"Failed to parse lemmatization response - error: {str(e)}")
            raise HeritageAPIError(f"Lemmatization parsing failed: {e}")

    def fetch_canonical_sanskrit(
        self,
        query: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Fetch canonical Sanskrit form from sktsearch.

        Uses Heritage's sktsearch CGI to get the canonical Devanagari
        representation of a term, which handles encoding robustly.
        """
        bare_query = re.sub(r"[^a-z]", "", query.lower())

        params = {
            "q": bare_query,
            "lex": "SH",
        }

        html_content = self.fetch_cgi_script("sktsearch", params=params, timeout=timeout)
        soup = BeautifulSoup(html_content, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if not isinstance(href, str):
                continue
            if "/skt/DICO/" in href or "/skt/MW" in href:
                link_text = link.get_text(strip=True)
                # NB: this only returns the first when there are likely multiple
                # potential_devanagari = transliterate(link_text, IAST, DEVANAGARI)
                # Extract the canonical part after H_
                canonical_part = ""
                if "H_" in href:
                    canonical_part = href.split("H_")[-1]
                elif "#" in href:
                    canonical_part = href.split("#")[-1]
                return {
                    "original_query": query,
                    "bare_query": bare_query,
                    "canonical_sanskrit": canonical_part,
                    "match_method": "sktsearch",
                    "entry_url": href,
                }

        return {
            "original_query": query,
            "bare_query": bare_query,
            "canonical_sanskrit": None,
            "match_method": "not_found",
        }


class HeritageAPIError(Exception):
    """Exception raised for Heritage API errors"""

    pass
