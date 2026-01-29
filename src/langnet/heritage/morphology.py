import time
from typing import Dict, Any, Optional, List

import structlog

from .client import HeritageHTTPClient, HeritageAPIError
from .parameters import HeritageParameterBuilder
from .models import (
    HeritageMorphologyResult,
    HeritageSolution,
    HeritageWordAnalysis,
)
from .parsers import MorphologyParser

logger = structlog.get_logger(__name__)


class HeritageMorphologyService:
    """Service for morphological analysis using sktreader CGI script"""

    def __init__(self, config=None):
        self.config = config
        self.client = None
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
        encoding: Optional[str] = None,
        max_solutions: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> HeritageMorphologyResult:
        """
        Perform morphological analysis on Sanskrit text

        Args:
            text: Sanskrit text to analyze
            encoding: Text encoding (velthuis, itrans, slp1). Default: velthuis
            max_solutions: Maximum number of solutions to return
            timeout: Request timeout in seconds

        Returns:
            HeritageMorphologyResult with structured analysis
        """
        start_time = time.time()

        try:
            # Ensure client is initialized
            if self.client is None:
                self.client = HeritageHTTPClient(self.config)
                self.client.__enter__()

            # Build parameters
            params = HeritageParameterBuilder.build_morphology_params(
                text=text,
                encoding=encoding or self.config.default_encoding if self.config else "velthuis",
                max_solutions=max_solutions or (self.config.max_solutions if self.config else 10),
            )

            # Make CGI request
            html_content = self.client.fetch_cgi_script("sktreader", params=params, timeout=timeout)

            # Parse response
            parsed_data = self.parser.parse(html_content)

            # Convert to structured result
            result = self._build_morphology_result(
                text=text, parsed_data=parsed_data, processing_time=time.time() - start_time
            )

            logger.info(
                "Morphology analysis completed",
                input_text=text,
                total_solutions=result.total_solutions,
                processing_time=round(result.processing_time, 3),
            )

            return result

        except Exception as e:
            logger.error("Morphology analysis failed", text=text, error=str(e))
            raise HeritageAPIError(f"Morphology analysis failed: {e}")

    def _build_morphology_result(
        self, text: str, parsed_data: Dict[str, Any], processing_time: float
    ) -> HeritageMorphologyResult:
        """Convert parsed data to structured result"""

        # Extract solutions
        solutions = []
        for solution_data in parsed_data.get("solutions", []):
            solution = self._build_solution(solution_data)
            solutions.append(solution)

        # Extract word analyses
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

    def _build_solution(self, solution_data: Dict[str, Any]) -> HeritageSolution:
        """Convert solution data to structured solution"""

        analyses = []
        for entry_data in solution_data.get("entries", []):
            analysis = self._build_word_analysis(entry_data)
            analyses.append(analysis)

        return HeritageSolution(
            type=solution_data.get("type", "morphological"),
            analyses=analyses,
            total_words=len(analyses),
            score=solution_data.get("score", 0.0),
            metadata=solution_data.get("metadata", {}),
        )

    def _build_word_analysis(self, entry_data: Dict[str, Any]) -> HeritageWordAnalysis:
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

    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse integer value safely"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_meanings(self, entry_data: Dict[str, Any]) -> List[str]:
        """Parse meaning/definition list"""
        meanings = []

        # Try different field names
        meaning_fields = ["meaning", "definition", "definitions", "sense"]

        for field in meaning_fields:
            if field in entry_data:
                value = entry_data[field]
                if isinstance(value, list):
                    meanings.extend(value)
                elif isinstance(value, str):
                    meanings.append(value)

        return meanings if meanings else []

    def _parse_lexicon_refs(self, entry_data: Dict[str, Any]) -> List[str]:
        """Parse lexicon references"""
        refs = []

        # Try different field names
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

    def batch_analyze(self, words: List[str], **kwargs) -> List[HeritageMorphologyResult]:
        """Analyze multiple words"""
        results = []

        for word in words:
            try:
                result = self.analyze(word, **kwargs)
                results.append(result)
            except Exception as e:
                logger.warning("Failed to analyze word", word=word, error=str(e))
                # Create error result
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
