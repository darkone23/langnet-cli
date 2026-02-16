from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SktSearchResult:
    original_query: str = ""
    bare_query: str = ""
    canonical_text: str = ""
    canonical_sanskrit: str = ""
    match_method: str = ""
    entry_url: str = ""


@dataclass(slots=True)
class MonierWilliamsResult:
    original_query: str = ""
    bare_query: str = ""
    canonical_sanskrit: str = ""
    match_method: str = ""
    entry_url: str = ""


@dataclass(slots=True)
class MorphologyPart:
    stem: str = ""
    ending: str = ""
    analysis: str = ""


@dataclass(slots=True)
class MorphologyAnalysis:
    form: str = ""
    stem: str = ""
    lemma: str = ""
    grammar: str = ""
    parts: list[MorphologyPart] | None = None
