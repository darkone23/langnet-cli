from __future__ import annotations

import importlib
import logging
from collections.abc import Callable, Iterable

logger = logging.getLogger(__name__)


class CLTKService:
    """
    Lazy-loading wrapper for CLTK NLP pipelines.

    Uses a singleton-style cache per language to avoid repeated warmups.
    """

    def __init__(self, loader: Callable[[str], object] | None = None) -> None:
        self._loader = loader or self._default_loader
        self._instances: dict[str, object] = {}

    def get_pipeline(self, language: str) -> object | None:
        if language not in self._instances:
            self._instances[language] = self._loader(language)
        return self._instances.get(language)

    def warm_up(self, languages: Iterable[str]) -> None:
        for lang in languages:
            self.get_pipeline(lang)

    def _default_loader(self, language: str) -> object | None:
        try:
            cltk_module = importlib.import_module("cltk")
            nlp_class = getattr(cltk_module, "NLP")
            return nlp_class(language=language, suppress_banner=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "cltk_pipeline_unavailable", extra={"language": language, "error": str(exc)}
            )
            return None
