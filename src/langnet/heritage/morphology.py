import re
from typing import Any

import structlog
from bs4 import BeautifulSoup

from ..cologne.core import SanskritCologneLexicon
from .client import HeritageAPIError, HeritageHTTPClient
from .models import HeritageMorphologyResult, HeritageSolution, HeritageWordAnalysis
from .parameters import HeritageParameterBuilder
from .parsers import MorphologyParser

logger = structlog.get_logger(__name__)


class HeritageDictionaryService:
    """Service combining Heritage morphology with CDSL dictionary lookup"""

    def __init__(self):
        self.scl = SanskritCologneLexicon()
        self.morphology_client = HeritageHTTPClient()

    def lookup_word(self, word: str, dict_id: str = "MW") -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        """Analyze a word with both morphology and dictionary lookup"""
        results = {
            "word": word,
            "morphology": None,
            "dictionary": None,
            "combined_analysis": None,
        }

        try:
            with self.morphology_client as client:
                morph_params = HeritageParameterBuilder.build_morphology_params(
                    text=word,
                    encoding=encoding,
                    max_solutions=max_solutions,
                )
                morph_result = client.fetch_cgi_script("sktreader", morph_params)

                parsed_morphology = self._parse_morphology_response(morph_result)
                results["morphology"] = parsed_morphology

                if parsed_morphology and parsed_morphology.get("lemma"):
                    lemma = parsed_morphology["lemma"]
                    dict_results = self.lookup_word(lemma)
                    results["dictionary"] = dict_results

                    results["combined_analysis"] = self._combine_analysis(
                        parsed_morphology, dict_results
                    )

        except Exception as e:
            logger.error("Word analysis failed", word=word, error=str(e))
            results["error"] = str(e)

        return results

    def _parse_morphology_response(self, html_content: str) -> dict[str, Any] | None:
        """Parse morphology response from Heritage Platform"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            morphology_data: dict[str, Any] = {
                "analyses": [],
                "lemma": None,
                "pos": None,
            }

            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 1:
                        cell_text = cells[0].get_text(strip=True)

                        pattern = r"\[([^\]]+)\]\{([^}]*)\}"
                        matches = re.findall(pattern, cell_text)

                        for match in matches:
                            headword, analysis = match
                            morphology_data["analyses"].append(
                                {
                                    "headword": headword,
                                    "analysis": analysis,
                                }
                            )

                            if not morphology_data["lemma"]:
                                morphology_data["lemma"] = headword

                            if analysis and not morphology_data["pos"]:
                                morphology_data["pos"] = analysis

            return morphology_data if morphology_data["analyses"] else None

        except Exception as e:
            logger.error("Morphology parsing failed", error=str(e))
            return None

    def _combine_analysis(
        self, morphology: dict[str, Any], dictionary: dict[str, Any]
    ) -> dict[str, Any]:
        """Combine morphology and dictionary results"""
        return {
            "lemma": morphology.get("lemma"),
            "pos": morphology.get("pos"),
            "morphology_analyses": morphology.get("analyses", []),
            "dictionary_entries": dictionary.get("entries", []),
            "transliteration": dictionary.get("transliteration", {}),
            "root": dictionary.get("root"),
        }

    def lookup_dictionary(self, term: str, dict_id: str = "MW") -> dict[str, Any]:
        """Look up a term in the dictionary"""
        try:
            result = self.scl.lookup_ascii(term)

            dict_results = {
                "term": term,
                "dict_id": dict_id,
                "entries": result.get("dictionaries", {}).get(dict_id.lower(), []),
                "transliteration": result.get("transliteration", {}),
            }

            return dict_results

        except Exception as e:
            logger.error("Dictionary lookup failed", term=term, error=str(e))
            return {
                "term": term,
                "dict_id": dict_id,
                "error": str(e),
                "entries": [],
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

        # Try original query
        params = HeritageParameterBuilder.build_morphology_params(
            text=text,
            encoding=encoding,
            max_solutions=max_solutions,
        )
        html_content = self.client.fetch_cgi_script("sktreader", params=params, timeout=timeout)

        # Check if result indicates unknown/error
        if use_fallback and self._is_unknown_result(html_content):
            # Generate long vowel variants and try them
            variants = self._generate_long_vowel_variants(text)
            for variant in variants:
                try:
                    fallback_params = HeritageParameterBuilder.build_morphology_params(
                        text=variant,
                        encoding=encoding,
                        max_solutions=max_solutions,
                    )
                    fallback_params = HeritageParameterBuilder.build_morphology_params(
                        text=variant,
                        encoding=encoding,
                        max_solutions=max_solutions,
                    )
                    fallback_html = self.client.fetch_cgi_script(
                        "sktreader", params=fallback_params, timeout=timeout
                    )

                    if not self._is_unknown_result(fallback_html):
                        # Fallback worked, parse and return with metadata
                        parsed_data = self.parser.parse(fallback_html)
                        result = self._build_morphology_result(
                            text=text, parsed_data=parsed_data, processing_time=0.0
                        )
                        # Add fallback metadata
                        if not result.metadata:
                            result.metadata = {}
                        result.metadata.update(
                            {
                                "fallback_used": True,
                                "original_input": text,
                                "suggested_input": variant,
                            }
                        )
                        return result

                except Exception:
                    continue

        # If no fallback or fallback didn't work, parse original result
        parsed_data = self.parser.parse(html_content)
        result = self._build_morphology_result(
            text=text, parsed_data=parsed_data, processing_time=0.0
        )
        return result

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

    def _build_morphology_result(
        self, text: str, parsed_data: dict[str, Any], processing_time: float
    ) -> HeritageMorphologyResult:
        """Convert parsed data to structured result"""

        solutions = []
        for solution_data in parsed_data.get("solutions", []):
            solution = self._build_solution(solution_data)
            solutions.append(solution)

        word_analyses = parsed_data.get("word_analyses", [])

        return HeritageMorphologyResult(
            input_text=text,
            solutions=solutions,
            word_analyses=word_analyses,
            total_solutions=len(solutions),
            encoding=parsed_data.get("encoding", "velthuis"),
            processing_time=processing_time,
            metadata=parsed_data.get("metadata", {}),
        )

    def _build_solution(self, solution_data: dict[str, Any]) -> HeritageSolution:
        """Convert solution data to structured solution"""

        analyses = []
        # Handle new parser format which returns HeritageWordAnalysis objects directly
        for entry_data in solution_data.get("analyses", solution_data.get("entries", [])):
            if hasattr(entry_data, "word"):  # HeritageWordAnalysis object
                # Convert HeritageWordAnalysis to dict for compatibility
                analysis_dict = {
                    "word": entry_data.word,
                    "lemma": entry_data.lemma,
                    "root": entry_data.root,
                    "pos": entry_data.pos,
                    "case": entry_data.case,
                    "gender": entry_data.gender,
                    "number": entry_data.number,
                    "person": entry_data.person,
                    "tense": entry_data.tense,
                    "voice": entry_data.voice,
                    "mood": entry_data.mood,
                    "stem": entry_data.stem,
                    "meaning": entry_data.meaning,
                    "lexicon_refs": entry_data.lexicon_refs,
                    "confidence": entry_data.confidence,
                }
                analysis = self._build_word_analysis(analysis_dict)
            else:  # Dictionary format (legacy)
                analysis = self._build_word_analysis(entry_data)
            analyses.append(analysis)

        return HeritageSolution(
            type=solution_data.get("type", "morphological"),
            analyses=analyses,
            total_words=len(analyses),
            score=solution_data.get("score", 0.0),
            metadata=solution_data.get("metadata", {}),
        )

    def _build_word_analysis(self, entry_data: dict[str, Any]) -> HeritageWordAnalysis:
        """Convert entry data to word analysis"""

        return HeritageWordAnalysis(
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
            meaning=self._parse_meanings(entry_data),
            lexicon_refs=self._parse_lexicon_refs(entry_data),
            confidence=float(entry_data.get("confidence", 0.0)),
        )

    def _parse_int(self, value: Any) -> int | None:
        """Parse integer value safely"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_meanings(self, entry_data: dict[str, Any]) -> list[str]:
        """Parse meaning/definition list"""
        meanings = []

        meaning_fields = ["meaning", "definition", "definitions", "sense"]

        for field in meaning_fields:
            if field in entry_data:
                value = entry_data[field]
                if isinstance(value, list):
                    meanings.extend(value)
                elif isinstance(value, str):
                    meanings.append(value)

        return meanings if meanings else []

    def _parse_lexicon_refs(self, entry_data: dict[str, Any]) -> list[str]:
        """Parse lexicon references"""
        refs = []

        ref_fields = ["lexicon_refs", "references", "refs", "source"]

        for field in ref_fields:
            if field in entry_data:
                value = entry_data[field]
                if isinstance(value, list):
                    refs.extend(value)
                elif isinstance(value, str):
                    refs.append(value)

        return refs if refs else []

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
