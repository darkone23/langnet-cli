from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class CdslEntry:
    dict_id: str
    key: str
    key_normalized: str
    key2: Optional[str] = None
    key2_normalized: Optional[str] = None
    lnum: Decimal = field(default_factory=Decimal)
    data: str = ""
    body: Optional[str] = None
    page_ref: Optional[str] = None


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
    short_title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    pub_place: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    encoding_date: Optional[str] = None
    license: Optional[str] = None


@dataclass
class CdslQueryResult:
    dict_id: str
    key: str
    lnum: str
    data: str
    body: Optional[str] = None
    page_ref: Optional[str] = None


@dataclass
class SanskritDictionaryEntry:
    id: str
    meaning: str
    subid: Optional[str] = None


@dataclass
class SanskritDictionaryLookup:
    term: str
    iast: str
    hk: str
    deva: str
    entries: list[SanskritDictionaryEntry] = field(default_factory=list)
