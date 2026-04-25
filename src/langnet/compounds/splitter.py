from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Compound classification thresholds
SIMPLE_COMPOUND_PARTS = 2  # tatpuruṣa compounds have exactly 2 parts
COMPLEX_COMPOUND_MIN_PARTS = 3  # complex compounds have 3+ parts


@dataclass
class TokenComponent:
    """Represents a component of a compound word."""

    surface: str
    normalized: str
    role: str  # "initial", "medial", "final"
    lemma: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "normalized": self.normalized,
            "role": self.role,
            "lemma": self.lemma,
        }


class CompoundSplitter:
    """Handles splitting of Sanskrit compound words."""

    def is_hyphenated_compound(self, text: str) -> bool:
        """Check if token contains hyphen indicating compound."""
        # Simple check: contains hyphen not at start or end
        return "-" in text and not text.startswith("-") and not text.endswith("-")

    def split_hyphenated(self, text: str) -> list[TokenComponent]:
        """Split hyphenated compounds into components with roles."""
        if not self.is_hyphenated_compound(text):
            return []

        parts = text.split("-")
        if len(parts) == SIMPLE_COMPOUND_PARTS:
            # Simple tatpuruṣa compound: initial + final
            return [
                TokenComponent(
                    surface=parts[0],
                    normalized=parts[0],  # Will be normalized later
                    role="initial",
                ),
                TokenComponent(surface=parts[1], normalized=parts[1], role="final"),
            ]
        elif len(parts) >= COMPLEX_COMPOUND_MIN_PARTS:
            # Complex compound with multiple components
            components = []
            for i, part in enumerate(parts):
                if i == 0:
                    role = "initial"
                elif i == len(parts) - 1:
                    role = "final"
                else:
                    role = "medial"

                components.append(TokenComponent(surface=part, normalized=part, role=role))
            return components

        return []

    def identify_compound_type(self, components: list[str]) -> str:
        """Identify compound type based on components."""
        if len(components) == SIMPLE_COMPOUND_PARTS:
            # For now, assume tatpuruṣa for all 2-component compounds
            # This is the most common type in Sanskrit
            return "tatpuruṣa"
        elif len(components) >= COMPLEX_COMPOUND_MIN_PARTS:
            return "complex"
        return "unknown"

    def get_compound_query(self, components: list[TokenComponent]) -> str:
        """
        Generate Heritage Platform query for compound.
        Joins components without hyphen for morphology analysis.
        """
        # Join normalized forms without hyphen
        normalized_parts = [c.normalized for c in components]
        return "".join(normalized_parts)

    def get_component_queries(self, components: list[TokenComponent]) -> list[str]:
        """Generate dictionary queries for each component."""
        return [c.normalized for c in components]
