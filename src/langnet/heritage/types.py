from __future__ import annotations

from typing import TypedDict

from langnet.types import JSONMapping


class MorphologyPattern(TypedDict):
    word: str
    analysis: str


class MorphologySegment(TypedDict, total=False):
    css_class: str | None
    text: str


class MorphologyAnalysisDict(TypedDict, total=False):
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
    type: str
    solution_number: int
    analyses: list[MorphologyAnalysisDict]
    entries: list[MorphologyAnalysisDict]
    patterns: list[MorphologyPattern]
    total_words: int
    score: float
    metadata: JSONMapping


class MorphologyParseResult(TypedDict):
    solutions: list[MorphologySolutionDict]
    word_analyses: list[MorphologyAnalysisDict]
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
    lemma: str | None
    pos: str | None
    morphology_analyses: list[MorphologyAnalysisDict]
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
