from __future__ import annotations

BASE_SYSTEM = (
    "You translate French lexicon entries into English for classical language students. "
    "Translate all ordinary French prose into English by substituting English for the "
    "French span. Preserve original casing, original punctuation, source-language "
    "tokens, abbreviations, sense numbering, separators, spacing, and layout. Work as "
    "a meticulous, conservative, source-faithful dictionary translator. Use only "
    "meanings present in the source entry."
)

SANSKRIT_HINTS = [
    (
        "This is DICO Sanskrit dictionary material in French. Translate French words and "
        "French phrases into clear English for Sanskrit readers. Translate every French "
        "explanation into English, including French common nouns and labels wherever "
        "they appear. Work in a meticulous, source-faithful style."
    ),
    (
        "Preserve layout, abbreviations, Sanskrit tokens, IAST diacritics, [brackets], "
        "(parens), and structural markers. Preserve original casing and preserve "
        "original punctuation."
    ),
    "Use only meanings present in the source entry. Keep abbreviations compact.",
    "Keep cross-language synonym examples prefixed with ; fr. as synonym clusters.",
    "Render French prose in English while retaining explicit synonym-cluster labels.",
    ("If input is single sanskrit term return it unmodified. Return only the source term."),
    "example word definition: apacasi cuisine rituelle. => apacasi ritual cooking.",
    "example synonym cluster: lat. lupus; fr. loup. => lat. lupus; fr. loup.",
    (
        "example formatting preservation: aṃśa [act. aś_1] m. (ce qu'on obtient) "
        "part, partie, portion, division, part d'héritage => aṃśa [act. aś_1] m. "
        "(that which is obtained) share, portion, portion, division, share of inheritance"
    ),
]

LATIN_HINTS = [
    (
        "This is Gaffiot Latin dictionary material in French. Translate French words and "
        "French phrases into clear English for Latin readers. Translate every French "
        "explanation into English, including French common nouns and labels wherever "
        "they appear. Work in a meticulous, source-faithful style."
    ),
    (
        "Preserve layout, Latin terms, author/work abbreviations, numbering, punctuation, "
        "and structural markers. Preserve original casing and preserve original "
        "punctuation. Keep abbreviations compact and unchanged."
    ),
    (
        "Translate French explanations and French translations of cited Latin. Keep Latin "
        "citations intact. Retain bibliographic citations that distinguish senses, "
        "registers, constructions, or examples."
    ),
    (
        "If input is single latin term or letter return it unmodified. "
        "Return only the source term or letter."
    ),
    "Render French prose in English.",
    (
        "French text is sometimes surrounded formatting or intermixed with latin citations, "
        "you may have to hunt for french phrases needing translating."
    ),
    "Use only meanings present in the source entry.",
    "Before responding, check once that ordinary French prose has been rendered in English.",
    "example of pass-through: n. ae 2 => n. ae 2",
]


GREEK_BAILLY_HINTS = [
    (
        "This is Bailly Greek dictionary material in French. Translate French words and "
        "French phrases into clear English for classical Greek readers. Translate every "
        "French explanation into English, including French common nouns and labels "
        "wherever they appear. Work in a meticulous, source-faithful style."
    ),
    (
        "Preserve layout, Greek headwords, Greek examples, Latin abbreviations, author "
        "abbreviations, sense numbering, and structural markers. Preserve original "
        "casing and preserve original punctuation."
    ),
    (
        "Copy Greek text, Latin citations, author abbreviations, work abbreviations, "
        "book numbers, section numbers, and punctuation exactly as they appear in the "
        "source entry."
    ),
    (
        "Render idiomatic French as natural English meaning while preserving the entry's "
        "sense boundaries."
    ),
    (
        "Render compact French labels and abbreviations into compact English labels: "
        "Postér. => Later; c. => with; c. à d. => i.e.; comme => as; "
        "synon. => syn.; dureté => hardness; insensibilité => insensibility; "
        "rocher => rock; rhéteur => rhetorician; apôtre => apostle; "
        "particul. => in particular; propr. => properly; en gén. => in general; "
        "p. suite => by extension; p. ext. => by extension; p. opp. à => opposed to."
    ),
    (
        "Return general English glosses and dictionary prose. Use only meanings, "
        "etymologies, and explanations present in the source entry."
    ),
    (
        "Retain bibliographic citations that organize or qualify a sense. Preserve the "
        "source's citation text and sense structure."
    ),
    (
        "If the source marks a usage category, register, figurative sense, proverb, "
        "or proper name, keep that distinction and translate the French label."
    ),
    (
        "Before responding, check once that ordinary French dictionary prose has been "
        "rendered in English and that Greek/Latin source tokens remain unchanged."
    ),
]


def default_hints_for_mode(mode: str) -> list[str]:
    return LATIN_HINTS if mode.lower() == "latin" else SANSKRIT_HINTS


def default_hints_for_language(language: str) -> list[str]:
    normalized = language.lower()
    if normalized == "lat":
        return LATIN_HINTS
    if normalized == "grc":
        return GREEK_BAILLY_HINTS
    return SANSKRIT_HINTS
