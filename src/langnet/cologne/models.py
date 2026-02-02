from dataclasses import dataclass, field
from decimal import Decimal

from langnet.citation.models import CitationCollection


@dataclass
class CdslEntry:
    dict_id: str
    key: str
    key_normalized: str
    key2: str | None = None
    key2_normalized: str | None = None
    lnum: Decimal = field(default_factory=Decimal)
    data: str = ""
    body: str | None = None
    page_ref: str | None = None


@dataclass
class CdslHomonym:
    dict_id: str
    lnum: Decimal
    homonym_num: int
    body: str
    sanskrit_forms: list[str] = field(default_factory=list)
    lex_categories: list[str] = field(default_factory=list)


@dataclass
class DictMetadata:
    dict_id: str
    title: str
    short_title: str | None = None
    author: str | None = None
    publisher: str | None = None
    pub_place: str | None = None
    year: int | None = None
    description: str | None = None
    source_url: str | None = None
    encoding_date: str | None = None
    license: str | None = None


@dataclass
class CdslQueryResult:
    dict_id: str
    key: str
    lnum: str
    data: str
    body: str | None = None
    page_ref: str | None = None


@dataclass
class SanskritDictionaryEntry:
    id: str
    meaning: str
    subid: str | None = None
    pos: str | None = None
    gender: list[str] | None = None
    sanskrit_form: str | None = None
    etymology: dict | None = None
    grammar_tags: dict | None = None
    references: CitationCollection | None = None
    page_ref: str | None = None


@dataclass
class SanskritDictionaryLookup:
    term: str
    iast: str
    hk: str
    deva: str
    entries: list[SanskritDictionaryEntry] = field(default_factory=list)


@dataclass
class SanskritTransliteration:
    input: str
    iast: str
    hk: str
    devanagari: str


@dataclass
class SanskritDictionaryResponse:
    transliteration: SanskritTransliteration
    dictionaries: dict[str, list[SanskritDictionaryEntry]]
