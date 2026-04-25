"""French gloss parser for Gaffiot and Heritage French lexicon entries."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from lark import Lark, Token, Tree, Visitor

# Grammar file path
_GRAMMAR_DIR = Path(__file__).parent / "grammars"
_FRENCH_GLOSS_GRAMMAR = _GRAMMAR_DIR / "french_gloss.lark"


class FrenchGloss(TypedDict, total=False):
    """Parsed French gloss/translation."""

    text: str  # Main gloss text
    qualifier: str | None  # Optional qualifier (fig., poet., etc.)
    cross_ref: str | None  # Optional cross-reference


class ParsedFrenchGlosses(TypedDict):
    """Complete parsed French glosses list."""

    glosses: list[FrenchGloss]
    raw_text: str  # Original text


class FrenchGlossTransformer(Visitor):
    """Transforms Lark parse tree into structured glosses."""

    def __init__(self) -> None:
        self.result: list[FrenchGloss] = []

    def gloss_list(self, tree: Tree) -> None:
        """Process complete gloss list."""
        self.result = []
        for child in tree.children:
            if isinstance(child, Tree) and child.data == "gloss":
                gloss = self._process_gloss(child)
                if gloss:
                    self.result.append(gloss)

    def _process_gloss(self, tree: Tree) -> FrenchGloss | None:
        """Process single gloss."""
        gloss: FrenchGloss = {"text": "", "qualifier": None, "cross_ref": None}

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == "qualifier":
                    qual_token = self._find_token(child, "QUALIFIER_TEXT")
                    if qual_token:
                        gloss["qualifier"] = qual_token.value
                elif child.data == "text":
                    text_token = self._find_token(child, "FRENCH_TEXT")
                    if text_token:
                        gloss["text"] = text_token.value.strip()
                elif child.data == "cross_ref":
                    # Extract cross-reference text
                    ref_tokens = self._find_all_tokens(child, "FRENCH_TEXT")
                    if ref_tokens:
                        gloss["cross_ref"] = ref_tokens[0].value.strip()

        # Only return if we have actual text
        if gloss["text"]:
            return gloss
        return None

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


class FrenchGlossParser:
    """Parser for French glosses/translations."""

    def __init__(self) -> None:
        """Initialize parser with Lark grammar."""
        if not _FRENCH_GLOSS_GRAMMAR.exists():
            msg = f"Grammar file not found: {_FRENCH_GLOSS_GRAMMAR}"
            raise FileNotFoundError(msg)

        with open(_FRENCH_GLOSS_GRAMMAR, encoding="utf-8") as f:
            grammar_text = f.read()

        self.parser = Lark(grammar_text, start="gloss_list", parser="lalr")

    def parse(self, text: str) -> ParsedFrenchGlosses:
        """
        Parse French gloss text into structured data.

        Args:
            text: Raw gloss text (e.g., "ardor, caritas" or "fig., amour, passion")

        Returns:
            ParsedFrenchGlosses with list of glosses

        Raises:
            lark.exceptions.LarkError: If parsing fails
        """
        tree = self.parser.parse(text)
        transformer = FrenchGlossTransformer()
        transformer.visit(tree)
        return {"glosses": transformer.result, "raw_text": text}

    def parse_safe(self, text: str) -> ParsedFrenchGlosses | None:
        """
        Parse gloss text, returning None on failure.

        Args:
            text: Raw gloss text

        Returns:
            ParsedFrenchGlosses or None if parsing failed
        """
        try:
            return self.parse(text)
        except Exception:
            return None


def parse_french_glosses(text: str) -> list[str]:
    """
    Parse French gloss text into list of individual glosses.

    Simplified convenience function that returns just the text strings.

    Args:
        text: Raw gloss text (e.g., "ardor, caritas, amor")

    Returns:
        List of gloss strings

    Example:
        >>> parse_french_glosses("ardor, caritas")
        ['ardor', 'caritas']
        >>> parse_french_glosses("fig., amour; passion")
        ['amour', 'passion']
    """
    parser = FrenchGlossParser()
    result = parser.parse_safe(text)

    if result:
        return [gloss["text"] for gloss in result["glosses"] if gloss["text"]]

    # Fallback: simple split on common delimiters
    return [
        g.strip()
        for g in text.replace("¶", ",").replace("\n", ",").replace(";", ",").split(",")
        if g.strip()
    ]


def parse_gaffiot_entry(headword: str, plain_text: str) -> dict[str, object]:
    """
    Parse Gaffiot entry into structured data.

    Args:
        headword: Latin lemma
        plain_text: French gloss text

    Returns:
        Dict with headword, glosses, and parsed structure

    Example:
        >>> parse_gaffiot_entry("amor", "ardor, caritas")
        {'headword': 'amor', 'glosses': ['ardor', 'caritas'], ...}
    """
    parser = FrenchGlossParser()
    parsed = parser.parse_safe(plain_text)

    return {
        "headword": headword,
        "glosses": parse_french_glosses(plain_text),
        "parsed": parsed,
        "raw_text": plain_text,
    }
