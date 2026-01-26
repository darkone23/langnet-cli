from dataclasses import dataclass
from dotenv import load_dotenv
import os


load_dotenv()


@dataclass
class Config:
    diogenes_url: str = "http://localhost:8888/"
    log_level: str = "INFO"
    cache_enabled: bool = True
    cache_path: str = ""

    @classmethod
    def load(cls) -> "Config":
        cache_path = os.getenv("LANGNET_CACHE_PATH", "")
        return cls(
            diogenes_url=os.getenv("DIOGENES_URL", "http://localhost:8888/"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cache_enabled=os.getenv("LANGNET_CACHE_ENABLED", "true").lower() == "true",
            cache_path=cache_path if cache_path else "",
        )


def get_config() -> Config:
    return Config.load()


config = get_config()
