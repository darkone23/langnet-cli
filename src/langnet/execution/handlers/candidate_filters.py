from __future__ import annotations

from difflib import SequenceMatcher

MIN_FALLBACK_SIMILARITY = 0.65


def close_fallback_candidates(
    headword: str,
    candidates: list[str],
    *,
    normalize,
    min_similarity: float = MIN_FALLBACK_SIMILARITY,
) -> list[str]:
    """Keep broad fallback candidates close enough to the searched surface."""
    headword_key = normalize(headword)
    if not headword_key:
        return candidates

    filtered: list[str] = []
    for candidate in candidates:
        candidate_key = normalize(candidate)
        if not candidate_key:
            filtered.append(candidate)
            continue
        if headword_key == candidate_key:
            filtered.append(candidate)
            continue
        similarity = SequenceMatcher(None, headword_key, candidate_key).ratio()
        if similarity >= min_similarity:
            filtered.append(candidate)
    return filtered
