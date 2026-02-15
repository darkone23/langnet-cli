from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.config import LangnetSettings, get_settings
from langnet.diogenes.core import DiogenesScraper
from langnet.engine.core import LanguageEngine, LanguageEngineConfig
from langnet.engine.sanskrit_normalizer import SanskritQueryNormalizer
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.config import HeritageConfig
from langnet.heritage.morphology import HeritageMorphologyService
from langnet.normalization import NormalizationPipeline
from langnet.whitakers_words.core import WhitakersWords

logger = structlog.get_logger(__name__)


def _default_diogenes_factory(settings: LangnetSettings) -> DiogenesScraper:
    return DiogenesScraper(base_url=settings.diogenes_url)


def _default_whitakers_factory(settings: LangnetSettings) -> WhitakersWords:
    return WhitakersWords()


def _default_cltk_factory(settings: LangnetSettings) -> ClassicsToolkit:
    return ClassicsToolkit()


def _default_cdsl_factory(settings: LangnetSettings) -> SanskritCologneLexicon:
    return SanskritCologneLexicon()


def _default_heritage_client_factory(settings: LangnetSettings) -> HeritageHTTPClient:
    heritage_config = HeritageConfig(
        base_url=settings.heritage_url,
        timeout=settings.http_timeout,
    )
    return HeritageHTTPClient(config=heritage_config)


def _default_heritage_morphology_factory(settings: LangnetSettings) -> HeritageMorphologyService:
    heritage_config = HeritageConfig(
        base_url=settings.heritage_url,
        timeout=settings.http_timeout,
    )
    return HeritageMorphologyService(heritage_config)


def _default_normalization_factory(settings: LangnetSettings) -> NormalizationPipeline | None:
    if not settings.enable_normalization:
        return None
    return NormalizationPipeline()


def _default_sanskrit_normalizer_factory(
    settings: LangnetSettings,
    heritage_client: HeritageHTTPClient | None,
    normalization_pipeline: NormalizationPipeline | None,
) -> SanskritQueryNormalizer:
    return SanskritQueryNormalizer(
        heritage_client=heritage_client, normalization_pipeline=normalization_pipeline
    )


@dataclass
class LangnetWiringConfig:
    """Configurable factories for building LanguageEngine wiring."""

    settings: LangnetSettings = field(default_factory=get_settings)
    diogenes_factory: Callable[[LangnetSettings], DiogenesScraper] = _default_diogenes_factory
    whitakers_factory: Callable[[LangnetSettings], WhitakersWords] = _default_whitakers_factory
    cltk_factory: Callable[[LangnetSettings], ClassicsToolkit] = _default_cltk_factory
    cdsl_factory: Callable[[LangnetSettings], SanskritCologneLexicon] = _default_cdsl_factory
    heritage_client_factory: Callable[[LangnetSettings], HeritageHTTPClient] = (
        _default_heritage_client_factory
    )
    heritage_morphology_factory: Callable[[LangnetSettings], HeritageMorphologyService] = (
        _default_heritage_morphology_factory
    )
    normalization_pipeline_factory: (
        Callable[[LangnetSettings], NormalizationPipeline | None] | None
    ) = _default_normalization_factory
    sanskrit_normalizer_factory: Callable[
        [LangnetSettings, HeritageHTTPClient | None, NormalizationPipeline | None],
        SanskritQueryNormalizer,
    ] = _default_sanskrit_normalizer_factory
    warmup_backends: bool | None = None


class LangnetWiring:
    """Assemble LanguageEngine dependencies using injectable factories."""

    def __init__(self, wiring_config: LangnetWiringConfig | None = None):
        self.config = wiring_config or LangnetWiringConfig()
        self.settings = self.config.settings

        scraper = self.config.diogenes_factory(self.settings)
        whitakers = self.config.whitakers_factory(self.settings)
        cltk = self.config.cltk_factory(self.settings)
        cdsl = self.config.cdsl_factory(self.settings)
        heritage_morphology = self.config.heritage_morphology_factory(self.settings)
        heritage_client = self.config.heritage_client_factory(self.settings)
        normalization_pipeline = (
            self.config.normalization_pipeline_factory(self.settings)
            if self.config.normalization_pipeline_factory
            else None
        )
        sanskrit_normalizer = self.config.sanskrit_normalizer_factory(
            self.settings, heritage_client, normalization_pipeline
        )

        engine_config = LanguageEngineConfig(
            scraper=scraper,
            whitakers=whitakers,
            cltk=cltk,
            cdsl=cdsl,
            heritage_client=heritage_client,
            heritage_morphology=heritage_morphology,
            normalization_pipeline=normalization_pipeline,
            sanskrit_normalizer=sanskrit_normalizer,
            enable_normalization=bool(normalization_pipeline),
        )
        self.engine = LanguageEngine(engine_config)

        warmup_backends = (
            self.config.warmup_backends
            if self.config.warmup_backends is not None
            else self.settings.warmup_backends
        )
        if warmup_backends:
            self._warmup_cltk(cltk)

    def _warmup_cltk(self, cltk: ClassicsToolkit) -> None:
        """Prime CLTK/spaCy models to prevent delayed readiness on first request."""
        try:
            cltk.latin_query("amo")
        except Exception as exc:  # noqa: BLE001
            logger.warning("cltk_warmup_latin_failed", error=str(exc))

        try:
            cltk.greek_morphology_query("logos")
        except Exception as exc:  # noqa: BLE001
            logger.warning("cltk_warmup_greek_failed", error=str(exc))

        try:
            cltk.sanskrit_morphology_query("agni")
        except Exception as exc:  # noqa: BLE001
            logger.warning("cltk_warmup_sanskrit_failed", error=str(exc))


def build_langnet_wiring(
    settings: LangnetSettings | None = None, warmup_backends: bool | None = None
) -> LangnetWiring:
    resolved_settings = settings or get_settings()
    wiring_config = LangnetWiringConfig(settings=resolved_settings, warmup_backends=warmup_backends)
    return LangnetWiring(wiring_config)
