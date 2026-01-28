import cattrs
import structlog

import langnet.logging  # noqa: F401 - ensures logging is configured before use
from langnet.cache.core import NoOpCache, QueryCache
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.diogenes.core import DiogenesLanguages, DiogenesScraper
from langnet.whitakers_words.core import WhitakersWords

logger = structlog.get_logger(__name__)

logger.info("loading_engine_core")


class LangnetLanguageCodes:
    Greek = "grc"
    Latin = "lat"
    Sanskrit = "san"

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
        cache: QueryCache | NoOpCache | None = None,
    ):
        self.diogenes = scraper
        self.whitakers = whitakers
        self.cltk = cltk
        self.cdsl = cdsl
        self.cache = cache if cache is not None else NoOpCache()
        self._cattrs_converter = cattrs.Converter(omit_if_default=True)

    def _query_greek(self, word: str, _cattrs_converter) -> dict:
        result: dict = {}
        try:
            result["diogenes"] = _cattrs_converter.unstructure(
                self.diogenes.parse_word(word, DiogenesLanguages.GREEK)
            )
        except Exception as e:
            logger.error("backend_failed", backend="diogenes", error=str(e))
            result["diogenes"] = {"error": f"Diogenes unavailable: {str(e)}"}
        try:
            if self.cltk.spacy_is_available():
                logger.debug("spacy_available", word=word)
                spacy_result = self.cltk.greek_morphology_query(word)
                result["spacy"] = _cattrs_converter.unstructure(spacy_result)
            else:
                logger.debug("spacy_unavailable", word=word)
        except Exception as e:
            logger.error("backend_failed", backend="spacy", error=str(e))
            result["spacy"] = {"error": f"Spacy unavailable: {str(e)}"}
        return result

    def _query_latin(self, word: str, _cattrs_converter) -> dict:
        tokenized = [word]
        result = {}
        try:
            dg_result = self.diogenes.parse_word(word, DiogenesLanguages.LATIN)
            result["diogenes"] = _cattrs_converter.unstructure(dg_result)
        except Exception as e:
            logger.error("backend_failed", backend="diogenes", error=str(e))
            result["diogenes"] = {"error": f"Diogenes unavailable: {str(e)}"}
        try:
            ww_result = self.whitakers.words(tokenized)
            result["whitakers"] = _cattrs_converter.unstructure(ww_result)
        except Exception as e:
            logger.error("backend_failed", backend="whitakers", error=str(e))
            result["whitakers"] = {"error": f"Whitakers unavailable: {str(e)}"}
        try:
            cltk_result = self.cltk.latin_query(word)
            result["cltk"] = _cattrs_converter.unstructure(cltk_result)
        except Exception as e:
            logger.error("backend_failed", backend="cltk", error=str(e))
            result["cltk"] = {"error": f"CLTK unavailable: {str(e)}"}
        return result

    def _query_sanskrit(self, word: str, _cattrs_converter) -> dict:
        try:
            direct_result = _cattrs_converter.unstructure(self.cdsl.lookup_ascii(word))
            has_results = bool(
                direct_result.get("dictionaries", {}).get("mw")
                or direct_result.get("dictionaries", {}).get("ap90")
            )
            if has_results:
                direct_result["_search_method"] = "direct"
                logger.debug("sanskrit_direct_lookup", word=word)
                return direct_result

            logger.debug(
                "sanskrit_direct_lookup_empty",
                word=word,
                trying_lemmatization=True,
            )

            morphology_result = self.cltk.sanskrit_morphology_query(word)
            if morphology_result.lemma and morphology_result.lemma not in (
                "cltk_unavailable",
                "error",
            ):
                logger.debug(
                    "sanskrit_lemmatization_success",
                    word=word,
                    lemma=morphology_result.lemma,
                )
                lemma_result = _cattrs_converter.unstructure(
                    self.cdsl.lookup_ascii(morphology_result.lemma)
                )
                has_lemma_results = bool(
                    lemma_result.get("dictionaries", {}).get("mw")
                    or lemma_result.get("dictionaries", {}).get("ap90")
                )
                if has_lemma_results:
                    lemma_result["_lemmatized_from"] = word
                    lemma_result["_search_method"] = "lemmatized"
                    lemma_result["_lemma"] = morphology_result.lemma
                    logger.debug(
                        "sanskrit_lemmatization_lookup_success",
                        word=word,
                        lemma=morphology_result.lemma,
                    )
                    return lemma_result

                logger.debug(
                    "sanskrit_lemmatization_lookup_empty",
                    word=word,
                    lemma=morphology_result.lemma,
                )
                direct_result["_lemmatized_from"] = word
                direct_result["_lemma"] = morphology_result.lemma
                direct_result["_search_method"] = "lemmatized_no_results"
                return direct_result

            logger.debug("sanskrit_lemmatization_failed", word=word)
            direct_result["_search_method"] = "direct_no_results"
            return direct_result

        except Exception as e:
            logger.error("backend_failed", backend="cdsl", error=str(e))
            return {"error": f"CDSL unavailable: {str(e)}"}

    def handle_query(self, lang, word):
        lang = LangnetLanguageCodes.get_for_input(lang)
        _cattrs_converter = self._cattrs_converter

        logger.debug("query_started", lang=lang, word=word)

        cached_result = self.cache.get(lang, word)
        if cached_result is not None:
            logger.debug("query_cached", lang=lang, word=word)
            return cached_result

        if lang == LangnetLanguageCodes.Greek:
            logger.debug("routing_to_greek_backends", lang=lang, word=word)
            result = self._query_greek(word, _cattrs_converter)
        elif lang == LangnetLanguageCodes.Latin:
            logger.debug("routing_to_latin_backends", lang=lang, word=word)
            result = self._query_latin(word, _cattrs_converter)
        elif lang == LangnetLanguageCodes.Sanskrit:
            logger.debug("routing_to_sanskrit_backends", lang=lang, word=word)
            result = self._query_sanskrit(word, _cattrs_converter)
        else:
            raise NotImplementedError(f"Do not know how to handle {lang}")

        self.cache.put(lang, word, result)
        logger.debug("query_completed", lang=lang, word=word)
        return result
