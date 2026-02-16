from __future__ import annotations

from collections.abc import Sequence

from query_spec import CanonicalCandidate, NormalizationStep


class LanguageNormalizer:
    """Base interface for language-specific canonicalization."""

    def canonical_candidates(
        self, text: str, steps: list[NormalizationStep]
    ) -> Sequence[CanonicalCandidate]:  # pragma: no cover - interface
        raise NotImplementedError
