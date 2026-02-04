import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    diogenes_url: str = "http://localhost:8888/"
    log_level: str = "INFO"
    cdsl_dict_dir: Path = field(default_factory=lambda: Path.home() / "cdsl_data" / "dict")
    cdsl_db_dir: Path = field(default_factory=lambda: Path.home() / "cdsl_data" / "db")
    heritage_url: str = os.getenv("HERITAGE_URL", "http://localhost:48080")
    http_timeout: int = 30

    @classmethod
    def load(cls) -> "Config":
        cdsl_dict = os.getenv("CDSL_DICT_DIR", "")
        cdsl_db = os.getenv("CDSL_DB_DIR", "")
        return cls(
            diogenes_url=os.getenv("DIOGENES_URL", "http://localhost:8888/"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cdsl_dict_dir=Path(cdsl_dict) if cdsl_dict else Path.home() / "cdsl_data" / "dict",
            cdsl_db_dir=Path(cdsl_db) if cdsl_db else Path.home() / "cdsl_data" / "db",
            heritage_url=Config.heritage_url,
            http_timeout=int(os.getenv("HTTP_TIMEOUT", "30")),
        )


def get_config() -> Config:
    return Config.load()


config = get_config()
