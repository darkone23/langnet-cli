from dataclasses import dataclass
from typing import Any, Optional

import cattrs
import structlog

import langnet.logging  # noqa: F401 - ensures logging is configured before use
from langnet.backend_adapter import LanguageAdapterRegistry
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.diogenes.core import DiogenesLanguages, DiogenesScraper
from langnet.foster.apply import apply_foster_view
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.morphology import (
    HeritageMorphologyService,  # TODO: not sure why this is not just in heritage client?
)
from langnet.normalization import NormalizationPipeline
from langnet.whitakers_words.core import WhitakersWords

logger = structlog.get_logger(__name__)


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
    heritage_morphology: Optional[HeritageMorphologyService] = None
    heritage_client: Optional[HeritageHTTPClient] = None
    normalization_pipeline: Optional[NormalizationPipeline] = None
    enable_normalization: bool = True


class LanguageEngine:
    def __init__(self, config: LanguageEngineConfig):
        self.diogenes = config.scraper
        self.whitakers = config.whitakers
        self.cltk = config.cltk
        self.cdsl = config.cdsl
        self.heritage_morphology = config.heritage_morphology
        self.heritage_client = config.heritage_client
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

        try:
            cdsl_result = self.cdsl.lookup_ascii(word)
            result["cdsl"] = _cattrs_converter.unstructure(cdsl_result)
        except Exception as e:  # noqa: BLE001
            logger.error("backend_failed", backend="cdsl", error=str(e))
            result["cdsl"] = {"error": f"CDSL unavailable: {str(e)}"}

        return result

    def _query_sanskrit_heritage(self, word: str, _cattrs_converter) -> dict | None:
        if not self.heritage_morphology:
            logger.warning("heritage_morphology_service_not_available")
            return None

        result: dict[str, Any] = {}

        # Perform morphological analysis
        try:
            morphology_result = self.heritage_morphology.analyze_word(word)
        except Exception as exc:  # noqa: BLE001
            logger.error("backend_failed", backend="heritage_morphology", error=str(exc))
            morphology_result = None

        if morphology_result:
            result["morphology"] = _cattrs_converter.unstructure(morphology_result)

            # If we have a lemma, look it up in the dictionary
            if morphology_result.solutions and morphology_result.solutions[0].analyses:
                # Extract lemma from first solution's first analysis
                first_analysis = morphology_result.solutions[0].analyses[0]
                lemma = first_analysis.lemma if first_analysis.lemma else None
                if lemma:
                    # Try Heritage Platform dictionary first, fallback to old service
                    dict_result = None
                    dict_source = None
                    if dict_result:
                        # Store dictionary source in result
                        result["dictionary"] = _cattrs_converter.unstructure(dict_result)
                        result["dictionary_source"] = dict_source

                        # Create combined analysis
                        combined = {
                            "lemma": lemma,
                            "pos": first_analysis.pos if first_analysis.pos else "unknown",
                            "morphology_analyses": [
                                {
                                    "word": analysis.word,
                                    "lemma": analysis.lemma,
                                    "pos": analysis.pos,
                                }
                                for analysis in morphology_result.solutions[0].analyses
                            ],
                            "dictionary_entries": dict_result.get("entries", []),
                            "dictionary_source": dict_source,
                            "transliteration": dict_result.get("transliteration", {}),
                        }
                        result["combined"] = combined

        # Fetch canonical form and lemmatization from Heritage HTTP endpoints
        if self.heritage_client:
            try:
                canonical_result = self.heritage_client.fetch_canonical_sanskrit(word)
                if canonical_result:
                    result["canonical"] = canonical_result
            except Exception as exc:  # noqa: BLE001
                logger.warning("heritage_canonical_failed", word=word, error=str(exc))

            try:
                lemmatize_result = self.heritage_client.fetch_lemmatization(word)
                if lemmatize_result:
                    result["lemmatize"] = lemmatize_result
            except Exception as exc:  # noqa: BLE001
                logger.warning("heritage_lemmatize_failed", word=word, error=str(exc))

        return result

    def handle_query(self, lang, word):
        """Handle queries using the universal schema with structured DictionaryEntry objects."""
        lang = LangnetLanguageCodes.get_for_input(lang)
        logger.debug("universal_query_started", lang=lang, word=word)

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

        # Apply Foster functional mapping before adapting to universal schema
        try:
            raw_result = apply_foster_view(raw_result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("apply_foster_view_failed", error=str(exc))

        # Convert to universal schema
        adapter_registry = LanguageAdapterRegistry()
        adapter = adapter_registry.get_adapter(lang)
        unified_result = adapter.adapt(raw_result, lang, word)

        logger.debug("universal_query_completed", lang=lang, word=word, entries=len(unified_result))
        return unified_result

    def get_tool_data(
        self,
        tool: str,
        action: str,
        lang: str | None = None,
        query: str | None = None,
        dict_name: str | None = None,
    ) -> dict:
        """Get raw tool data for debugging and schema evolution."""

        logger.debug(
            "tool_data_request",
            tool=tool,
            action=action,
            lang=lang,
            query=query,
            dict_name=dict_name,
        )

        # Validate tool and action
        self._validate_tool_and_action(tool, action)

        # Validate tool-specific parameters
        self._validate_tool_parameters(tool, lang, query, dict_name)

        # Call tool-specific methods
        return self._execute_tool(tool, action, lang, query, dict_name)

    def _validate_tool_and_action(self, tool: str, action: str):
        """Validate tool and action parameters."""
        valid_tools = {"diogenes", "whitakers", "heritage", "cdsl", "cltk"}
        valid_actions_by_tool = {
            "diogenes": {"parse"},
            "whitakers": {"search"},
            "heritage": {"morphology", "canonical", "lemmatize"},
            "cdsl": {"lookup"},
            "cltk": {"morphology", "dictionary"},
        }

        if tool not in valid_tools:
            raise ValueError(
                f"Invalid tool: {tool}. Must be one of: {', '.join(sorted(valid_tools))}"
            )

        allowed_actions = valid_actions_by_tool.get(tool, set())
        if action not in allowed_actions:
            raise ValueError(
                f"Invalid action '{action}' for tool '{tool}'. Must be one of: "
                f"{', '.join(sorted(allowed_actions)) or '(none)'}"
            )

    def _validate_tool_parameters(
        self, tool: str, lang: str | None, query: str | None, dict_name: str | None
    ):
        """Validate tool-specific parameters."""
        if tool == "diogenes":
            self._validate_diogenes_params(lang, query)
        elif tool == "whitakers":
            self._validate_whitakers_params(query)
        elif tool == "heritage":
            self._validate_heritage_params(query)
        elif tool == "cdsl":
            self._validate_cdsl_params(query)
        elif tool == "cltk":
            self._validate_cltk_params(lang, query)

    def _validate_diogenes_params(self, lang: str | None, query: str | None):
        """Validate Diogenes-specific parameters."""
        if not lang:
            raise ValueError("Missing required parameter: lang for diogenes tool")
        if not query:
            raise ValueError("Missing required parameter: query for diogenes tool")
        valid_languages = {"lat", "grc", "san", "grk"}
        if lang not in valid_languages:
            raise ValueError(
                f"Invalid language: {lang}. Must be one of: {', '.join(sorted(valid_languages))}"
            )

    def _validate_whitakers_params(self, query: str | None):
        """Validate Whitaker's Words-specific parameters."""
        if not query:
            raise ValueError("Missing required parameter: query for whitakers tool")

    def _validate_heritage_params(self, query: str | None):
        """Validate Heritage-specific parameters."""
        if not query:
            raise ValueError("Missing required parameter: query for heritage tool")

    def _validate_cdsl_params(self, query: str | None):
        """Validate CDSL-specific parameters."""
        if not query:
            raise ValueError("Missing required parameter: query for cdsl tool")

    def _validate_cltk_params(self, lang: str | None, query: str | None):
        """Validate CLTK-specific parameters."""
        if not lang:
            raise ValueError("Missing required parameter: lang for cltk tool")
        if not query:
            raise ValueError("Missing required parameter: query for cltk tool")
        valid_languages = {"lat", "grc", "san"}
        if lang not in valid_languages:
            raise ValueError(
                f"Invalid language: {lang}. Must be one of: {', '.join(sorted(valid_languages))}"
            )

    def _execute_tool(
        self, tool: str, action: str, lang: str | None, query: str | None, dict_name: str | None
    ):
        """Execute the specific tool and return results."""
        try:
            if tool == "diogenes":
                return self._get_diogenes_raw(lang or "", query or "")
            elif tool == "whitakers":
                return self._get_whitakers_raw(query or "")
            elif tool == "heritage":
                return self._get_heritage_raw(query or "", action, dict_name)
            elif tool == "cdsl":
                return self._get_cdsl_raw(query or "", dict_name)
            elif tool == "cltk":
                return self._get_cltk_raw(lang or "", query or "", action)
            else:
                raise ValueError(f"Unknown tool: {tool}")
        except Exception as e:
            logger.error("Tool data retrieval failed", tool=tool, action=action, error=str(e))
            raise ValueError(f"Failed to retrieve data from {tool} tool: {str(e)}")

    def _get_diogenes_raw(self, lang: str, query: str) -> dict:
        """Get raw data from Diogenes backend."""
        # Normalize language code
        if lang == "grk":
            lang = "grc"

        # Diogenes only supports Latin and Greek
        if lang not in ["lat", "grc"]:
            raise ValueError(f"Diogenes does not support language: {lang}")

        diogenes_lang = {
            "lat": DiogenesLanguages.LATIN,
            "grc": DiogenesLanguages.GREEK,
        }[lang]

        result = self.diogenes.parse_word(query, diogenes_lang)
        return self._cattrs_converter.unstructure(result)

    def _get_whitakers_raw(self, query: str) -> dict:
        """Get raw data from Whitaker's Words backend."""
        tokenized = [query]
        result = self.whitakers.words(tokenized)
        return self._cattrs_converter.unstructure(result)

    def _get_heritage_raw(self, query: str, action: str, dict_name: str | None = None) -> dict:
        """Get raw data from Heritage Platform backend."""
        if not self.heritage_morphology:
            raise ValueError("Heritage morphology service not available")

        result = {}

        if action == "morphology":
            morphology_result = self.heritage_morphology.analyze_word(query)
            if morphology_result:
                result["morphology"] = self._cattrs_converter.unstructure(morphology_result)

        if action == "canonical":
            canonical_result = self.heritage_client.fetch_canonical_sanskrit(query)
            result["canonical"] = canonical_result

        if action == "lemmatize":
            lemmatize_result = self.heritage_client.fetch_lemmatization(query)
            result["lemmatize"] = lemmatize_result

        return result

    def _get_cdsl_raw(self, query: str, dict_name: str | None = None) -> dict:
        """Get raw data from CDSL backend."""
        # CDSL only supports ASCII lookup currently
        result = self.cdsl.lookup_ascii(query)

        return self._cattrs_converter.unstructure(result)

    def _get_cltk_raw(self, lang: str, query: str, action: str) -> dict:
        """Get raw data from CLTK backend."""
        result = {}

        if lang == "lat" and action == "morphology":
            cltk_result = self.cltk.latin_query(query)
            result["latin_morphology"] = self._cattrs_converter.unstructure(cltk_result)
        elif lang == "grc" and action == "morphology":
            cltk_result = self.cltk.greek_morphology_query(query)
            result["greek_morphology"] = self._cattrs_converter.unstructure(cltk_result)
        elif lang == "san" and action == "morphology":
            cltk_result = self.cltk.sanskrit_morphology_query(query)
            result["sanskrit_morphology"] = self._cattrs_converter.unstructure(cltk_result)
        elif action == "dictionary":
            if lang == "lat":
                cltk_result = self.cltk.latin_query(query)
                result["latin_dictionary"] = self._cattrs_converter.unstructure(cltk_result)
            # Add other language dictionary queries as needed

        return result
