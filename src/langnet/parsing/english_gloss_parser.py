"""Simple English gloss parser for GPT-translated dictionary entries."""

from __future__ import annotations


def parse_english_glosses(text: str) -> list[str]:
    """
    Parse English gloss text (e.g., from GPT translation) into individual glosses.

    Handles common separators: comma, semicolon, newline.
    Simple but effective for GPT-translated French dictionaries.

    Args:
        text: English gloss text (e.g., "love, passion; desire")

    Returns:
        List of individual English glosses

    Example:
        >>> parse_english_glosses("love, passion; desire")
        ['love', 'passion', 'desire']
        >>> parse_english_glosses("wolf\\ngreedy person")
        ['wolf', 'greedy person']
    """
    if not text:
        return []

    # Replace common separators with comma
    normalized = text.replace("\n", ",").replace(";", ",").replace("¶", ",")

    # Split and clean
    glosses = [g.strip() for g in normalized.split(",") if g.strip()]

    return glosses


def enrich_with_gpt_translation(
    entry_data: dict, french_field: str = "plain_text", target_field: str = "gpt_translation"
) -> dict:
    """
    Placeholder for enriching entry with GPT translation.

    In practice, this would:
    1. Take French text from french_field
    2. Call GPT API to translate
    3. Parse the English translation
    4. Store in target_field

    Args:
        entry_data: Dict with French text field
        french_field: Name of field containing French text
        target_field: Name of field to store English translation

    Returns:
        Updated dict with parsed GPT translation

    Example:
        >>> entry = {"headword": "amor", "plain_text": "amour, passion"}
        >>> # In real use: enriched = enrich_with_gpt_translation(entry)
        >>> # Result: {"headword": "amor", "plain_text": "...", "gpt_translation": {...}}
    """
    french_text = entry_data.get(french_field, "")

    if not french_text:
        return entry_data

    # TODO: Call GPT API here
    # For now, return placeholder structure
    return {
        **entry_data,
        target_field: {
            "source": french_text,
            "translated": None,  # Would be GPT output
            "parsed_glosses": [],  # Would be parse_english_glosses(gpt_output)
            "needs_translation": True,
        },
    }
