import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    diogenes_url: str = "http://localhost:8888/"
    log_level: str = "INFO"
    cache_enabled: bool = True
    cache_path: str = ""
    cdsl_dict_dir: Path = field(default_factory=lambda: Path.home() / "cdsl_data" / "dict")
    cdsl_db_dir: Path = field(default_factory=lambda: Path.home() / "cdsl_data" / "db")

    @classmethod
    def load(cls) -> "Config":
        cache_path = os.getenv("LANGNET_CACHE_PATH", "")
        cdsl_dict = os.getenv("CDSL_DICT_DIR", "")
        cdsl_db = os.getenv("CDSL_DB_DIR", "")
        return cls(
            diogenes_url=os.getenv("DIOGENES_URL", "http://localhost:8888/"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cache_enabled=os.getenv("LANGNET_CACHE_ENABLED", "true").lower() == "true",
            cache_path=cache_path if cache_path else "",
            cdsl_dict_dir=Path(cdsl_dict) if cdsl_dict else Path.home() / "cdsl_data" / "dict",
            cdsl_db_dir=Path(cdsl_db) if cdsl_db else Path.home() / "cdsl_data" / "db",
        )


def get_config() -> Config:
    return Config.load()


config = get_config()
