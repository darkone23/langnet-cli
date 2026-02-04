import structlog

from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.config import config as langnet_config
from langnet.diogenes.core import DiogenesScraper
from langnet.engine.core import LanguageEngine, LanguageEngineConfig
from langnet.heritage.config import HeritageConfig
from langnet.heritage.dictionary import HeritageDictionaryService
from langnet.heritage.morphology import HeritageMorphologyService
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

        scraper = DiogenesScraper()
        whitakers = WhitakersWords()
        cltk = ClassicsToolkit()
        cdsl = SanskritCologneLexicon()

        heritage_config = HeritageConfig(
            base_url=langnet_config.heritage_url,
            timeout=langnet_config.http_timeout,
        )
        heritage_morphology = HeritageMorphologyService(heritage_config)
        heritage_dictionary = HeritageDictionaryService()

        config = LanguageEngineConfig(
            scraper=scraper,
            whitakers=whitakers,
            cltk=cltk,
            cdsl=cdsl,
            heritage_morphology=heritage_morphology,
            heritage_dictionary=heritage_dictionary,
        )
        self.engine = LanguageEngine(config)
        self._initialized = True
