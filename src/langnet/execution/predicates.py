"""Canonical predicate constants for universal claims layer.

This module defines the stable vocabulary of predicates used across all tools
when projecting tool-specific facts into universal semantic triples.

Design Principle:
- Predicates are STABLE semantic constants (never change meaning)
- Tools emit different predicates, but use same vocabulary
- Scoping rules constrain which predicates apply to which anchor types

References:
- docs/technical/semantic_triples.md
- docs/technical/triples_txt.md
- docs/technical/predicates_evidence.md
- docs/plans/active/tool-fact-indexing.md
"""

# =============================================================================
# LINKING PREDICATES
# =============================================================================
# Connect different anchor types (form → interp → lex → sense)

HAS_INTERPRETATION = "has_interpretation"
"""Links form: anchor to interp: anchor.

Example: form:lupus → has_interpretation → interp:form:lupus→lex:lupus#noun
"""

REALIZES_LEXEME = "realizes_lexeme"
"""Links interp: anchor to lex: anchor.

Example: interp:form:lupus→lex:lupus#noun → realizes_lexeme → lex:lupus#noun
"""

INFLECTION_OF = "inflection_of"
"""Direct form→lex link (when no intermediate interpretation needed).

Example: form:lupus → inflection_of → lex:lupus
Note: Prefer has_interpretation + realizes_lexeme for full provenance.
"""

# =============================================================================
# LEXICAL PREDICATES
# =============================================================================
# Describe lexemes and senses

HAS_SENSE = "has_sense"
"""Links lex: anchor to sense: anchor.

Example: lex:lupus#noun → has_sense → sense:lex:lupus#noun#wild_canine
"""

GLOSS = "gloss"
"""Textual definition of a sense.

Example: sense:lex:lupus#noun#wild_canine → gloss → "wolf, wild canine"
Scope: sense: anchors (NOT lex: anchors - use has_sense to link)
"""

HAS_CITATION = "has_citation"
"""Usage example or textual reference.

Example: lex:lupus → has_citation → "Verg. E. 2, 63"
Scope: lex: or sense: anchors
"""

HAS_FREQUENCY = "has_frequency"
"""Corpus frequency indicator.

Example: lex:lupus → has_frequency → {"count": 147, "corpus": "perseus_lat"}
"""

VARIANT_FORM = "variant_form"
"""Alternative surface realization of same lexeme.

Example: lex:lupus → variant_form → "lup"
Scope: lex: anchors
"""

VARIANT_OF = "variant_of"
"""Inverse of variant_form (bidirectional).

Example: lex:lup → variant_of → lex:lupus
"""

HAS_ROOT = "has_root"
"""Etymological or morphological root.

Example: lex:agni → has_root → "√ag" (burn)
"""

HAS_DOMAIN = "has_domain"
"""Semantic domain classification.

Example: sense:... → has_domain → "religion"
Values: "religion", "military", "technical", "poetic", etc.
"""

HAS_REGISTER = "has_register"
"""Stylistic register classification.

Example: sense:... → has_register → "vedic"
Values: "vedic", "classical", "epic", "technical", etc.
"""

# =============================================================================
# FORM PREDICATES
# =============================================================================
# Describe surface forms

HAS_FORM = "has_form"
"""Surface string representation.

Example: form:lupus → has_form → "lupus"
(Usually redundant with anchor itself, but useful for variants)
"""

HAS_PRONUNCIATION = "has_pronunciation"
"""Phonetic transcription.

Example: lex:λόγος → has_pronunciation → "/ˈlo.ɡos/"
"""

# =============================================================================
# MORPHOLOGY PREDICATES
# =============================================================================
# Grammatical features (typically on interp: anchors)

HAS_POS = "has_pos"
"""Part of speech.

Example: interp:... → has_pos → "noun"
Values: "noun", "verb", "adjective", "pronoun", "particle", etc.
Scope: interp: or lex: anchors
"""

HAS_CASE = "has_case"
"""Grammatical case.

Example: interp:... → has_case → "nominative"
Values: "nominative", "accusative", "genitive", "dative", "ablative",
        "locative", "vocative", "instrumental"
Scope: interp: anchors (inflected form property)
"""

HAS_NUMBER = "has_number"
"""Grammatical number.

Example: interp:... → has_number → "singular"
Values: "singular", "dual", "plural"
"""

HAS_GENDER = "has_gender"
"""Grammatical gender.

Example: interp:... → has_gender → "masculine"
Values: "masculine", "feminine", "neuter"
"""

HAS_PERSON = "has_person"
"""Grammatical person.

Example: interp:... → has_person → "first"
Values: "first", "second", "third"
"""

HAS_TENSE = "has_tense"
"""Grammatical tense.

Example: interp:... → has_tense → "present"
Values: "present", "imperfect", "perfect", "pluperfect", "future", etc.
"""

HAS_VOICE = "has_voice"
"""Grammatical voice.

Example: interp:... → has_voice → "active"
Values: "active", "middle", "passive", "medio-passive"
"""

HAS_MOOD = "has_mood"
"""Grammatical mood.

Example: interp:... → has_mood → "indicative"
Values: "indicative", "subjunctive", "optative", "imperative", "infinitive"
"""

HAS_DEGREE = "has_degree"
"""Degree of comparison.

Example: interp:... → has_degree → "comparative"
Values: "positive", "comparative", "superlative"
"""

HAS_DECLENSION = "has_declension"
"""Declension class.

Example: lex:lupus → has_declension → "2"
Values: "1", "2", "3", "3i", "4", "5" (Latin); "1", "2", "3" (Greek)
"""

HAS_CONJUGATION = "has_conjugation"
"""Conjugation class.

Example: lex:amo → has_conjugation → "1"
Values: "1", "2", "3", "3io", "4", "irregular"
"""

HAS_MORPHOLOGY = "has_morphology"
"""Structured morphology object from a source analyzer.

Example: form:agni → has_morphology → {"case": "nominative", "number": "singular"}
Scope: form: anchors when the morphology belongs to a specific surface form.
"""

# =============================================================================
# ESCAPE HATCH
# =============================================================================
# For tool-specific metadata that doesn't fit universal schema

HAS_FEATURE = "has_feature"
"""Generic feature bag for tool-specific extras.

Example: interp:... → has_feature → {"whitaker_age": "Classical", "freq": "A"}

Use sparingly - prefer specific predicates above when possible.
This preserves information loss during universal projection while
keeping the core schema clean.
"""

# =============================================================================
# SCOPING RULES
# =============================================================================
# Which predicates are allowed on which anchor types

FORM_PREDICATES = {
    HAS_FORM,
    HAS_INTERPRETATION,
    INFLECTION_OF,  # Direct link (discouraged, use has_interpretation instead)
    HAS_MORPHOLOGY,
}
"""Predicates valid for form: anchors."""

INTERP_PREDICATES = {
    REALIZES_LEXEME,
    HAS_POS,
    HAS_CASE,
    HAS_NUMBER,
    HAS_GENDER,
    HAS_PERSON,
    HAS_TENSE,
    HAS_VOICE,
    HAS_MOOD,
    HAS_DEGREE,
    HAS_FEATURE,
}
"""Predicates valid for interp: anchors (morphological interpretation layer)."""

LEX_PREDICATES = {
    HAS_SENSE,
    HAS_POS,  # Lexeme-level POS (when unambiguous)
    HAS_DECLENSION,
    HAS_CONJUGATION,
    HAS_ROOT,
    HAS_FREQUENCY,
    HAS_CITATION,
    VARIANT_FORM,
    VARIANT_OF,
    HAS_PRONUNCIATION,
    HAS_FEATURE,
}
"""Predicates valid for lex: anchors."""

SENSE_PREDICATES = {
    GLOSS,
    HAS_CITATION,
    HAS_DOMAIN,
    HAS_REGISTER,
    HAS_FREQUENCY,
    HAS_FEATURE,
}
"""Predicates valid for sense: anchors."""


def validate_predicate_scope(anchor: str, predicate: str) -> bool:
    """Check if predicate is valid for the given anchor type.

    Args:
        anchor: Scoped anchor (e.g., "form:lupus", "lex:lupus#noun")
        predicate: Predicate constant (e.g., HAS_CASE)

    Returns:
        True if predicate is allowed for this anchor type

    Examples:
        >>> validate_predicate_scope("form:lupus", HAS_INTERPRETATION)
        True
        >>> validate_predicate_scope("form:lupus", HAS_CASE)
        False  # Case lives on interp:, not form:
        >>> validate_predicate_scope("lex:lupus", GLOSS)
        False  # Gloss lives on sense:, not lex: (use has_sense to link)
    """
    if anchor.startswith("form:"):
        return predicate in FORM_PREDICATES
    if anchor.startswith("interp:"):
        return predicate in INTERP_PREDICATES
    if anchor.startswith("lex:"):
        return predicate in LEX_PREDICATES
    if anchor.startswith("sense:"):
        return predicate in SENSE_PREDICATES
    return False  # Unknown anchor type
