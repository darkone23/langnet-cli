from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class HeritageConfig:
    """Configuration for Heritage Platform backend."""

    base_url: str = "http://localhost:48080"
    cgi_path: str = "/cgi-bin/skt/"
    timeout: int = 30
    verbose: bool = False

    @classmethod
    def from_env(cls) -> HeritageConfig:
        return cls(
            base_url=os.getenv("HERITAGE_BASE_URL", "http://localhost:48080"),
            cgi_path=os.getenv("HERITAGE_CGI_PATH", "/cgi-bin/skt/"),
            timeout=int(os.getenv("HERITAGE_TIMEOUT", "30")),
            verbose=os.getenv("HERITAGE_VERBOSE", "false").lower() == "true",
        )


heritage_config = HeritageConfig.from_env()
