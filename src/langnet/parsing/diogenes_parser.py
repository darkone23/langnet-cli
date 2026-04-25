"""Diogenes entry parser using Lark grammars for clean extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from lark import Lark, Token, Tree, Visitor

# Grammar file path (relative to this module)
_GRAMMAR_DIR = Path(__file__).parent / "grammars"
_DIOGENES_GRAMMAR = _GRAMMAR_DIR / "diogenes_entry.lark"


class SenseBlock(TypedDict, total=False):
    """Parsed sense block from a dictionary entry."""

    level: str  # "I", "A", "1", etc.
    qualifier: str | None  # "lit.", "transf.", "poet."
    gloss: str  # The actual definition text
    citations: list[str]  # Author abbreviations


class EntryHeader(TypedDict, total=False):
    """Parsed entry header information."""

    lemma: str  # Base lemma form
    principal_parts: list[str]  # Principal parts (genitive, infinitive, etc.)
    pos: str | None  # Part of speech
    gender: str | None  # Gender marker
    root: str | None  # Etymology root


class ParsedEntry(TypedDict, total=False):
    """Complete parsed dictionary entry."""

    header: EntryHeader
    senses: list[SenseBlock]


class PerseusMorph(TypedDict, total=False):
    """Parsed Perseus morphology analysis."""

    forms: list[str]  # List of inflected forms
    pos: str  # Part of speech
    features: list[str]  # Morphological features (case, number, gender, etc.)


class DiogenesEntryTransformer(Visitor):
    """Transforms Lark parse tree into structured dictionary."""

    def __init__(self) -> None:
        self.result: dict[str, Any] = {}

    def entry(self, tree: Tree) -> None:
        """Process complete entry."""
        header: EntryHeader = {}
        senses: list[SenseBlock] = []

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == "entry_header":
                    header = self._process_header(child)
                elif child.data == "sense_block":
                    senses.append(self._process_sense_block(child))

        self.result = {"header": header, "senses": senses}

    def _process_header(self, tree: Tree) -> EntryHeader:
        """Process entry header from flattened structure."""
        header: EntryHeader = {"lemma": "", "principal_parts": []}

        # First LEMMA is the base lemma
        lemmas = self._find_all_tokens(tree, "LEMMA")
        if lemmas:
            header["lemma"] = lemmas[0].value

        # Process INFLECTION tokens as principal parts
        inflection_tokens = self._find_all_tokens(tree, "INFLECTION")
        header["principal_parts"] = [tok.value for tok in inflection_tokens]

        # Check for GENDER or POS tokens
        gender_tok = self._find_token(tree, "GENDER")
        if gender_tok:
            header["gender"] = gender_tok.value

        pos_tok = self._find_token(tree, "POS")
        if pos_tok:
            header["pos"] = pos_tok.value

        # Check for etymology
        for child in tree.children:
            if isinstance(child, Tree) and child.data == "etymology":
                root_lemmas = self._find_all_tokens(child, "LEMMA")
                if root_lemmas:
                    header["root"] = root_lemmas[0].value

        return header

    def _process_sense_block(self, tree: Tree) -> SenseBlock:  # noqa: C901
        """Process sense block."""
        sense: SenseBlock = {"level": "", "qualifier": None, "gloss": "", "citations": []}

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == "sense_marker":
                    level_token = self._find_token(child)
                    if level_token:
                        sense["level"] = level_token.value
                elif child.data == "qualifier":
                    qualifier_token = self._find_token(child, "QUALIFIER_TEXT")
                    if qualifier_token:
                        # Strip the trailing period from qualifier (e.g., "lit." -> "lit")
                        sense["qualifier"] = qualifier_token.value.rstrip(".")
                elif child.data == "gloss_text":
                    gloss_token = self._find_token(child, "GLOSS")
                    if gloss_token:
                        sense["gloss"] = gloss_token.value.strip()
                elif child.data == "citation_block":
                    citations_token = self._find_token(child, "CITATIONS")
                    if citations_token:
                        # Split citations by semicolon and strip periods
                        cit_text = citations_token.value
                        sense["citations"] = [
                            c.strip().rstrip(".") for c in cit_text.split(";") if c.strip()
                        ]

        return sense

    def _find_token(self, tree: Tree, token_type: str | None = None) -> Token | None:
        """Find first token of given type in tree."""
        for child in tree.children:
            if isinstance(child, Token):
                if token_type is None or child.type == token_type:
                    return child
            elif isinstance(child, Tree):
                found = self._find_token(child, token_type)
                if found:
                    return found
        return None

    def _find_all_tokens(self, tree: Tree, token_type: str) -> list[Token]:
        """Find all tokens of given type in tree."""
        tokens: list[Token] = []

        for child in tree.children:
            if isinstance(child, Token) and child.type == token_type:
                tokens.append(child)
            elif isinstance(child, Tree):
                tokens.extend(self._find_all_tokens(child, token_type))

        return tokens


class DiogenesEntryParser:
    """Parser for Diogenes dictionary entries using Lark grammar."""

    def __init__(self) -> None:
        """Initialize parser with Lark grammar."""
        if not _DIOGENES_GRAMMAR.exists():
            msg = f"Grammar file not found: {_DIOGENES_GRAMMAR}"
            raise FileNotFoundError(msg)

        with open(_DIOGENES_GRAMMAR, encoding="utf-8") as f:
            grammar_text = f.read()

        self.parser = Lark(grammar_text, start="entry", parser="lalr")

    def parse(self, text: str) -> ParsedEntry:
        """
        Parse dictionary entry text into structured data.

        Args:
            text: Raw entry text (cleaned from HTML)

        Returns:
            ParsedEntry with header and sense blocks

        Raises:
            lark.exceptions.LarkError: If parsing fails
        """
        tree = self.parser.parse(text)
        transformer = DiogenesEntryTransformer()
        transformer.visit(tree)
        return transformer.result  # type: ignore[return-value]

    def parse_safe(self, text: str) -> ParsedEntry | None:
        """
        Parse entry text, returning None on failure.

        Args:
            text: Raw entry text

        Returns:
            ParsedEntry or None if parsing failed
        """
        try:
            return self.parse(text)
        except Exception:
            return None


def parse_diogenes_entry(text: str) -> ParsedEntry:
    """
    Parse Diogenes dictionary entry text.

    Convenience function that creates parser and parses text.

    Args:
        text: Raw entry text (cleaned from HTML)

    Returns:
        ParsedEntry with structured data

    Example:
        >>> text = "lupus, -i, m. I. a wolf A. lit., Cic."
        >>> entry = parse_diogenes_entry(text)
        >>> entry["header"]["lemma"]
        'lupus'
    """
    parser = DiogenesEntryParser()
    return parser.parse(text)


def parse_perseus_morph(text: str) -> PerseusMorph | None:
    """
    Parse Perseus morphology analysis.

    Format: "lupus, lupi: noun masc nom sg"

    Args:
        text: Perseus morphology text

    Returns:
        PerseusMorph with forms and features, or None if parse fails
    """
    try:
        # Simple regex-based parsing for now
        # TODO: Add Lark grammar for perseus_morph rule
        if ":" not in text:
            return None

        forms_part, tags_part = text.split(":", 1)
        forms = [f.strip() for f in forms_part.split(",")]
        tags = tags_part.strip().split()

        if not tags:
            return None

        pos = tags[0]
        features = tags[1:] if len(tags) > 1 else []

        return {
            "forms": forms,
            "pos": pos,
            "features": features,
        }
    except Exception:
        return None
