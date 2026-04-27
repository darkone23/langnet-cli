from __future__ import annotations

BASE_SYSTEM = (
    "You translate french lexicon entries into english for classical language students. "
    "All french phrases should be translated to english unless instructed otherwise. "
    "Preserve transliterated tokens and sense numbering. Respond with concise prose."
)

SANSKRIT_HINTS = [
    (
        "Keep abbreviations and any Sanskrit tokens unchanged. "
        "Preserve layout, punctuation, and style."
    ),
    (
        "Do not modify formatting, leave [brackets] as brackets and (parens) as parens: "
        "do not omit formatting. Leave sanskrit IAST diacritics intact."
    ),
    "Do not expand abbreviations or enhance beyond material found in the source text.",
    "Avoid translation of cross-language synonym examples prefixed with ; fr.",
    "All french phrases must be translated. Do not emit french text except for synonym clusters.",
    (
        "If input is single sanskrit term return it unmodified. "
        "Do not add clarifying explanations not found in source."
    ),
    (
        "example word definition: apacasi tu ne sais pas cuisiner. => "
        "apacasi you do not know how to cook."
    ),
    "example synonym cluster: lat. lupus; fr. loup. => lat. lupus; fr. loup.",
    (
        "example formatting preservation: aṃśa [act. aś_1] m. (ce qu'on obtient) "
        "part, partie, portion, division, part d'héritage => aṃśa [act. aś_1] m. "
        "(that which is obtained) share, portion, portion, division, share of inheritance"
    ),
]

LATIN_HINTS = [
    (
        "Keep abbreviations and Latin terms/authors/works unchanged. "
        "Preserve numbering, punctuation, and style. Do not expand abbreviations."
    ),
    (
        "Do not add markdown styling such as bold, italics, or numbering, "
        "nor enhance with content not in the source text."
    ),
    (
        "Sometimes an entry is full of classic latin citations with french translations "
        "of those citations. Please keep the latin citations intact and provide english "
        "translations from the french."
    ),
    (
        "If input is single latin term or letter return it unmodified. "
        "Do not add clarifying explanations not found in source."
    ),
    "All french phrases must be translated. Do not emit untranslated french text.",
    (
        "French text is sometimes surrounded formatting or intermixed with latin citations, "
        "you may have to hunt for french phrases needing translating."
    ),
    "Be sure to do a double pass and select the best option.",
    "example of pass-through: n. ae 2 => n. ae 2",
]


def default_hints_for_mode(mode: str) -> list[str]:
    return LATIN_HINTS if mode.lower() == "latin" else SANSKRIT_HINTS


def default_hints_for_language(language: str) -> list[str]:
    return LATIN_HINTS if language.lower() == "lat" else SANSKRIT_HINTS
