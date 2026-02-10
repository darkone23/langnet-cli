import re

import structlog
from bs4 import BeautifulSoup

from ..cologne.core import SanskritCologneLexicon
from .client import HeritageAPIError, HeritageHTTPClient
from .encoding_service import EncodingService
from .models import HeritageMorphologyResult, HeritageSolution, HeritageWordAnalysis
from .parameters import HeritageParameterBuilder
from .parsers import MorphologyParser
from .types import (
    CombinedAnalysis,
    HeritageDictionaryLookup,
    MorphologyParseResult,
    MorphologySolutionDict,
    WordAnalysisBundle,
)

logger = structlog.get_logger(__name__)


class HeritageDictionaryService:
    """Service combining Heritage morphology with CDSL dictionary lookup"""

    def __init__(self):
        self.scl = SanskritCologneLexicon()
        self.morphology_client = HeritageHTTPClient()

    def _normalize_for_sktreader(self, text: str, encoding: str | None) -> tuple[str, str]:
        """Normalize inputs for sktreader requests while preserving original text."""
        target_encoding = "velthuis"
        try:
            from indic_transliteration.detect import detect  # noqa: PLC0415
            from indic_transliteration.sanscript import VELTHUIS, transliterate  # noqa: PLC0415

            detected = encoding or EncodingService.detect_encoding(text) or "ascii"
            source_scheme = detect(text) or detected
            normalized = transliterate(text, source_scheme, VELTHUIS)
            return normalized, target_encoding
        except Exception:
            return text, target_encoding

    def lookup_word(self, word: str, dict_id: str = "MW") -> HeritageDictionaryLookup:
        """Look up a word in the CDSL dictionary"""
        try:
            result = self.scl.lookup_ascii(word)

            dict_key = dict_id.lower()
            entries = result.get("dictionaries", {}).get(dict_key, [])

            return {
                "word": word,
                "dict_id": dict_id,
                "entries": entries,
                "transliteration": result.get("transliteration", {}),
                "root": result.get("root"),
            }

        except Exception as e:
            logger.error("Dictionary lookup failed", word=word, error=str(e))
            return {
                "word": word,
                "dict_id": dict_id,
                "error": str(e),
                "entries": [],
                "transliteration": {},
            }

    def analyze_word(
        self, word: str, encoding: str | None = None, max_solutions: int | None = None
    ) -> WordAnalysisBundle:
        """Analyze a word with both morphology and dictionary lookup"""
        results: WordAnalysisBundle = {
            "word": word,
            "morphology": None,
            "dictionary": None,
            "combined_analysis": None,
        }

        try:
            # Create a client directly without context manager
            client = HeritageHTTPClient()
            normalized_word, normalized_encoding = self._normalize_for_sktreader(word, encoding)
            morph_params = HeritageParameterBuilder.build_morphology_params(
                text=normalized_word,
                encoding=normalized_encoding,
                max_solutions=max_solutions,
            )
            morph_result = client.fetch_cgi_script("sktreader", morph_params)

            parsed_morphology = self._parse_morphology_response(morph_result)
            results["morphology"] = parsed_morphology

            if parsed_morphology:
                # Extract lemma from first solution if available
                lemma = None
                solutions = parsed_morphology.get("solutions", [])
                if solutions:
                    first_solution = solutions[0]
                    analyses = first_solution.get("analyses", [])
                    if analyses:
                        first_analysis = analyses[0]
                        lemma = first_analysis.lemma

                if lemma:
                    dict_results = self.lookup_word(lemma)
                    results["dictionary"] = dict_results

                    results["combined_analysis"] = self._combine_analysis(
                        parsed_morphology, dict_results
                    )

        except Exception as e:
            logger.error("Word analysis failed", word=word, error=str(e))
            results["error"] = str(e)

        return results

    def _parse_morphology_response(self, html_content: str) -> MorphologyParseResult | None:
        """Parse morphology response from Heritage Platform"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            morphology_data: MorphologyParseResult = {
                "solutions": [],
                "word_analyses": [],
                "total_solutions": 0,
                "encoding": "velthuis",
                "metadata": {},
            }
            self._collect_latin_spans(soup, morphology_data)
            if not morphology_data["solutions"]:
                self._collect_navy_links(soup, morphology_data)
            if morphology_data["solutions"]:
                morphology_data["total_solutions"] = len(morphology_data["solutions"])
                return morphology_data
            return None
        except Exception as e:
            logger.error("Morphology parsing failed", error=str(e))
            return None

    def _collect_latin_spans(
        self, soup: BeautifulSoup, morphology_data: MorphologyParseResult
    ) -> None:
        """Extract analysis data from latin12 spans."""
        latin_spans = soup.find_all("span", class_="latin12")
        for span in latin_spans:
            span_text = span.get_text(strip=True)
            pattern = r"\[([^\]]+)\]\{([^}]*)\}"
            matches = re.findall(pattern, span_text)

            for headword, analysis in matches:
                word_analysis = HeritageWordAnalysis(
                    word=headword,
                    lemma=headword,
                    root="",
                    pos="unknown",
                    stem="",
                    meaning=[],
                )
                morphology_data["solutions"].append(
                    {
                        "type": "morphological_analysis",
                        "solution_number": len(morphology_data["solutions"]) + 1,
                        "analyses": [word_analysis],
                        "total_words": 1,
                        "score": 0.0,
                        "metadata": {},
                    }
                )

    def _collect_navy_links(
        self, soup: BeautifulSoup, morphology_data: MorphologyParseResult
    ) -> None:
        """Fallback extraction from Navy links."""
        navy_links = soup.find_all("a", class_="navy")
        for link in navy_links:
            lemma_tag = link.find("i")
            if not lemma_tag:
                continue
            lemma = lemma_tag.get_text(strip=True)
            word_analysis = HeritageWordAnalysis(
                word=lemma,
                lemma=lemma,
                root="",
                pos="unknown",
                stem="",
                meaning=[],
            )
            morphology_data["solutions"].append(
                {
                    "type": "morphological_analysis",
                    "solution_number": len(morphology_data["solutions"]) + 1,
                    "analyses": [word_analysis],
                    "total_words": 1,
                    "score": 0.0,
                    "metadata": {},
                }
            )

    def _combine_analysis(
        self, morphology: MorphologyParseResult, dictionary: HeritageDictionaryLookup
    ) -> CombinedAnalysis:
        """Combine morphology and dictionary results"""
        return {
            "lemma": next(
                (
                    analysis.lemma
                    for solution in morphology.get("solutions", [])
                    for analysis in solution.get("analyses", [])
                    if analysis.lemma
                ),
                None,
            ),
            "pos": next(
                (
                    analysis.pos
                    for solution in morphology.get("solutions", [])
                    for analysis in solution.get("analyses", [])
                    if analysis.pos
                ),
                None,
            ),
            "morphology_analyses": [
                analysis
                for solution in morphology.get("solutions", [])
                for analysis in solution.get("analyses", [])
            ],
            "dictionary_entries": dictionary.get("entries", []),
            "transliteration": dictionary.get("transliteration", {}),
            "root": dictionary.get("root"),
        }

    def lookup_dictionary(self, term: str, dict_id: str = "MW") -> HeritageDictionaryLookup:
        """Look up a term in the dictionary"""
        try:
            result = self.scl.lookup_ascii(term)

            dict_results: HeritageDictionaryLookup = {
                "word": term,
                "dict_id": dict_id,
                "entries": result.get("dictionaries", {}).get(dict_id.lower(), []),
                "transliteration": result.get("transliteration", {}),
                "root": result.get("root"),
            }

            return dict_results

        except Exception as e:
            logger.error("Dictionary lookup failed", term=term, error=str(e))
            return {
                "word": term,
                "dict_id": dict_id,
                "error": str(e),
                "entries": [],
                "transliteration": {},
            }


class HeritageMorphologyService:
    """Service for morphological analysis using sktreader CGI script"""

    def __init__(self, config=None):
        self.config = config
        self.client: HeritageHTTPClient | None = None
        self.parser = MorphologyParser()

    def __enter__(self):
        """Context manager entry"""
        self.client = HeritageHTTPClient(self.config)
        self.client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.client:
            self.client.__exit__(exc_type, exc_val, exc_tb)

    def analyze(
        self,
        text: str,
        encoding: str | None = None,
        max_solutions: int | None = None,
        timeout: int | None = None,
        use_fallback: bool = True,
    ) -> HeritageMorphologyResult:
        """
        Perform morphological analysis on Sanskrit text

        Args:
            text: Sanskrit text to analyze
            encoding: Text encoding (velthuis, itrans, slp1). Default: velthuis
            max_solutions: Maximum number of solutions to return
            timeout: Request timeout in seconds
            use_fallback: Whether to try long vowel variants if initial query fails

        Returns:
            HeritageMorphologyResult with structured analysis
        """
        try:
            if self.client is None:
                self.client = HeritageHTTPClient(self.config)
                self.client.__enter__()

            # Type assertion: client is now guaranteed to be initialized
            assert self.client is not None

            # Try original query first
            result = self._analyze_with_fallback(
                text=text,
                encoding=encoding or self.config.default_encoding if self.config else "velthuis",
                max_solutions=max_solutions or (self.config.max_solutions if self.config else 10),
                timeout=timeout,
                use_fallback=use_fallback,
            )

            logger.info(
                "Morphology analysis completed",
                input_text=text,
                total_solutions=result.total_solutions,
                processing_time=round(result.processing_time, 3),
                fallback_used=getattr(result.metadata, "fallback_used", False),
            )

            return result

        except Exception as e:
            logger.error("Morphology analysis failed", text=text, error=str(e))
            raise HeritageAPIError(f"Morphology analysis failed: {e}")

    def _analyze_with_fallback(
        self,
        text: str,
        encoding: str,
        max_solutions: int,
        timeout: int | None,
        use_fallback: bool,
    ) -> HeritageMorphologyResult:
        """Try original query, with fallback to long vowel variants if needed."""

        # Client is guaranteed to be initialized by calling method
        assert self.client is not None, (
            "Client must be initialized before calling _analyze_with_fallback"
        )

        # Normalize to Velthuis before hitting sktreader to avoid encoding surprises.
        normalized_text, normalized_encoding = self._normalize_for_sktreader(text, encoding)

        # Try original query
        params = HeritageParameterBuilder.build_morphology_params(
            text=normalized_text,
            encoding=normalized_encoding,
            max_solutions=max_solutions,
        )
        html_content = self.client.fetch_cgi_script("sktreader", params=params, timeout=timeout)

        parsed_data = self.parser.parse(html_content)
        has_solutions = bool(parsed_data.get("solutions"))

        # If we got solutions, return immediately even if the HTML contained warning markers.
        if has_solutions:
            return self._build_morphology_result(
                text=text,  # Use original text, not normalized
                parsed_data=parsed_data,
                processing_time=0.0,
            )

        # Check if result indicates unknown/error
        if use_fallback and self._is_unknown_result(html_content):
            # Generate long vowel variants and try them
            variants = self._generate_long_vowel_variants(normalized_text)
            for variant in variants:
                try:
                    fallback_params = HeritageParameterBuilder.build_morphology_params(
                        text=variant,
                        encoding=normalized_encoding,
                        max_solutions=max_solutions,
                    )
                    fallback_html = self.client.fetch_cgi_script(
                        "sktreader", params=fallback_params, timeout=timeout
                    )

                    parsed_fallback = self.parser.parse(fallback_html)
                    if parsed_fallback.get("solutions"):
                        result = self._build_morphology_result(
                            text=text,  # Use original text, not normalized
                            parsed_data=parsed_fallback,
                            processing_time=0.0,
                        )
                        # Add fallback metadata
                        if not result.metadata:
                            result.metadata = {}
                        result.metadata.update(
                            {
                                "fallback_used": True,
                                "original_input": text,
                                "normalized_input": normalized_text,
                                "suggested_input": variant,
                            }
                        )
                        return result

                except Exception:
                    continue

        # If no fallback or fallback didn't work, return parsed (possibly empty) result
        return self._build_morphology_result(
            text=text,  # Use original text, not normalized
            parsed_data=parsed_data,
            processing_time=0.0,
        )

    def _is_unknown_result(self, html_content: str) -> bool:
        """Check if HTML result indicates unknown/error analysis."""
        return "{?}" in html_content or "grey_back" in html_content

    def _generate_long_vowel_variants(self, text: str) -> list[str]:
        """Generate common long vowel variants for fallback."""
        variants = []

        # Common Sanskrit word endings that often need long vowels
        if text.endswith("i") and len(text) > 1:
            variants.append(text + "i")  # agni → agnii
        if text.endswith("a") and len(text) > 1:
            variants.append(text + "a")  # sita → siitaa
        if text.endswith("u") and len(text) > 1:
            variants.append(text + "u")  # guru → guruu

        return variants

    def _normalize_for_sktreader(self, text: str, encoding: str | None) -> tuple[str, str]:
        """
        Normalize any incoming script/transliteration to Velthuis before sending to sktreader.
        """
        target_encoding = "velthuis"
        try:
            from indic_transliteration.detect import detect  # noqa: PLC0415
            from indic_transliteration.sanscript import VELTHUIS, transliterate  # noqa: PLC0415

            detected = encoding or EncodingService.detect_encoding(text) or "ascii"
            source_scheme = detect(text) or detected
            normalized = transliterate(text, source_scheme, VELTHUIS)
            return normalized, target_encoding
        except Exception:
            # Best effort fallback: leave text as-is while marking encoding as Velthuis
            # to avoid DN/IAST params.
            return text, target_encoding

    def _build_morphology_result(
        self, text: str, parsed_data: MorphologyParseResult, processing_time: float
    ) -> HeritageMorphologyResult:
        """Convert parsed data to structured result"""

        solutions = [
            self._build_solution(solution_data)
            for solution_data in parsed_data.get("solutions", [])
        ]
        word_analyses_raw = parsed_data.get("word_analyses", [])
        word_analyses = [
            entry
            if isinstance(entry, HeritageWordAnalysis)
            else HeritageWordAnalysis(
                word=entry.get("word", ""),
                lemma=entry.get("lemma", entry.get("word", "")),
                root=entry.get("root", ""),
                pos=entry.get("pos", ""),
                case=entry.get("case"),
                gender=entry.get("gender"),
                number=entry.get("number"),
                person=self._parse_int(entry.get("person")),
                tense=entry.get("tense"),
                voice=entry.get("voice"),
                mood=entry.get("mood"),
                stem=entry.get("stem", ""),
                meaning=entry.get("meaning", []),
            )
            for entry in word_analyses_raw
        ]

        # DEBUG: Log what we're storing as input_text
        logger.warning(
            "DEBUG: Building morphology result with input_text",
            input_text_to_store=text,
            input_text_repr=repr(text),
            original_parameter=text,
            solutions_count=len(solutions),
        )

        # DEBUG: Log what we're storing as input_text
        logger.warning(
            "DEBUG: Building morphology result with input_text",
            input_text_to_store=text,
            input_text_repr=repr(text),
            original_parameter=text,
            solutions_count=len(solutions),
        )

        return HeritageMorphologyResult(
            input_text=text,
            solutions=solutions,
            word_analyses=word_analyses,
            total_solutions=len(solutions),
            encoding=parsed_data.get("encoding", "velthuis"),
            processing_time=processing_time,
            metadata=parsed_data.get("metadata", {}),
        )

    def _build_solution(self, solution_data: MorphologySolutionDict) -> HeritageSolution:
        """Convert solution data to structured solution"""

        analyses = []
        # Convert all entries to HeritageWordAnalysis
        for entry_data in solution_data.get("analyses", solution_data.get("entries", [])):
            if isinstance(entry_data, HeritageWordAnalysis):
                analyses.append(entry_data)
            elif isinstance(entry_data, dict):
                # Convert dict to HeritageWordAnalysis
                analyses.append(
                    HeritageWordAnalysis(
                        word=entry_data.get("word", ""),
                        lemma=entry_data.get("lemma", entry_data.get("word", "")),
                        root=entry_data.get("root", ""),
                        pos=entry_data.get("pos", ""),
                        case=entry_data.get("case"),
                        gender=entry_data.get("gender"),
                        number=entry_data.get("number"),
                        person=self._parse_int(entry_data.get("person")),
                        tense=entry_data.get("tense"),
                        voice=entry_data.get("voice"),
                        mood=entry_data.get("mood"),
                        stem=entry_data.get("stem", ""),
                        meaning=entry_data.get("meaning", []),
                    )
                )
            else:
                logger.debug("Skipping unsupported analysis entry", entry_type=type(entry_data))
                continue

        return HeritageSolution(
            type=solution_data.get("type", "morphological"),
            analyses=analyses,
            total_words=len(analyses),
            score=solution_data.get("score", 0.0),
            metadata=solution_data.get("metadata", {}),
        )

    def _parse_int(self, value: int | str | None) -> int | None:
        """Parse integer value safely"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def analyze_word(self, word: str, **kwargs) -> HeritageMorphologyResult:
        """Analyze a single word"""
        return self.analyze(word, **kwargs)

    def analyze_sentence(self, sentence: str, **kwargs) -> HeritageMorphologyResult:
        """Analyze a complete sentence"""
        return self.analyze(sentence, **kwargs)

    def batch_analyze(self, words: list[str], **kwargs) -> list[HeritageMorphologyResult]:
        """Analyze multiple words"""
        results = []

        for word in words:
            try:
                result = self.analyze(word, **kwargs)
                results.append(result)
            except Exception as e:
                logger.warning("Failed to analyze word", word=word, error=str(e))
                error_result = HeritageMorphologyResult(
                    input_text=word,
                    solutions=[],
                    word_analyses=[],
                    total_solutions=0,
                    processing_time=0.0,
                    metadata={"error": str(e)},
                )
                results.append(error_result)

        return results
