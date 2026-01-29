import json
import time
from typing import Dict, Any, Optional, Union
from urllib.parse import urljoin, urlencode

import requests
import structlog
from bs4 import BeautifulSoup

from .config import heritage_config

logger = structlog.get_logger(__name__)


class HeritageHTTPClient:
    """HTTP client for Heritage Platform CGI scripts"""

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

    def build_cgi_url(self, script_name: str, params: Optional[Dict[str, Any]] = None) -> str:
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
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        timeout: Optional[int] = None,
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
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch response and parse as JSON"""
        html_content = self.fetch_cgi_script(script_name, params, method, timeout)
        return self.parse_html_to_json(html_content)

    def parse_html_to_json(self, html_content: str) -> Dict[str, Any]:
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


class HeritageAPIError(Exception):
    """Exception raised for Heritage API errors"""

    pass
