import os
from dataclasses import dataclass


@dataclass
class HeritageConfig:
    """Configuration for Heritage Platform backend"""

    # Base URL for Heritage Platform
    base_url: str = "http://localhost:48080"

    # CGI script path
    cgi_path: str = "/cgi-bin/skt/"

    # Request timeout in seconds
    timeout: int = 30

    # Enable caching of responses
    caching_enabled: bool = True

    # Cache TTL in seconds
    cache_ttl: int = 3600

    # Enable verbose logging
    verbose: bool = False

    # Default encoding for text (Velthuis for Sanskrit)
    default_encoding: str = "velthuis"

    # Maximum number of solutions to return
    max_solutions: int = 10

    # Enable fallback to simple search
    enable_fallback: bool = True

    @classmethod
    def load_from_env(cls) -> "HeritageConfig":
        """Load configuration from environment variables"""
        return cls(
            base_url=os.getenv("HERITAGE_BASE_URL", "http://localhost:48080"),
            cgi_path=os.getenv("HERITAGE_CGI_PATH", "/cgi-bin/skt/"),
            timeout=int(os.getenv("HERITAGE_TIMEOUT", "30")),
            caching_enabled=os.getenv("HERITAGE_CACHING_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("HERITAGE_CACHE_TTL", "3600")),
            verbose=os.getenv("HERITAGE_VERBOSE", "false").lower() == "true",
            default_encoding=os.getenv("HERITAGE_ENCODING", "velthuis"),
            max_solutions=int(os.getenv("HERITAGE_MAX_SOLUTIONS", "10")),
            enable_fallback=os.getenv("HERITAGE_ENABLE_FALLBACK", "true").lower() == "true",
        )


# Global configuration instance
heritage_config = HeritageConfig.load_from_env()
