from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

CTSV2_URN_PREFIX = "urn:ctsv2:"
CTSV2_URI_SCHEME = "ctsv2"
DEFAULT_INCIPIT_WORDS = 3

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_GREEK_TRANSLITERATION = str.maketrans(
    {
        "α": "a",
        "β": "b",
        "γ": "g",
        "δ": "d",
        "ε": "e",
        "ζ": "z",
        "η": "e",
        "θ": "th",
        "ι": "i",
        "κ": "k",
        "λ": "l",
        "μ": "m",
        "ν": "n",
        "ξ": "x",
        "ο": "o",
        "π": "p",
        "ρ": "r",
        "σ": "s",
        "ς": "s",
        "τ": "t",
        "υ": "u",
        "φ": "ph",
        "χ": "ch",
        "ψ": "ps",
        "ω": "o",
    }
)


@dataclass(frozen=True)
class Ctsv2Resource:
    text_id: str
    ref: str | None = None
    range: str | None = None
    witness: str | None = None
    source: str | None = None
    layer: str | None = None
    script: str | None = None


def ctsv2_text_id(language: str, title: str, incipit: str | None = None) -> str:
    language_key = _slug(language) or "und"
    title_key = _slug(title) or "text"
    incipit_key = _incipit_key(incipit or "")
    slug = f"{title_key}-{incipit_key}" if incipit_key else title_key
    return f"{CTSV2_URN_PREFIX}{language_key}:{slug}"


def ctsv2_segment_address(canonical_text_id: str, citation_path: str) -> str:
    return f"{canonical_text_id}?{urlencode({'ref': citation_path})}"


def parse_ctsv2_resource(value: str) -> Ctsv2Resource | None:
    text = value.strip()
    if not text:
        return None
    if text.startswith(CTSV2_URN_PREFIX):
        text_id, query = _split_urn_query(text)
        return _resource_from_query(text_id, query)
    parsed = urlparse(text)
    if parsed.scheme != CTSV2_URI_SCHEME or not parsed.netloc:
        return None
    text_id = f"{CTSV2_URN_PREFIX}{parsed.netloc}:{parsed.path.lstrip('/')}"
    return _resource_from_query(text_id, parsed.query)


def _resource_from_query(text_id: str, query: str) -> Ctsv2Resource:
    params = parse_qs(query, keep_blank_values=False)
    return Ctsv2Resource(
        text_id=text_id,
        ref=_first_param(params, "ref"),
        range=_first_param(params, "range"),
        witness=_first_param(params, "witness"),
        source=_first_param(params, "source"),
        layer=_first_param(params, "layer"),
        script=_first_param(params, "script"),
    )


def _first_param(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _split_urn_query(value: str) -> tuple[str, str]:
    text_id, separator, query = value.partition("?")
    return text_id, query if separator else ""


def _incipit_key(value: str) -> str:
    words = [word for word in _slug(value).split("-") if not word.isdigit()]
    return "-".join(words[:DEFAULT_INCIPIT_WORDS])


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    transliterated = without_marks.translate(_GREEK_TRANSLITERATION)
    return _NON_ALNUM_RE.sub("-", transliterated).strip("-")
