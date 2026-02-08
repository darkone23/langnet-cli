from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

load_dotenv()


class Environment(str, Enum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"

    @classmethod
    def from_env(cls, value: str | None) -> "Environment":
        if not value:
            return cls.DEV
        normalized = value.lower()
        for env in cls:
            if env.value == normalized:
                return env
        return cls.DEV


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _coerce_timeout(raw: str | None, default: int) -> int:
    if raw is None:
        return default
    try:
        timeout = int(raw)
    except ValueError as exc:  # noqa: BLE001
        raise ValueError(f"Invalid timeout value: {raw}") from exc
    if timeout <= 0:
        raise ValueError("Timeout must be a positive integer")
    return timeout


@dataclass(frozen=True)
class LangnetSettings:
    """Validated, single-source settings for langnet."""

    env: Environment
    diogenes_url: str
    log_level: str
    cdsl_dict_dir: Path
    cdsl_db_dir: Path
    heritage_url: str
    http_timeout: int
    enable_normalization: bool = True
    warmup_backends: bool = True

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "LangnetSettings":
        environment = Environment.from_env(env.get("LANGNET_ENV"))
        diogenes_url = env.get("DIOGENES_URL", "http://localhost:8888/")
        heritage_url = env.get("HERITAGE_URL", "http://localhost:48080")
        log_level = env.get("LOG_LEVEL") or env.get("LANGNET_LOG_LEVEL") or "INFO"
        cdsl_dict_dir = Path(env.get("CDSL_DICT_DIR") or (Path.home() / "cdsl_data" / "dict"))
        cdsl_db_dir = Path(env.get("CDSL_DB_DIR") or (Path.home() / "cdsl_data" / "db"))
        http_timeout = _coerce_timeout(env.get("HTTP_TIMEOUT"), default=30)
        enable_normalization = _parse_bool(
            env.get("LANGNET_ENABLE_NORMALIZATION"), default=True
        )
        warmup_default = environment != Environment.TEST
        warmup_backends = _parse_bool(env.get("LANGNET_WARMUP_BACKENDS"), warmup_default)

        settings = cls(
            env=environment,
            diogenes_url=diogenes_url,
            log_level=log_level,
            cdsl_dict_dir=cdsl_dict_dir,
            cdsl_db_dir=cdsl_db_dir,
            heritage_url=heritage_url,
            http_timeout=http_timeout,
            enable_normalization=enable_normalization,
            warmup_backends=warmup_backends,
        )
        settings._validate()
        return settings

    def _validate(self) -> None:
        if not self.diogenes_url:
            raise ValueError("DIOGENES_URL must not be empty")
        if not self.heritage_url:
            raise ValueError("HERITAGE_URL must not be empty")
        if self.http_timeout <= 0:
            raise ValueError("HTTP_TIMEOUT must be positive")

    @property
    def log_level_value(self) -> int:
        import logging  # delayed import to avoid configuration at module load

        return getattr(logging, self.log_level.upper(), logging.INFO)


_settings_cache: LangnetSettings | None = None


def load_settings(env: Mapping[str, str] | None = None) -> LangnetSettings:
    env_data = dict(os.environ)
    if env:
        env_data.update(env)
    return LangnetSettings.from_env(env_data)


def get_settings(env_override: Mapping[str, str] | None = None) -> LangnetSettings:
    global _settings_cache
    if env_override is None:
        if _settings_cache is None:
            _settings_cache = load_settings()
        return _settings_cache
    return load_settings(env_override)


settings = get_settings()
# Backwards compatibility alias for legacy imports
config = settings
