import logging
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import heritage_config
from .types import CanonicalResult

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
        self.session: requests.Session | None = None

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

    def build_cgi_url(
        self, script_name: str, params: dict[str, str | int | float | bool | None] | None = None
    ) -> str:
        """Build complete CGI script URL with semicolon-separated parameters"""
        base_url = self.config.base_url.rstrip("/")
        # Heritage hosts sktsearch at /cgi-bin/sktsearch (without /skt/)
        if script_name == "sktsearch" and self.config.cgi_path.rstrip("/").endswith("/skt"):
            cgi_path = self.config.cgi_path.rstrip("/").rsplit("/", 1)[0] + "/"
        else:
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
        params: dict[str, str | int | float | bool | None] | None = None,
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

    def fetch_canonical_sanskrit(
        self,
        query: str,
        timeout: int | None = None,
    ) -> CanonicalResult:
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

        # Collect all matching candidates to prefer the last one (often the base form)
        candidates = []
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if not isinstance(href, str):
                continue
            if "/skt/DICO/" in href or "/skt/MW" in href:
                # Extract the canonical part after H_
                canonical_part = ""
                if "H_" in href:
                    canonical_part = href.split("H_")[-1]
                if canonical_part:  # Only add if we found a valid canonical form
                    candidates.append(
                        {
                            "canonical_sanskrit": canonical_part,
                            "entry_url": href,
                        }
                    )

        # Prefer the last candidate (often the base form, e.g., kṛṣṇa over kṛṣṇā)
        if len(candidates) > 0:
            last = candidates[-1]
            return {
                "original_query": query,
                "bare_query": bare_query,
                "canonical_sanskrit": last["canonical_sanskrit"],
                "match_method": "sktsearch",
                "entry_url": last["entry_url"],
            }

        return {
            "original_query": query,
            "bare_query": bare_query,
            "canonical_sanskrit": None,
            "match_method": "not_found",
            "entry_url": "",
        }

    def fetch_canonical_via_sktsearch(
        self, query: str, timeout: int | None = None
    ) -> CanonicalResult:
        """Backward-compatible wrapper for canonical Sanskrit lookup via sktsearch."""
        canonical: CanonicalResult = self.fetch_canonical_sanskrit(query, timeout=timeout)

        match_method = canonical.get("match_method") or "not_found"
        entry_url = canonical.get("entry_url") or ""

        canonical_result: CanonicalResult = {
            "original_query": canonical.get("original_query", query),
            "bare_query": canonical.get("bare_query", query),
            "canonical_text": canonical.get("canonical_sanskrit"),
            "canonical_sanskrit": canonical.get("canonical_sanskrit"),
            "match_method": match_method,
            "entry_url": entry_url,
        }
        return canonical_result


class HeritageAPIError(Exception):
    """Exception raised for Heritage API errors"""

    pass
