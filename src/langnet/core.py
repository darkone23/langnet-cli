
from langnet.diogenes.core import DiogenesScraper
from langnet.whitakers_words.core import WhitakersWords
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon

from langnet.engine.core import LanguageEngine

class LangnetWiring:

    def __init__(self):
        
        scraper = DiogenesScraper()
        whitakers = WhitakersWords()
        cltk = ClassicsToolkit()
        cdsl = SanskritCologneLexicon()

        self.engine = LanguageEngine(scraper, whitakers, cltk, cdsl)
