from dataclasses import dataclass
from typing import Any

import cattrs
import structlog

import langnet.logging  # noqa: F401 - ensures logging is configured before use
from langnet.cache.core import NoOpCache, QueryCache
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.diogenes.core import DiogenesLanguages, DiogenesScraper
from langnet.foster.apply import apply_foster_view
from langnet.heritage.dictionary import HeritageDictionaryService
from langnet.heritage.morphology import HeritageMorphologyService
from langnet.normalization import NormalizationPipeline
from langnet.whitakers_words.core import WhitakersWords

logger = structlog.get_logger(__name__)

logger.info("loading_engine_core")


class LangnetLanguageCodes:
    Greek = "grc"
    Latin = "lat"
    Sanskrit = "san"

    @staticmethod
    def get_for_input(lang):
        # Support aliases: grk -> grc
        if lang in (LangnetLanguageCodes.Greek, "grk"):
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


@dataclass(frozen=True)
class LanguageEngineConfig:
    scraper: DiogenesScraper
    whitakers: WhitakersWords
    cltk: ClassicsToolkit
    cdsl: SanskritCologneLexicon
    heritage_morphology: HeritageMorphologyService | None = None
    heritage_dictionary: HeritageDictionaryService | None = None
    cache: QueryCache | NoOpCache | None = None
    normalization_pipeline: NormalizationPipeline | None = None
    enable_normalization: bool = True


class LanguageEngine:
    def __init__(self, config: LanguageEngineConfig):
        self.diogenes = config.scraper
        self.whitakers = config.whitakers
        self.cltk = config.cltk
        self.cdsl = config.cdsl
        self.heritage_morphology = config.heritage_morphology
        self.heritage_dictionary = config.heritage_dictionary
        self.cache = config.cache if config.cache is not None else NoOpCache()
        self.normalization_pipeline = config.normalization_pipeline
        self.enable_normalization = config.enable_normalization
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
        result = {}

        heritage_result = self._query_sanskrit_heritage(word, _cattrs_converter)
        if heritage_result:
            result["heritage"] = heritage_result

        cdsl_result = self._query_sanskrit_cdsl(word, _cattrs_converter)
        if cdsl_result:
            result["cdsl"] = cdsl_result

        lemma_result = self._query_sanskrit_lemma_fallback(result, _cattrs_converter)
        if lemma_result:
            result["cdsl"] = lemma_result

        return result

    def _query_sanskrit_heritage(self, word: str, _cattrs_converter) -> dict | None:
        if not self.heritage_morphology or not self.heritage_dictionary:
            return None

        try:
            logger.debug("attempting_heritage_analysis", word=word)
            heritage_result = self._query_sanskrit_with_heritage(word, _cattrs_converter)
            if heritage_result.get("morphology") or heritage_result.get("dictionary"):
                logger.debug("heritage_analysis_success", word=word)
                return heritage_result
            else:
                logger.debug("heritage_analysis_empty", word=word)
                return heritage_result
        except Exception as e:
            logger.error("heritage_analysis_failed", word=word, error=str(e))
            return {"error": f"Heritage analysis failed: {str(e)}"}

    def _query_sanskrit_cdsl(self, word: str, _cattrs_converter) -> dict:
        try:
            logger.debug("attempting_cdsl_lookup", word=word)
            direct_result = _cattrs_converter.unstructure(self.cdsl.lookup_ascii(word))
            has_results = bool(
                direct_result.get("dictionaries", {}).get("mw")
                or direct_result.get("dictionaries", {}).get("ap90")
            )
            if has_results:
                direct_result["_search_method"] = "direct"
                logger.debug("cdsl_lookup_success", word=word)
            else:
                direct_result["_search_method"] = "no_results"
                direct_result["_warning"] = (
                    "Sanskrit lemmatization unavailable. "
                    "Please search headwords directly (e.g., 'yoga' not 'योगेन')."
                )
                logger.debug("cdsl_lookup_empty", word=word, note="no CDSL results")
            return direct_result
        except Exception as e:
            logger.error("cdsl_lookup_failed", word=word, error=str(e))
            return {"error": f"CDSL unavailable: {str(e)}"}

    def _query_sanskrit_lemma_fallback(self, result: dict, _cattrs_converter) -> dict | None:
        if not result.get("heritage") or result.get("cdsl", {}).get("dictionaries"):
            return None

        heritage_data = result.get("heritage", {})
        solutions = heritage_data.get("morphology", {}).get("solutions", [])
        if not solutions:
            return None

        first_solution = solutions[0]
        analyses = first_solution.get("analyses", [])
        if not analyses:
            return None

        first_analysis = analyses[0]
        lemma = first_analysis.get("lemma")
        if not lemma:
            return None

        try:
            logger.debug("attempting_cdsl_lemma_lookup", lemma=lemma)
            cdsl_result = _cattrs_converter.unstructure(self.cdsl.lookup_ascii(lemma))
            if cdsl_result.get("dictionaries"):
                cdsl_result["_search_method"] = "lemma"
                logger.debug("cdsl_lemma_lookup_success", lemma=lemma)
                return cdsl_result
        except Exception as e:
            logger.error("cdsl_lemma_lookup_failed", lemma=lemma, error=str(e))
        return None

    def _query_sanskrit_with_heritage(self, word: str, _cattrs_converter) -> dict:
        """Query Sanskrit using Heritage Platform for better lemmatization"""
        result: dict[str, Any] = {
            "morphology": None,
            "dictionary": None,
            "combined": None,
        }

        if not self.heritage_morphology or not self.heritage_dictionary:
            logger.warning("heritage_services_not_available")
            return result

        # Perform morphological analysis
        morphology_result = self.heritage_morphology.analyze_word(word)
        if morphology_result:
            result["morphology"] = _cattrs_converter.unstructure(morphology_result)

            # If we have a lemma, look it up in the dictionary
            if morphology_result.solutions and morphology_result.solutions[0].analyses:
                # Extract lemma from first solution's first analysis
                first_analysis = morphology_result.solutions[0].analyses[0]
                lemma = first_analysis.lemma if first_analysis.lemma else None
                if lemma:
                    dict_result = self.heritage_dictionary.lookup_word(lemma)
                    if dict_result and dict_result.get("entries"):
                        result["dictionary"] = _cattrs_converter.unstructure(dict_result)

                        # Create combined analysis
                        combined = {
                            "lemma": lemma,
                            "pos": first_analysis.pos if first_analysis.pos else "unknown",
                            "morphology_analyses": [
                                {
                                    "word": analysis.word,
                                    "lemma": analysis.lemma,
                                    "pos": analysis.pos,
                                    "confidence": analysis.confidence,
                                }
                                for analysis in morphology_result.solutions[0].analyses
                            ],
                            "dictionary_entries": dict_result.get("entries", []),
                            "transliteration": dict_result.get("transliteration", {}),
                        }
                        result["combined"] = combined

        return result

    def handle_query(self, lang, word):
        """Handle queries using the universal schema with structured DictionaryEntry objects."""
        from langnet.backend_adapter import LanguageAdapterRegistry

        lang = LangnetLanguageCodes.get_for_input(lang)
        logger.debug("universal_query_started", lang=lang, word=word)

        # Check cache for structured entries
        cached_result = self.cache.get(lang, word)
        if cached_result is not None:
            logger.debug("query_cached_universal", lang=lang, word=word)
            # If cached result is already DictionaryEntry objects, return them
            if (
                isinstance(cached_result, list)
                and cached_result
                and hasattr(cached_result[0], "word")
            ):
                return cached_result
            # If cached result is a dict (old format), convert it
            elif isinstance(cached_result, dict):
                adapter_registry = LanguageAdapterRegistry()
                adapter = adapter_registry.get_adapter(lang)
                unified_result = adapter.adapt(cached_result, lang, word)
                self.cache.put(lang, word, unified_result)  # Update with structured format
                return unified_result
            # If cached result is a list of dicts (old format), convert it
            elif (
                isinstance(cached_result, list)
                and cached_result
                and isinstance(cached_result[0], dict)
            ):
                adapter_registry = LanguageAdapterRegistry()
                adapter = adapter_registry.get_adapter(lang)
                unified_result = adapter.adapt(cached_result, lang, word)
                self.cache.put(lang, word, unified_result)  # Update with structured format
                return unified_result

        # Get raw backend results
        _cattrs_converter = self._cattrs_converter

        if lang == LangnetLanguageCodes.Greek:
            logger.debug("routing_to_greek_backends", lang=lang, word=word)
            raw_result = self._query_greek(word, _cattrs_converter)
        elif lang == LangnetLanguageCodes.Latin:
            logger.debug("routing_to_latin_backends", lang=lang, word=word)
            raw_result = self._query_latin(word, _cattrs_converter)
        elif lang == LangnetLanguageCodes.Sanskrit:
            logger.debug("routing_to_sanskrit_backends", lang=lang, word=word)
            raw_result = self._query_sanskrit(word, _cattrs_converter)
        else:
            raise NotImplementedError(f"Do not know how to handle {lang}")

        # Convert to universal schema
        adapter_registry = LanguageAdapterRegistry()
        adapter = adapter_registry.get_adapter(lang)
        unified_result = adapter.adapt(raw_result, lang, word)

        # Cache structured entries
        self.cache.put(lang, word, unified_result)
        logger.debug("universal_query_completed", lang=lang, word=word, entries=len(unified_result))
        return unified_result
