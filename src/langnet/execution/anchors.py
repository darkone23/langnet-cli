"""Scoped anchor utilities for universal claims layer.

Anchors are stable identifiers for entities in the semantic graph:
- form: - Surface forms (inflected words)
- interp: - Morphological interpretations (form→lex connections)
- lex: - Lexemes (citation forms with optional POS)
- sense: - Word senses (meaning nodes)

Design Principles:
- Anchors are DETERMINISTIC - same inputs yield same anchor
- Anchors are NORMALIZED - case-insensitive, accent-folded when appropriate
- Anchors encode MINIMAL information - just enough to be unique
- Anchors use STABLE separators - : for scope, # for fragments, → for links

References:
- docs/technical/semantic_triples.md
- docs/technical/triples_txt.md
"""

import unicodedata


def _normalize_surface(text: str) -> str:
    """Normalize surface form for anchor generation.

    Rules:
    - Lowercase
    - NFD normalization (decompose accents)
    - Remove combining diacritics (accents)
    - Fold macrons/breves (ā→a, ă→a)
    - Preserve non-Latin scripts as-is (Devanagari, Greek)

    Args:
        text: Raw surface form

    Returns:
        Normalized form suitable for anchor

    Examples:
        >>> _normalize_surface("LUPUS")
        'lupus'
        >>> _normalize_surface("λόγος")
        'λογος'
        >>> _normalize_surface("agnī")
        'agni'
    """
    # Lowercase
    text = text.lower()

    # NFD normalization (decompose)
    text = unicodedata.normalize("NFD", text)

    # Remove combining diacriticals (accents, macrons, breves)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"  # Mn = Mark, nonspacing
    )

    # NFC normalization (recompose what's left)
    text = unicodedata.normalize("NFC", text)

    return text


def form_anchor(surface: str) -> str:
    """Generate form: anchor for inflected surface form.

    Args:
        surface: Surface form as it appears in text

    Returns:
        Scoped anchor like "form:lupus"

    Examples:
        >>> form_anchor("lupus")
        'form:lupus'
        >>> form_anchor("λόγος")
        'form:λογος'
        >>> form_anchor("ARMA")
        'form:arma'
    """
    normalized = _normalize_surface(surface)
    return f"form:{normalized}"


def lex_anchor(lemma: str, pos: str | None = None) -> str:
    """Generate lex: anchor for lexeme (citation form).

    Args:
        lemma: Citation form (dictionary headword)
        pos: Optional part of speech for disambiguation

    Returns:
        Scoped anchor like "lex:lupus" or "lex:lupus#noun"

    Examples:
        >>> lex_anchor("lupus")
        'lex:lupus'
        >>> lex_anchor("lupus", "noun")
        'lex:lupus#noun'
        >>> lex_anchor("sum", "verb")
        'lex:sum#verb'
    """
    normalized = _normalize_surface(lemma)
    if pos:
        pos_normalized = pos.lower().strip()
        return f"lex:{normalized}#{pos_normalized}"
    return f"lex:{normalized}"


def sense_anchor(lex: str, sense_key: str) -> str:
    """Generate sense: anchor for word sense.

    Args:
        lex: Lexeme anchor (with or without scope prefix)
        sense_key: Stable sense identifier (e.g., hash, source_ref, semantic constant)

    Returns:
        Scoped anchor like "sense:lex:lupus#noun#wild_canine"

    Examples:
        >>> sense_anchor("lex:lupus#noun", "wild_canine")
        'sense:lex:lupus#noun#wild_canine'
        >>> sense_anchor("lupus", "70699593")  # Diogenes sense ID
        'sense:lex:lupus#70699593'
    """
    # Strip lex: prefix if present
    if lex.startswith("lex:"):
        lex = lex[4:]

    return f"sense:lex:{lex}#{sense_key}"


def interp_anchor(form: str, lex: str) -> str:
    """Generate interp: anchor for morphological interpretation.

    The interpretation layer connects inflected forms to lexemes,
    carrying morphological features (case, number, gender, etc.).

    Args:
        form: Form anchor or surface string
        lex: Lex anchor or lemma string

    Returns:
        Scoped anchor like "interp:form:lupus→lex:lupus#noun"

    Examples:
        >>> interp_anchor("form:lupus", "lex:lupus#noun")
        'interp:form:lupus→lex:lupus#noun'
        >>> interp_anchor("lupus", "lupus#noun")
        'interp:form:lupus→lex:lupus#noun'
        >>> interp_anchor("amarem", "amo#verb")
        'interp:form:amarem→lex:amo#verb'
    """
    # Ensure form has scope
    if not form.startswith("form:"):
        form = form_anchor(form)

    # Ensure lex has scope
    if not lex.startswith("lex:"):
        lex = lex_anchor(lex)

    return f"interp:{form}→{lex}"


def parse_anchor(anchor: str) -> dict[str, str]:
    """Parse scoped anchor into components.

    Args:
        anchor: Scoped anchor string

    Returns:
        Dictionary with keys:
        - scope: "form" | "lex" | "sense" | "interp"
        - value: The identifier (without scope prefix)
        - Additional fields depending on scope type

    Examples:
        >>> parse_anchor("form:lupus")
        {'scope': 'form', 'surface': 'lupus'}

        >>> parse_anchor("lex:lupus#noun")
        {'scope': 'lex', 'lemma': 'lupus', 'pos': 'noun'}

        >>> parse_anchor("sense:lex:lupus#noun#wild_canine")
        {'scope': 'sense', 'lex': 'lupus#noun', 'sense_key': 'wild_canine'}

        >>> parse_anchor("interp:form:lupus→lex:lupus#noun")
        {'scope': 'interp', 'form': 'form:lupus', 'lex': 'lex:lupus#noun'}
    """
    if ":" not in anchor:
        raise ValueError(f"Invalid anchor (missing scope): {anchor}")

    scope, rest = anchor.split(":", 1)

    if scope == "form":
        return {"scope": "form", "surface": rest}

    if scope == "lex":
        if "#" in rest:
            lemma, pos = rest.split("#", 1)
            return {"scope": "lex", "lemma": lemma, "pos": pos}
        return {"scope": "lex", "lemma": rest}

    if scope == "sense":
        # sense:lex:lupus#noun#wild_canine
        if not rest.startswith("lex:"):
            raise ValueError(f"Invalid sense anchor (expected lex:): {anchor}")

        lex_part = rest[4:]  # Remove "lex:"
        if "#" not in lex_part:
            raise ValueError(f"Invalid sense anchor (missing sense_key): {anchor}")

        # Find last # separator (sense_key)
        parts = lex_part.rsplit("#", 1)
        lex_id = parts[0]
        sense_key = parts[1]

        return {"scope": "sense", "lex": lex_id, "sense_key": sense_key}

    if scope == "interp":
        # interp:form:lupus→lex:lupus#noun
        if "→" not in rest:
            raise ValueError(f"Invalid interp anchor (missing →): {anchor}")

        form_part, lex_part = rest.split("→", 1)
        return {"scope": "interp", "form": form_part, "lex": lex_part}

    raise ValueError(f"Unknown anchor scope: {scope}")


def extract_lemma(anchor: str) -> str | None:
    """Extract lemma from any anchor type.

    Args:
        anchor: Any scoped anchor

    Returns:
        Lemma string, or None if anchor doesn't contain a lemma

    Examples:
        >>> extract_lemma("lex:lupus#noun")
        'lupus'
        >>> extract_lemma("sense:lex:lupus#noun#wild_canine")
        'lupus'
        >>> extract_lemma("interp:form:lupus→lex:lupus#noun")
        'lupus'
        >>> extract_lemma("form:lupus")
        None
    """
    parsed = parse_anchor(anchor)

    if parsed["scope"] == "lex":
        return parsed["lemma"]

    if parsed["scope"] == "sense":
        lex_id = parsed["lex"]
        if "#" in lex_id:
            return lex_id.split("#")[0]
        return lex_id

    if parsed["scope"] == "interp":
        lex_part = parsed["lex"]
        if lex_part.startswith("lex:"):
            lex_part = lex_part[4:]
        if "#" in lex_part:
            return lex_part.split("#")[0]
        return lex_part

    return None


def is_form_anchor(anchor: str) -> bool:
    """Check if anchor is a form: anchor."""
    return anchor.startswith("form:")


def is_lex_anchor(anchor: str) -> bool:
    """Check if anchor is a lex: anchor."""
    return anchor.startswith("lex:")


def is_sense_anchor(anchor: str) -> bool:
    """Check if anchor is a sense: anchor."""
    return anchor.startswith("sense:")


def is_interp_anchor(anchor: str) -> bool:
    """Check if anchor is an interp: anchor."""
    return anchor.startswith("interp:")
