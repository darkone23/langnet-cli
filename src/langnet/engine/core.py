from langnet.diogenes.core import DiogenesScraper, DiogenesLanguages
from langnet.whitakers_words.core import WhitakersWords
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon

from rich.pretty import pprint

pprint("Loading engine core...")

class LangnetLanguageCodes:

    Greek = ClassicsToolkit.GREEK.iso_639_3_code  # grc
    Latin = ClassicsToolkit.LATIN.iso_639_3_code  # lat
    Sanskrit = ClassicsToolkit.SANSKRIT.iso_639_3_code  # san

    @staticmethod
    def get_for_input(lang):
        if lang == LangnetLanguageCodes.Greek:
            return LangnetLanguageCodes.Greek
        elif lang == LangnetLanguageCodes.Latin:
            return LangnetLanguageCodes.Latin
        elif lang == LangnetLanguageCodes.Sanskrit:
            return LangnetLanguageCodes.Sanskrit
        else:
            raise ValueError(f"Unsupported language: {lang}")


class GrammarAbbreviations:
    cassells_terms_ = {  # list from 1854 with some tweaks
        "abbrev": "abbreviated, abbreviation.",
        "abl": "ablative.",
        "absol": "absolute.",
        "abstr": "abstract",
        "acc": "accusative",
        "act": "active.",
        "adj": "adjective.",
        "adversat": "adversative.",
        "architect": "architectural.",
        "c": "common (both m. and f.).",
        "class": "classical.",
        "colloq": "colloquial.",
        "commerc": "commercial.",
        "compar": "comparative.",
        "concr": "concrete,",
        "conj": "conjunction,",
        "dat": "dative.",
        "dep": "deponent.",
        "dim": "dimunitive.",
        "distrib": "distributive.",
        "e.g.": "exempli gratia (for example).",
        "esp": "especially.",
        "etc": "et cetera.",
        "exclam": "exclamatory.",
        "f": "feminine.",
        "fem": "feminine.",
        "fig": "figure, figurative.",
        "foll": "followed.",
        "fut": "future.",
        "gen": "general, generally.",
        "genit": "genitive.",
        "i.e.": "id est (that is}.",
        "imperf": "imperfect.",
        "impers": "impersonal,",
        "indecl": "indeclinable.",
        "indef": "indefinite.",
        "indic": "indicative.",
        "infin": "infinitive.",
        "inter": "interjection.",
        "interrog": "interrogative.",
        "intransit": "intransitive.",
        "logic": "logical.",
        "m": "masculine.",
        "medic": "medical.",
        "naut": "nautical,",
        "neg": "negative.",
        "nom": "nominative.",
        "obs": "obsolete.",
        "opp": "opposite (to).",
        "partic": "participle.",
        "pass": "passive.",
        "perf": "perfect.",
        "pers": "person.",
        "personif": "personified",
        "philosoph": "philosophy, philosophical .",
        "perh": "perhaps.",
        "phr": "phrase.",
        "p": "plural.",
        "pl": "plural.",
        # "pp": "past-participle.",
        "posit": "positive.",
        "pos": "positive.",
        "prep": "preposition.",
        "bres": "present.",
        "pron": "pronoun,",
        "q.v.": "quod vide, quae vide (i.e. see article concerned)",
        "relig": "religious.",
        "rhet": "rhetoric, rhetorical.",
        "sc": "scilicet (that is to say).",
        "sing": "singular.",
        "subst": "substantive,",
        "t.t.": "technical term",
        "transf": "transferred (i.e. used in altered sense)",
        "transit": "transitive.",
        "voc": "vocative.",
    }


class LanguageEngine:

    def __init__(
        self,
        scraper: DiogenesScraper,
        whitakers: WhitakersWords,
        cltk: ClassicsToolkit,
        cdsl: SanskritCologneLexicon,
    ):
        self.diogenes = scraper
        self.whitakers = whitakers
        self.cltk = cltk
        self.cdsl = cdsl

    def handle_query(self, lang, word):
        print("got query:", word, lang)
        # at this point word and lang are utf-8 characters as presented by the user

        # add some basic 'what sort of input is this' mode checking for the word
        # ie "does it have ascii only or not"

        lang = LangnetLanguageCodes.get_for_input(lang)

        if lang == LangnetLanguageCodes.Greek:
            result = dict(
                diogenes=self.diogenes.parse_word(
                    word, DiogenesLanguages.GREEK
                ).model_dump(exclude_none=True)
            )
        elif lang == LangnetLanguageCodes.Latin:
            tokenized = [word]
            result = dict(
                diogenes=self.diogenes.parse_word(
                    word, DiogenesLanguages.LATIN
                ).model_dump(exclude_none=True),
                whitakers=self.whitakers.words(tokenized).model_dump(exclude_none=True),
                cltk=self.cltk.latin_query(word).model_dump(exclude_none=True),
            )
        elif lang == LangnetLanguageCodes.Sanskrit:
            # TODO: add basic sanskrit lexicon support via CDSL
            result = self.cdsl.lookup_ascii(word).model_dump(exclude_none=True)
        else:
            raise NotImplementedError(f"Do not know how to handle {lang}")

        return result
