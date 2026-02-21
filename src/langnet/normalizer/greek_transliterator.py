from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from betacode import conv as betacode_conv  # type: ignore[import]
from lark import Lark, Transformer  # type: ignore[import]

GREEK_LOWER_A = 0x0370
GREEK_UPPER_END = 0x03FF
PAIR_LEN = 2


@dataclass(frozen=True)
class GreekTransliteration:
    search_key: str  # Greek letters, diacriticless, sigma normalized to σ
    betacode: str  # Uppercase betacode-like (no accents)
    display: str | None = None  # Placeholder for future breathing/accents


class _GreekTransformer(Transformer):
    """
    Map transliteration tokens to Greek letters and betacode.
    """

    def start(self, items):
        # Propagate list of (greek, betacode) tuples
        return items

    letter_map = {
        "a": ("α", "A"),
        "b": ("β", "B"),
        "g": ("γ", "G"),
        "d": ("δ", "D"),
        "e": ("ε", "E"),
        "z": ("ζ", "Z"),
        # Bare 'h' often signals rough breathing; ignore for search key
        "h": ("", ""),
        "i": ("ι", "I"),
        "k": ("κ", "K"),
        "l": ("λ", "L"),
        "m": ("μ", "M"),
        "n": ("ν", "N"),
        "x": ("ξ", "C"),  # betacode C for xi
        "o": ("ο", "O"),
        "p": ("π", "P"),
        "r": ("ρ", "R"),
        "s": ("σ", "S"),
        "t": ("τ", "T"),
        "u": ("υ", "U"),
        "y": ("υ", "U"),  # accept y as upsilon
        "f": ("φ", "F"),
        "c": ("κ", "K"),  # lax mapping for c→k
        "v": ("β", "B"),  # lax mapping for v→beta
        "w": ("ω", "W"),
        "q": ("θ", "Q"),  # allow q→theta
    }

    digraph_map = {
        "ph": ("φ", "F"),
        "ch": ("χ", "X"),
        "th": ("θ", "Q"),
        "ps": ("ψ", "Y"),
        "rh": ("ρ", "R"),  # breathing ignored in search_key
        "ei": ("ει", "EI"),
        "ai": ("αι", "AI"),
        "oi": ("οι", "OI"),
        "eu": ("ευ", "EU"),
        "au": ("αυ", "AU"),
        "ou": ("ου", "OU"),
        "ui": ("υι", "UI"),
    }

    macron_map = {
        "ē": ("η", "H"),
        "ê": ("η", "H"),
        "ō": ("ω", "W"),
        "ô": ("ω", "W"),
    }

    def __default_token__(self, token):
        text = token.value.lower()
        if token.type == "DIGRAPH":
            return self.digraph_map.get(text, ("", ""))
        if token.type == "VOWEL_MACRON":
            return self.macron_map.get(text, ("", ""))
        if token.type == "LETTER":
            return self.letter_map.get(text, ("", ""))
        return ("", "")


_PARSER: Lark | None = None


def _get_parser() -> Lark:
    """
    Lazily construct the transliteration parser once per process.
    """
    global _PARSER  # noqa: PLW0603
    if _PARSER is None:
        grammar_path = Path(__file__).with_name("greek_transliterator.lark")
        grammar = grammar_path.read_text(encoding="utf-8")
        _PARSER = Lark(grammar, start="start", parser="lalr")
    return _PARSER


def _flatten(pairs: Iterable[tuple[str, str]]) -> tuple[str, str]:
    greek: list[str] = []
    beta: list[str] = []
    for item in pairs:
        if hasattr(item, "children"):
            children = getattr(item, "children", None)
            if isinstance(children, Iterable):
                for child in children:
                    if not isinstance(child, tuple) or len(child) != PAIR_LEN:
                        continue
                    g, b = child
                    if g or b:
                        greek.append(g)
                        beta.append(b)
                continue
        if not isinstance(item, tuple) or len(item) != PAIR_LEN:
            continue
        g, b = item
        if g or b:
            greek.append(g)
            beta.append(b)
    return "".join(greek), "".join(beta)


def _normalize_sigma(word: str) -> str:
    if not word:
        return word
    if word.endswith("σ") or word.endswith("ς"):
        return word[:-1] + "σ"
    return word


def transliterate(text: str) -> GreekTransliteration:
    """
    Best-effort Latin → Greek transliteration for search.

    Produces a diacriticless Greek search key and a betacode-like uppercase
    rendering. Breathings/accents are intentionally omitted for determinism.
    """
    if not text:
        return GreekTransliteration(search_key="", betacode="", display=None)

    parser = _get_parser()
    transformer = _GreekTransformer()
    tree = parser.parse(text.lower())
    mapped_tree = transformer.transform(tree)
    # The transformer returns a Tree; flatten children to pairs
    mapped = mapped_tree.children if hasattr(mapped_tree, "children") else mapped_tree
    greek, beta = _flatten(mapped)
    # Normalize final sigma for search
    search_key = _normalize_sigma(greek)
    # For display, prefer final sigma form if we had one
    display = greek[:-1] + ("ς" if greek.endswith(("σ", "ς")) else greek[-1:]) if greek else None
    return GreekTransliteration(search_key=search_key, betacode=beta, display=display)


def contains_greek(text: str) -> bool:
    """Detect if any character is in the Greek block."""
    return any(GREEK_LOWER_A <= ord(ch) <= GREEK_UPPER_END for ch in text)


def _greek_to_betacode(word: str) -> str:
    """
    Unicode polytonic Greek → betacode using betacode.conv if available.
    Falls back to a plain transliteration when the library is missing.
    """
    try:
        return betacode_conv.uni_to_beta(word)
    except Exception:
        pass
    # Fallback: strip to basic letters without diacritics
    mapping = {
        "α": "A",
        "β": "B",
        "γ": "G",
        "δ": "D",
        "ε": "E",
        "ζ": "Z",
        "η": "H",
        "θ": "Q",
        "ι": "I",
        "κ": "K",
        "λ": "L",
        "μ": "M",
        "ν": "N",
        "ξ": "C",
        "ο": "O",
        "π": "P",
        "ρ": "R",
        "σ": "S",
        "ς": "S",
        "τ": "T",
        "υ": "U",
        "φ": "F",
        "χ": "X",
        "ψ": "Y",
        "ω": "W",
    }
    return "".join(mapping.get(ch.lower(), "") for ch in word if ch.strip())


def transliterate_variants(text: str) -> list[GreekTransliteration]:
    """
    Produce strict transliteration plus a small set of loose variants
    (omega/eta expansions) for better recall when macrons are omitted.
    """
    base = transliterate(text)
    variants: dict[str, GreekTransliteration] = {}
    if base.search_key:
        variants[base.search_key] = base

    prioritized = _prioritized_eta_variants(text, base.search_key)

    for variant in _eta_omega_variants(base.search_key):
        if variant not in variants:
            variants[variant] = GreekTransliteration(
                search_key=_normalize_sigma(variant),
                betacode=_greek_to_betacode(variant),
                display=variant,
            )

    ordered_keys = list(dict.fromkeys(prioritized + list(variants.keys())))
    return [variants[k] for k in ordered_keys if k in variants]


def _prioritized_eta_variants(raw_text: str, base_key: str) -> list[str]:
    out: list[str] = []
    if raw_text.lower().startswith("h") and base_key.startswith("ε"):
        eta_variant = _replace_first(base_key, "ε", "η")
        if eta_variant:
            out.append(eta_variant)
    if base_key.endswith("ε"):
        terminal_eta = base_key[:-1] + "η"
        out.append(terminal_eta)
    return out


def _eta_omega_variants(base_key: str) -> list[str]:
    variants: list[str] = []
    omega_variant = _replace_first_nonfinal(base_key, "ο", "ω")
    if omega_variant:
        variants.append(omega_variant)
    eta_variant = _replace_first_nonfinal(base_key, "ε", "η")
    if eta_variant:
        variants.append(eta_variant)
    if base_key.endswith("ε"):
        variants.append(base_key[:-1] + "η")
    return variants


def _replace_first(src: str, target: str, replacement: str) -> str | None:
    if target not in src:
        return None
    chars = list(src)
    for i, ch in enumerate(chars):
        if ch == target:
            chars[i] = replacement
            return "".join(chars)
    return None


def _replace_first_nonfinal(src: str, target: str, replacement: str) -> str | None:
    chars = list(src)
    for i, ch in enumerate(chars):
        if ch == target and i < len(chars) - 1:
            chars[i] = replacement
            return "".join(chars)
    return None
