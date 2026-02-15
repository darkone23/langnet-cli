from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from langnet.types import JSONMapping

if TYPE_CHECKING:
    from langnet.heritage.models import HeritageWordAnalysis


class MorphologyPattern(TypedDict):
    word: str
    analysis: str


class MorphologySegment(TypedDict, total=False):
    css_class: str | None
    text: str


class MorphologyAnalysisDict(TypedDict, total=False):
    """Dict representation of morphology analysis - used only at parse boundaries."""

    word: str
    lemma: str
    root: str
    pos: str
    case: str | None
    gender: str | None
    number: str | None
    person: int | None
    tense: str | None
    voice: str | None
    mood: str | None
    stem: str
    meaning: list[str]
    analysis: str
    expanded_analysis: str


class MorphologySolutionDict(TypedDict, total=False):
    """Solution dict - analyses are always HeritageWordAnalysis objects."""

    type: str
    solution_number: int
    analyses: list[HeritageWordAnalysis]
    entries: list[HeritageWordAnalysis]
    patterns: list[MorphologyPattern]
    total_words: int
    score: float
    metadata: JSONMapping
    sandhi: JSONMapping
    is_compound: bool


class MorphologyParseResult(TypedDict):
    """Parse result - word_analyses are always HeritageWordAnalysis objects."""

    solutions: list[MorphologySolutionDict]
    word_analyses: list[HeritageWordAnalysis]
    total_solutions: int
    encoding: str
    metadata: JSONMapping


class HeritageDictionaryLookup(TypedDict, total=False):
    word: str
    dict_id: str
    entries: list[JSONMapping]
    transliteration: JSONMapping
    root: str | None
    error: str


class CombinedAnalysis(TypedDict, total=False):
    """Combined analysis - morphology_analyses are always HeritageWordAnalysis objects."""

    lemma: str | None
    pos: str | None
    morphology_analyses: list[HeritageWordAnalysis]
    dictionary_entries: list[JSONMapping]
    transliteration: JSONMapping
    root: str | None


class WordAnalysisBundle(TypedDict, total=False):
    word: str
    morphology: MorphologyParseResult | None
    dictionary: HeritageDictionaryLookup | None
    combined_analysis: CombinedAnalysis | None
    error: str


class CanonicalResult(TypedDict, total=False):
    canonical_text: str | None
    canonical_sanskrit: str | None
    match_method: str
    original_query: str
    bare_query: str
    entry_url: str
