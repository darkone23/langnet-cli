from dataclasses import dataclass
from dotenv import load_dotenv
import os


load_dotenv()


@dataclass
class Config:
    diogenes_url: str = "http://localhost:8888/"
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "Config":
        return cls(
            diogenes_url=os.getenv("DIOGENES_URL", "http://localhost:8888/"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def get_config() -> Config:
    return Config.load()


config = get_config()
