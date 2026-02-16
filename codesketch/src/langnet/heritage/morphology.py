import re
from collections.abc import Iterable
from dataclasses import replace
from typing import cast

import structlog
from bs4 import BeautifulSoup
from langnet.types import JSONMapping

from ..cologne.core import SanskritCologneLexicon
from ..foster.apply import (
    _map_tag_to_foster,
    _normalize_sanskrit_tag,
)
from ..foster.sanskrit import (
    FOSTER_SANSKRIT_CASES,
    FOSTER_SANSKRIT_GENDERS,
    FOSTER_SANSKRIT_NUMBERS,
)
from .client import HeritageAPIError, HeritageHTTPClient
from .encoding_service import EncodingService
from .models import HeritageMorphologyResult, HeritageSolution, HeritageWordAnalysis
from .parameters import HeritageParameterBuilder
from .parsers import MorphologyParser
from .types import (
    CombinedAnalysis,
    HeritageDictionaryLookup,
    MorphologyParseResult,
    MorphologySegment,
    MorphologySolutionDict,
    WordAnalysisBundle,
)

logger = structlog.get_logger(__name__)


def _get_foster_codes(analysis: HeritageWordAnalysis) -> dict[str, str]:
    """Map HeritageWordAnalysis features to Foster grammar codes."""
    foster_codes: dict[str, str] = {}

    if analysis.case:
        case_val = _normalize_sanskrit_tag(analysis.case)
        case_mapped = _map_tag_to_foster(case_val, [FOSTER_SANSKRIT_CASES])
        if case_mapped:
            foster_codes["case"] = case_mapped

    if analysis.gender:
        gender_val = _normalize_sanskrit_tag(analysis.gender)
        gender_mapped = _map_tag_to_foster(gender_val, [FOSTER_SANSKRIT_GENDERS])
        if gender_mapped:
            foster_codes["gender"] = gender_mapped

    if analysis.number:
        number_val = _normalize_sanskrit_tag(analysis.number)
        number_mapped = _map_tag_to_foster(number_val, [FOSTER_SANSKRIT_NUMBERS])
        if number_mapped:
            foster_codes["number"] = number_mapped

    return foster_codes


def _segments_from_metadata(metadata: dict) -> list[MorphologySegment]:
    """Extract the raw segments list stored by the HTML extractor."""
    if not metadata:
        return []
    segments = metadata.get("segments")
    if isinstance(segments, dict):
        segments = segments.get("data")
    if isinstance(segments, list):
        # Copy to avoid accidental mutation
        return cast(
            list[MorphologySegment],
            [
                {"css_class": seg.get("css_class"), "text": seg.get("text")}
                for seg in segments
                if isinstance(seg, dict)
            ],
        )
    return []


def _normalize_color_class(css_class: str | None) -> str | None:
    """Map Heritage CSS class names to a base color token."""
    if not css_class:
        return None
    cls = css_class.lower()
    if cls.endswith("_back"):
        cls = cls.removesuffix("_back")
    color_keys = {
        "yellow": "yellow",
        "blue": "blue",
        "light_blue": "light_blue",  # Sky blue - pronouns
        "deep_sky": "deep_sky",  # Deep sky blue - pronouns
        "cyan": "cyan",
        "magenta": "magenta",
        "lavender": "lavender",
        "orange": "orange",
        "red": "red",
        "carmin": "red",  # Carmine red - verbs/finite forms
        "mauve": "mauve",
        "salmon": "salmon",
        "green": "green",
        "lawngreen": "green",  # Lawn green - another green variant
        "grey": "grey",
        "gray": "grey",
        "chamois": "beige",  # Chamois/beige - general background/table
        "pink": "pink",  # Pink - annotations/solution numbers
    }
    for key, val in color_keys.items():
        if key in cls:
            return val
    return cls or None


# Heritage CSS color meanings based on Gérard Huet's Sanskrit Heritage Platform
# See: https://sanskrit.inria.fr/
COLOR_MEANINGS: dict[str, str] = {
    # Nominals (Blue family)
    "blue": "noun or adjective",  # Standard inflected noun (Subanta)
    "light_blue": "pronoun",  # Light blue / sky blue - Sarvanāman
    "deep_sky": "pronoun",  # Deep sky blue - alternative pronoun color
    "cyan": "final compound member",  # Ifc - compound final
    # Verbs (Red)
    "red": "finite verb",  # Tiṅanta - dynamic action
    # Structure colors
    "yellow": "compound stem",  # Pūrvapada - initial/medial compound member
    "mauve": "indeclinable",  # Avyaya - words that never change form
    "lavender": "preverb or preposition",
    "green": "vocative",  # Sambodhana - calling/direct address
    "orange": "periphrastic or cvi stem",
    "magenta": "phonetic or sandhi",
    "salmon": "special infinitive (tu-form)",
    "grey": "unknown morphology",
    # Additional colors from sktparser
    "beige": "general background or table",  # Chamois/beige background
    "pink": "annotation or solution number",  # Solution numbering
}


def _segment_tokens(
    segments: Iterable[MorphologySegment], *, allowed_classes: set[str] | None = None
) -> list[tuple[str | None, str]]:
    """Return (class, text) pairs. Optionally filter by class."""
    tokens: list[tuple[str | None, str]] = []
    for seg in segments:
        css_class = (seg.get("css_class") or "").lower() if isinstance(seg, dict) else ""
        if css_class == "latin12":
            continue  # skip embedded pattern text
        if allowed_classes is not None and css_class not in allowed_classes:
            continue
        text = (seg.get("text") or "").strip()
        if text:
            tokens.append((css_class or None, text))
    return tokens


def _is_arrow_token(txt: str) -> bool:
    """Check if text is an arrow token indicating sandhi output."""
    return txt in {"→", "->", "=>"}


def _extract_words_from_segments(segments: list[MorphologySegment]) -> list[dict[str, str | None]]:
    """Extract component words (with color hints) from segments."""
    words: list[dict[str, str | None]] = []
    seen_words: set[str] = set()

    for cls, text in _segment_tokens(segments, allowed_classes=None):
        if _is_arrow_token(text):
            continue
        if " " in text:
            continue
        # Treat any non-empty, non-boundary token as a word candidate
        if len(text) > 1 and text not in seen_words:
            seen_words.add(text)
            color = _normalize_color_class(cls)
            words.append(
                {
                    "word": text,
                    "color": color,
                    "color_meaning": COLOR_MEANINGS.get(color or "", None),
                }
            )

    return words


def _find_nearest_token(
    segments: list[MorphologySegment], start_idx: int, direction: int
) -> str | None:
    """Find the nearest non-boundary token in the given direction from start_idx."""
    j = start_idx + direction
    while 0 <= j < len(segments):
        nxt = segments[j]
        nxt_text = (nxt.get("text") or "").strip()
        if nxt_text and nxt_text not in {"|", "→", "->", "=>"}:
            return nxt_text
        j += direction
    return None


def _find_output_after_arrow(segments: list[MorphologySegment], start_idx: int) -> str | None:
    """Find the sandhi output token after the arrow following start_idx."""
    j = start_idx + 1
    arrow_idx = None
    while 0 <= j < len(segments):
        nxt_text = (segments[j].get("text") or "").strip()
        if nxt_text in {"→", "->", "=>"}:
            arrow_idx = j
            break
        j += 1

    # If no arrow, fallback to first token after boundary
    if arrow_idx is None:
        return _find_nearest_token(segments, start_idx, 1)

    k = arrow_idx + 1
    while 0 <= k < len(segments):
        nxt_text = (segments[k].get("text") or "").strip()
        if nxt_text:
            return nxt_text
        k += 1
    return None


def _extract_sandhi_rules(
    segments: list[MorphologySegment],
) -> list[dict[str, str | list[str] | None]]:
    """Extract sandhi transformations using the '|' boundary marker."""
    sandhi_rules: list[dict[str, str | list[str] | None]] = []

    for idx, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        if text != "|":
            continue

        left = _find_nearest_token(segments, idx, -1)
        right = _find_nearest_token(segments, idx, 1)
        output = _find_output_after_arrow(segments, idx)

        # Only add sandhi rule if we have valid left and right tokens
        if left is not None and right is not None:
            sandhi_rules.append(
                {
                    "input": [left, right],
                    "output": output,
                    "type": "sandhi",
                }
            )

    return sandhi_rules


def _parse_compound_segments(
    segments: list[MorphologySegment],
) -> tuple[list[dict[str, str | None]], list[dict[str, str | list[str] | None]]]:
    """Parse Heritage segments into component words (with color hints) and sandhi info."""
    if not segments:
        return [], []

    words = _extract_words_from_segments(segments)
    sandhi_rules = _extract_sandhi_rules(segments)

    return words, sandhi_rules


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
                normalized_input=normalized_text,
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
                            normalized_input=normalized_text,
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
            normalized_input=normalized_text,
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

        Uses Heritage-compatible converter to match the exact format expected by Heritage Platform.
        """
        target_encoding = "velthuis"
        try:
            # Use our Heritage-compatible converter instead of the buggy library
            normalized = EncodingService.to_velthuis(text)
            return normalized, target_encoding
        except Exception:
            # Best effort fallback: leave text as-is while marking encoding as Velthuis
            # to avoid DN/IAST params.
            return text, target_encoding

    def _build_morphology_result(
        self,
        text: str,
        parsed_data: MorphologyParseResult,
        processing_time: float,
        normalized_input: str | None = None,
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
                compound_role=entry.get("compound_role"),
                color=entry.get("color"),
                color_meaning=entry.get("color_meaning"),
            )
            for entry in word_analyses_raw
        ]

        metadata = parsed_data.get("metadata", {}) or {}
        if normalized_input and metadata.get("normalized_input") is None:
            metadata = {**metadata, "normalized_input": normalized_input}

        return HeritageMorphologyResult(
            input_text=text,
            solutions=solutions,
            word_analyses=word_analyses,
            total_solutions=len(solutions),
            encoding=parsed_data.get("encoding", "velthuis"),
            processing_time=processing_time,
            metadata=metadata,
        )

    def _build_solution(self, solution_data: MorphologySolutionDict) -> HeritageSolution:
        """Convert solution data to structured solution"""

        analyses = []
        metadata = solution_data.get("metadata", {}) or {}
        segments = _segments_from_metadata(metadata)
        compound_words, sandhi_rules = _parse_compound_segments(segments)
        sol_color = _normalize_color_class(cast(str | None, metadata.get("color")))

        # Convert all entries to HeritageWordAnalysis
        for entry_data in solution_data.get("analyses", solution_data.get("entries", [])):
            if isinstance(entry_data, HeritageWordAnalysis):
                # Fill color from solution if missing
                if sol_color and not entry_data.color:
                    updated = replace(
                        entry_data,
                        color=sol_color,
                        color_meaning=COLOR_MEANINGS.get(sol_color or "", None),
                    )
                else:
                    updated = entry_data
                # Apply Foster codes if not already present
                if not updated.foster_codes:
                    updated.foster_codes = cast(JSONMapping, _get_foster_codes(updated))
                analyses.append(updated)
            elif isinstance(entry_data, dict):
                # Convert dict to HeritageWordAnalysis
                analysis = HeritageWordAnalysis(
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
                    compound_role=entry_data.get("compound_role"),
                    color=entry_data.get("color") or sol_color,
                    color_meaning=entry_data.get("color_meaning")
                    or COLOR_MEANINGS.get((entry_data.get("color") or sol_color) or "", None),
                )
                # Apply Foster codes
                analysis.foster_codes = cast(JSONMapping, _get_foster_codes(analysis))
                analyses.append(analysis)
            else:
                logger.debug("Skipping unsupported analysis entry", entry_type=type(entry_data))
                continue

        analyses = self._merge_compound_members(analyses, compound_words)

        # Remove segments from metadata before creating solution
        metadata_without_segments = {k: v for k, v in metadata.items() if k != "segments"}

        return HeritageSolution(
            type=solution_data.get("type", "morphological"),
            analyses=analyses,
            total_words=len(analyses),
            score=solution_data.get("score", 0.0),
            metadata=metadata_without_segments,
            sandhi=cast(list[JSONMapping] | None, sandhi_rules) if sandhi_rules else None,
            is_compound=len(compound_words) > 1,
        )

    def _parse_int(self, value: int | str | None) -> int | None:
        """Parse integer value safely"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _merge_compound_members(
        self, analyses: list[HeritageWordAnalysis], compound_words: list[dict[str, str | None]]
    ) -> list[HeritageWordAnalysis]:
        """Expand analyses with compound member data derived from segments."""
        if not compound_words:
            return analyses

        merged: list[HeritageWordAnalysis] = []
        template = analyses[0] if analyses else None

        def _role(idx: int, total: int) -> str | None:
            if total <= 1:
                return None
            if idx == 0:
                return "initial"
            if idx == total - 1:
                return "final"
            return "medial"

        for idx, word_info in enumerate(compound_words):
            word = (
                word_info.get("word", "") if isinstance(word_info, dict) else str(word_info)
            ) or ""
            color = word_info.get("color") if isinstance(word_info, dict) else None
            color_meaning = word_info.get("color_meaning") if isinstance(word_info, dict) else None
            source = analyses[idx] if idx < len(analyses) else template
            if source:
                role = source.compound_role or _role(idx, len(compound_words))
                effective_color = color or source.color
                effective_color_meaning = color_meaning or source.color_meaning
                merged.append(
                    replace(
                        source,
                        word=word,
                        lemma=source.lemma or word,
                        compound_role=role,
                        color=effective_color,
                        color_meaning=effective_color_meaning,
                    )
                )
            else:
                merged.append(
                    HeritageWordAnalysis(
                        word=word,
                        lemma=word,
                        root="",
                        pos="unknown",
                        stem="",
                        meaning=[],
                        compound_role=_role(idx, len(compound_words)),
                        color=color,
                        color_meaning=color_meaning,
                    )
                )

        return merged

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
