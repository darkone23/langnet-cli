from __future__ import annotations

import json
from typing import Any

from .sanskrit import SanskritTokenizer, TokenizedPassage


class TokenAnalysisService:
    """
    Service for analyzing Sanskrit passages with full tokenization pipeline.
    """

    def __init__(self):
        self.tokenizer = SanskritTokenizer()

    def analyze_passage(self, text: str) -> dict[str, Any]:
        """
        Full pipeline analysis of Sanskrit passage.

        Steps:
        1. Tokenize text into tokens
        2. Split hyphenated compounds
        3. Normalize all tokens to Velthuis format
        4. Generate dictionary queries

        Args:
            text: Sanskrit text to analyze

        Returns:
            Dictionary with full analysis including tokens and queries
        """
        # Step 1: Tokenization
        passage = self.tokenizer.tokenize(text)

        # Step 2: Normalize tokens
        self._normalize_tokens(passage)

        # Step 3: Generate queries
        compound_queries, component_queries = self.tokenizer.get_compound_queries(passage)

        # Step 4: Prepare output
        return {
            "original_text": passage.original_text,
            "language": passage.language,
            "tokens": [t.to_dict() for t in passage.tokens],
            "dictionary_queries": {
                "compound_forms": compound_queries,
                "component_forms": component_queries,
            },
            "metadata": {
                "token_count": len(passage.tokens),
                "compound_count": sum(1 for t in passage.tokens if t.is_compound),
                "normalization_applied": True,
            },
        }

    def _normalize_tokens(self, passage: TokenizedPassage) -> None:
        """
        Apply normalization to all tokens in passage.
        Converts IAST to Velthuis format for Heritage Platform.
        """
        # Basic IAST to Velthuis conversion
        iast_to_velthuis = {
            "ṛ": "R",
            "ā": "aa",
            "ṣ": "S",
            "ṭ": "T",
            "ḥ": "H",
            "ṅ": "N",
            "ñ": "J",
            "ṇ": "N",
            "ś": "z",
            "ṁ": "M",
            "ḷ": "L",
            "ḹ": "LL",
            "ṝ": "RR",
        }

        for token in passage.tokens:
            # Simple normalization: convert IAST diacritics to Velthuis
            normalized = token.surface_form
            for iast, velthuis in iast_to_velthuis.items():
                normalized = normalized.replace(iast, velthuis)

            # Handle common IAST to Velthuis patterns
            normalized = normalized.replace("kṣ", "kS")
            normalized = normalized.replace("ch", "c")  # Simple approximation

            token.normalized_form = normalized
            token.encoding = "velthuis"

            # Normalize components too
            if token.components:
                for component in token.components:
                    comp_normalized = component.surface
                    for iast, velthuis in iast_to_velthuis.items():
                        comp_normalized = comp_normalized.replace(iast, velthuis)
                    comp_normalized = comp_normalized.replace("kṣ", "kS")
                    component.normalized = comp_normalized

    def to_json(self, text: str) -> str:
        """Return analysis as JSON string."""
        result = self.analyze_passage(text)
        return json.dumps(result, indent=2, ensure_ascii=False)
