import time
from dataclasses import dataclass
from typing import cast

import cattrs
import structlog

from langnet.adapters.registry import LanguageAdapterRegistry
from langnet.classics_toolkit.core import ClassicsToolkit
from langnet.cologne.core import SanskritCologneLexicon
from langnet.diogenes.core import DiogenesLanguages, DiogenesScraper
from langnet.engine.sanskrit_normalizer import (
    SanskritNormalizationResult,
    SanskritQueryNormalizer,
)
from langnet.foster.apply import apply_foster_view
from langnet.heritage.client import HeritageHTTPClient
from langnet.heritage.morphology import (
    HeritageMorphologyService,  # TODO: not sure why this is not just in heritage client?
)
from langnet.heritage.types import CanonicalResult
from langnet.normalization import NormalizationPipeline
from langnet.types import JSONMapping
from langnet.validation import validate_tool_request
from langnet.whitakers_words.core import WhitakersWords

try:  # structlog contextvars may be missing in some environments
    from structlog.contextvars import get_contextvars  # type: ignore
except Exception:  # pragma: no cover

    def get_contextvars():
        return {}


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
    heritage_morphology: HeritageMorphologyService | None = None
    heritage_client: HeritageHTTPClient | None = None
    normalization_pipeline: NormalizationPipeline | None = None
    sanskrit_normalizer: SanskritQueryNormalizer | None = None
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
        self.sanskrit_normalizer = config.sanskrit_normalizer
        self.enable_normalization = config.enable_normalization
        self._cattrs_converter = cattrs.Converter(omit_if_default=True)

    def _get_sanskrit_normalizer(self) -> SanskritQueryNormalizer:
        if not self.sanskrit_normalizer:
            self.sanskrit_normalizer = SanskritQueryNormalizer(
                heritage_client=self.heritage_client,
                normalization_pipeline=self.normalization_pipeline
                if self.enable_normalization
                else None,
            )
        return self.sanskrit_normalizer

    def _normalize_sanskrit_word(self, word: str) -> tuple[str, str, list[str], list[str] | None]:
        normalizer = self._get_sanskrit_normalizer()
        normalized = normalizer.normalize(word)
        heritage_form = normalized.canonical_heritage
        canonical_slp1 = normalized.canonical_slp1
        slp1_candidates = list(normalized.slp1_candidates)
        if canonical_slp1 and canonical_slp1 not in slp1_candidates:
            slp1_candidates.insert(0, canonical_slp1)
        return heritage_form, canonical_slp1, slp1_candidates, normalized.canonical_tokens

    def _detect_heritage_encoding(self, word: str) -> str:
        normalizer = self._get_sanskrit_normalizer()
        return normalizer.detect_heritage_encoding(word)

    def _looks_mangled_slp1(self, text: str) -> bool:
        # Delegate to the normalizer heuristic to keep behavior in sync.
        return self._get_sanskrit_normalizer()._looks_mangled_slp1(text)  # type: ignore[attr-defined]

    @staticmethod
    def _backend_error(backend: str, exc: Exception) -> JSONMapping:
        ctx = {}
        try:
            ctx = get_contextvars()
        except Exception:
            ctx = {}
        envelope: JSONMapping = {"backend": backend, "message": str(exc)}
        if ctx.get("request_id"):
            envelope["request_id"] = ctx["request_id"]
        return {"error": envelope}

    def _record_timing(self, timings: dict[str, float], name: str, func):
        start = time.perf_counter()
        try:
            return func()
        finally:
            timings[name] = (time.perf_counter() - start) * 1000

    def _query_greek(self, word: str, _cattrs_converter, timings: dict[str, float]) -> dict:
        result: dict = {}
        try:
            result["diogenes"] = self._record_timing(
                timings,
                "diogenes",
                lambda: _cattrs_converter.unstructure(
                    self.diogenes.parse_word(word, DiogenesLanguages.GREEK)
                ),
            )
        except Exception as e:
            logger.error("backend_failed", backend="diogenes", error=str(e))
            result["diogenes"] = self._backend_error("diogenes", e)
        try:
            if self.cltk.spacy_is_available():
                logger.debug("spacy_available", word=word)
                spacy_result = self._record_timing(
                    timings, "spacy", lambda: self.cltk.greek_morphology_query(word)
                )
                result["spacy"] = _cattrs_converter.unstructure(spacy_result)
            else:
                logger.debug("spacy_unavailable", word=word)
                timings.setdefault("spacy", 0.0)
        except Exception as e:
            logger.error("backend_failed", backend="spacy", error=str(e))
            result["spacy"] = self._backend_error("spacy", e)
        return result

    def _query_latin(self, word: str, _cattrs_converter, timings: dict[str, float]) -> dict:
        tokenized = [word]
        result = {}
        try:
            dg_result = self._record_timing(
                timings,
                "diogenes",
                lambda: self.diogenes.parse_word(word, DiogenesLanguages.LATIN),
            )
            result["diogenes"] = _cattrs_converter.unstructure(dg_result)
        except Exception as e:
            logger.error("backend_failed", backend="diogenes", error=str(e))
            result["diogenes"] = self._backend_error("diogenes", e)
        try:
            ww_result = self._record_timing(
                timings, "whitakers", lambda: self.whitakers.words(tokenized)
            )
            result["whitakers"] = _cattrs_converter.unstructure(ww_result)
        except Exception as e:
            logger.error("backend_failed", backend="whitakers", error=str(e))
            result["whitakers"] = self._backend_error("whitakers", e)
        try:
            cltk_result = self._record_timing(timings, "cltk", lambda: self.cltk.latin_query(word))
            result["cltk"] = _cattrs_converter.unstructure(cltk_result)
        except Exception as e:
            logger.error("backend_failed", backend="cltk", error=str(e))
            result["cltk"] = self._backend_error("cltk", e)
        return result

    def _query_sanskrit(self, word: str, _cattrs_converter, timings: dict[str, float]) -> dict:
        result = {}

        normalized: SanskritNormalizationResult = self._record_timing(
            timings,
            "sanskrit_normalize",
            lambda: self._get_sanskrit_normalizer().normalize(word),
        )
        canonical = normalized.canonical_heritage
        canonical_slp1 = normalized.canonical_slp1
        slp1_candidates = normalized.slp1_candidates
        canonical_tokens = normalized.canonical_tokens

        heritage_result = self._record_timing(
            timings,
            "heritage",
            lambda: self._query_sanskrit_heritage(canonical, _cattrs_converter, timings),
        )
        if heritage_result:
            result["heritage"] = heritage_result

        try:
            cdsl_lookup_error: Exception | None = None
            cdsl_result = None
            for candidate in [canonical_slp1, *slp1_candidates]:
                try:
                    cdsl_result = self._record_timing(
                        timings, "cdsl", lambda: self.cdsl.lookup_ascii(candidate)
                    )
                    break
                except Exception as exc:  # noqa: BLE001
                    cdsl_lookup_error = exc
                    continue

            if cdsl_result:
                result["cdsl"] = _cattrs_converter.unstructure(cdsl_result)
            else:
                raise cdsl_lookup_error or RuntimeError("CDSL lookup failed for all candidates")
        except Exception as e:  # noqa: BLE001
            logger.error("backend_failed", backend="cdsl", error=str(e))
            result["cdsl"] = self._backend_error("cdsl", e)

        result["canonical_form"] = canonical_slp1 or canonical
        result["canonical_slp1"] = canonical_slp1
        if slp1_candidates:
            result["canonical_slp1_candidates"] = slp1_candidates
        result["canonical_heritage"] = canonical
        if canonical_tokens:
            result["canonical_tokens"] = canonical_tokens
        result["input_form"] = word
        return result

    def _query_sanskrit_heritage(
        self, word: str, _cattrs_converter, timings: dict[str, float]
    ) -> dict | None:
        if not self.heritage_morphology:
            logger.warning("heritage_morphology_service_not_available")
            return None

        result: JSONMapping = {}

        # Perform morphological analysis
        try:
            morphology_encoding = (
                self.sanskrit_normalizer.detect_heritage_encoding(word)
                if self.sanskrit_normalizer
                else "velthuis"
            )
            morphology_result = self._record_timing(
                timings,
                "heritage_morphology",
                lambda: self.heritage_morphology.analyze_word(word, encoding=morphology_encoding),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("backend_failed", backend="heritage_morphology", error=str(exc))
            morphology_result = None

        if morphology_result:
            result["morphology"] = _cattrs_converter.unstructure(morphology_result)

            if morphology_result.solutions and morphology_result.solutions[0].analyses:
                first_analysis = morphology_result.solutions[0].analyses[0]
                analyses = morphology_result.solutions[0].analyses
                result["combined"] = {
                    "lemma": first_analysis.lemma or word,
                    "pos": first_analysis.pos or "unknown",
                    "morphology_analyses": [
                        {
                            "word": analysis.word,
                            "lemma": analysis.lemma,
                            "pos": analysis.pos,
                            "features": {
                                "case": analysis.case,
                                "gender": analysis.gender,
                                "number": analysis.number,
                                "person": analysis.person,
                                "tense": analysis.tense,
                                "voice": analysis.voice,
                                "mood": analysis.mood,
                                "stem": analysis.stem,
                            },
                        }
                        for analysis in analyses
                    ],
                }

        # Fetch canonical form and lemmatization from Heritage HTTP endpoints
        if self.heritage_client:
            try:
                canonical_result: CanonicalResult | None = self._record_timing(
                    timings,
                    "heritage_canonical",
                    lambda: self.heritage_client.fetch_canonical_sanskrit(word),
                )
                if canonical_result:
                    result["canonical"] = cast(JSONMapping, canonical_result)
            except Exception as exc:  # noqa: BLE001
                logger.warning("heritage_canonical_failed", word=word, error=str(exc))

        return result

    def handle_query(self, lang, word):
        """Handle queries using the universal schema with structured DictionaryEntry objects."""
        overall_start = time.perf_counter()
        lang = LangnetLanguageCodes.get_for_input(lang)
        logger.debug("universal_query_started", lang=lang, word=word)

        # Get raw backend results
        _cattrs_converter = self._cattrs_converter

        timings: dict[str, float] = {}

        if lang == LangnetLanguageCodes.Greek:
            logger.debug("routing_to_greek_backends", lang=lang, word=word)
            raw_result = self._query_greek(word, _cattrs_converter, timings)
        elif lang == LangnetLanguageCodes.Latin:
            logger.debug("routing_to_latin_backends", lang=lang, word=word)
            raw_result = self._query_latin(word, _cattrs_converter, timings)
        elif lang == LangnetLanguageCodes.Sanskrit:
            logger.debug("routing_to_sanskrit_backends", lang=lang, word=word)
            raw_result = self._query_sanskrit(word, _cattrs_converter, timings)
        else:
            raise NotImplementedError(f"Do not know how to handle {lang}")

        raw_result["_timings"] = timings

        # Apply Foster functional mapping before adapting to universal schema
        foster_start = time.perf_counter()
        try:
            raw_result = apply_foster_view(raw_result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("apply_foster_view_failed", error=str(exc))
        timings["foster_view"] = (time.perf_counter() - foster_start) * 1000

        # Convert to universal schema
        adapt_start = time.perf_counter()
        adapter_registry = LanguageAdapterRegistry()
        adapter = adapter_registry.get_adapter(lang)
        # Pass timings to adapters that support it for finer attribution.
        try:
            unified_result = adapter.adapt(raw_result, lang, word, timings=timings)  # type: ignore[arg-type]
        except TypeError:
            unified_result = adapter.adapt(raw_result, lang, word)
        timings["adapt_unified"] = (time.perf_counter() - adapt_start) * 1000
        timings["handle_query_total"] = (time.perf_counter() - overall_start) * 1000

        logger.info(
            "handle_query_timings",
            lang=lang,
            word=word,
            timings={k: round(v, 3) for k, v in timings.items()},
        )

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

        validation_error = validate_tool_request(tool, action, lang, query, dict_name)
        if validation_error:
            raise ValueError(validation_error)

        return self._execute_tool(tool, action, lang, query, dict_name)

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

        (
            canonical_query,
            canonical_slp1,
            _slp1_candidates,
            canonical_tokens,
        ) = self._normalize_sanskrit_word(query)
        result = {}

        if action == "morphology":
            morphology_encoding = self._detect_heritage_encoding(canonical_query)
            morphology_result = self.heritage_morphology.analyze_word(
                canonical_query, encoding=morphology_encoding
            )
            if morphology_result:
                result["morphology"] = self._cattrs_converter.unstructure(morphology_result)

        if action == "canonical":
            canonical_result = (
                self.heritage_client.fetch_canonical_via_sktsearch(query)
                if self.heritage_client
                else {"canonical_text": None, "match_method": "unavailable"}
            )
            if (
                canonical_result
                and not canonical_result.get("canonical_text")
                and self.heritage_client
            ):
                # Fallback to older canonical endpoint if sktsearch misses
                canonical_result = self.heritage_client.fetch_canonical_sanskrit(query)
            result["canonical"] = canonical_result

        if action == "lemmatize":
            # Use morphology as the lemmatization source to avoid legacy endpoints.
            morphology_encoding = self._detect_heritage_encoding(canonical_query)
            morpho = self.heritage_morphology.analyze_word(
                canonical_query, encoding=morphology_encoding
            )
            if morpho and morpho.solutions:
                analyses = morpho.solutions[0].analyses if morpho.solutions else []
                primary = analyses[0] if analyses else {}
                result["lemmatize"] = {
                    "lemma": primary.get("lemma"),
                    "grammar": primary.get("analysis") or primary.get("pos"),
                    "analyses": self._cattrs_converter.unstructure(analyses),
                    "used_source": "heritage_sktreader",
                    "original_input": query,
                    "canonical_input": canonical_query,
                }
            else:
                result["lemmatize"] = {
                    "lemma": None,
                    "message": "No structured lemmatization data found",
                    "used_source": "heritage_sktreader",
                    "original_input": query,
                    "canonical_input": canonical_query,
                }

        if canonical_tokens:
            result["canonical_tokens"] = canonical_tokens
        return result

    def _get_cdsl_raw(self, query: str, dict_name: str | None = None) -> dict:
        """Get raw data from CDSL backend."""
        heritage_form, canonical_slp1, slp1_candidates, canonical_tokens = (
            self._normalize_sanskrit_word(query)
        )

        # Build a candidate list preferring clean SLP1 forms first.
        dedup: list[str] = []
        for c in [canonical_slp1, *slp1_candidates]:
            if c and c not in dedup:
                dedup.append(c)
        candidate_list = [c for c in dedup if not self._looks_mangled_slp1(c)]
        if not candidate_list:
            candidate_list = dedup
        # Normalize casing so mixed-case headwords (e.g., Siva/) still match CDSL keys.
        candidate_list = [c.lower() for c in candidate_list]
        # Deduplicate again after lowercasing while preserving order
        seen_lower: set[str] = set()
        candidate_list = [
            c for c in candidate_list if c and not (c in seen_lower or seen_lower.add(c))
        ]

        cdsl_result = None
        last_error: Exception | None = None
        for candidate in candidate_list:
            try:
                cdsl_result = self.cdsl.lookup_ascii(candidate)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if cdsl_result is None:
            raise last_error or RuntimeError(f"CDSL lookup failed for {query}")

        # Attach canonical forms for caller visibility
        cdsl_result["canonical_form"] = canonical_slp1 or heritage_form
        cdsl_result["canonical_form_candidates"] = [
            c for c in [canonical_slp1, *slp1_candidates] if c
        ]
        cdsl_result["input_form"] = query
        if canonical_tokens:
            cdsl_result["canonical_tokens"] = canonical_tokens

        return self._cattrs_converter.unstructure(cdsl_result)

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
