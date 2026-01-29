import structlog

from langnet.cache.core import create_cache
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.config import config as langnet_config
from langnet.diogenes.core import DiogenesScraper
from langnet.engine.core import LanguageEngine, LanguageEngineConfig
from langnet.whitakers_words.core import WhitakersWords

logger = structlog.get_logger(__name__)


class LangnetWiring:
    _singleton_instance: "LangnetWiring | None" = None

    def __new__(cls, cache_enabled: bool | None = None):
        if cls._singleton_instance is None:
            cls._singleton_instance = super().__new__(cls)
        return cls._singleton_instance

    def __init__(self, cache_enabled: bool | None = None):
        if hasattr(self, "_initialized"):
            return

        use_cache = cache_enabled if cache_enabled is not None else langnet_config.cache_enabled
        scraper = DiogenesScraper()
        whitakers = WhitakersWords()
        cltk = ClassicsToolkit()
        cdsl = SanskritCologneLexicon()
        cache = create_cache(use_cache)

        if use_cache:
            logger.info("cache_enabled", path=str(cache.cache_dir))
        else:
            logger.info("cache_disabled")

        config = LanguageEngineConfig(
            scraper=scraper,
            whitakers=whitakers,
            cltk=cltk,
            cdsl=cdsl,
            cache=cache,
        )
        self.engine = LanguageEngine(config)
        self._initialized = True
