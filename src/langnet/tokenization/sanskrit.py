from __future__ import annotations

import re
from dataclasses import dataclass, field
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


@dataclass
class Token:
    """Represents a single token in Sanskrit text."""

    surface_form: str
    normalized_form: str
    position: int
    encoding: str
    is_compound: bool = False
    compound_type: str | None = None
    components: list[TokenComponent] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface_form,
            "normalized": self.normalized_form,
            "position": self.position,
            "encoding": self.encoding,
            "is_compound": self.is_compound,
            "compound_type": self.compound_type,
            "components": [c.to_dict() for c in self.components] if self.components else None,
        }


@dataclass
class TokenizedPassage:
    """Represents a fully tokenized Sanskrit passage."""

    original_text: str
    language: str = "san"
    tokens: list[Token] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "language": self.language,
            "tokens": [t.to_dict() for t in self.tokens],
            "metadata": self.metadata,
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


class SanskritTokenizer:
    """Tokenizer for Sanskrit text with compound word handling."""

    def __init__(self):
        self.compound_splitter = CompoundSplitter()

    def tokenize(self, text: str) -> TokenizedPassage:
        """
        Split Sanskrit text into tokens with compound analysis.

        Args:
            text: Sanskrit text to tokenize

        Returns:
            TokenizedPassage containing tokens and metadata
        """
        # Clean and normalize whitespace
        cleaned = re.sub(r"\s+", " ", text.strip())

        # Basic tokenization: split on whitespace
        raw_tokens = cleaned.split(" ")

        # Process each token
        tokens = []
        for position, surface_form in enumerate(raw_tokens):
            if not surface_form:
                continue

            token = Token(
                surface_form=surface_form,
                normalized_form=surface_form,  # Will be normalized later
                position=position,
                encoding="unknown",  # Will be detected later
            )

            # Check for compounds
            if self.compound_splitter.is_hyphenated_compound(surface_form):
                token.is_compound = True
                components = self.compound_splitter.split_hyphenated(surface_form)
                if components:
                    token.components = components
                    # Identify compound type
                    component_texts = [c.surface for c in components]
                    token.compound_type = self.compound_splitter.identify_compound_type(
                        component_texts
                    )

            tokens.append(token)

        return TokenizedPassage(original_text=text, tokens=tokens)

    def get_compound_queries(self, passage: TokenizedPassage) -> tuple[list[str], list[str]]:
        """
        Generate queries for dictionary lookup.

        Returns:
            Tuple of (compound_queries, component_queries)
            - compound_queries: joined forms for morphology analysis
            - component_queries: individual components for dictionary lookup
        """
        compound_queries = []
        component_queries = []

        for token in passage.tokens:
            # Add the token itself (will be normalized later)
            compound_queries.append(token.normalized_form)

            # Add components if it's a compound
            if token.is_compound and token.components:
                # Generate joined compound query
                joined = self.compound_splitter.get_compound_query(token.components)
                if joined:
                    compound_queries.append(joined)

                # Add individual components
                components = self.compound_splitter.get_component_queries(token.components)
                component_queries.extend(components)
            else:
                # Non-compound token is also a component query
                component_queries.append(token.normalized_form)

        # Remove duplicates while preserving order
        unique_compound = []
        seen_compound = set()
        for q in compound_queries:
            if q not in seen_compound:
                seen_compound.add(q)
                unique_compound.append(q)

        unique_component = []
        seen_component = set()
        for q in component_queries:
            if q not in seen_component:
                seen_component.add(q)
                unique_component.append(q)

        return unique_compound, unique_component
