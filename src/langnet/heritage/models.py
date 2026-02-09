from dataclasses import dataclass, field

from langnet.types import JSONMapping


@dataclass
class HeritageWordAnalysis:
    """Analysis result for a single word"""

    word: str
    lemma: str
    root: str
    pos: str
    case: str | None = None
    gender: str | None = None
    number: str | None = None
    person: int | None = None
    tense: str | None = None
    voice: str | None = None
    mood: str | None = None
    stem: str = ""
    meaning: list[str] = field(default_factory=list)


@dataclass
class HeritageSolution:
    """Complete solution from morphological analysis"""

    type: str
    analyses: list[HeritageWordAnalysis]
    total_words: int
    score: float = 0.0
    metadata: JSONMapping = field(default_factory=dict)


@dataclass
class HeritageDictionaryEntry:
    """Dictionary entry from search results"""

    headword: str
    lemma: str
    definitions: list[str]
    pos: str | None = None
    gender: str | None = None
    number: str | None = None
    case: int | None = None
    etymology: str | None = None
    stem: str | None = None
    root: str | None = None
    frequency: int | None = None
    metadata: JSONMapping = field(default_factory=dict)


@dataclass
class HeritageSearchResult:
    """Complete search result from dictionary lookup"""

    query: str
    lexicon: str
    entries: list[HeritageDictionaryEntry]
    total_results: int
    page: int = 1
    has_next: bool = False
    has_prev: bool = False
    suggestions: list[str] = field(default_factory=list)


@dataclass
class HeritageMorphologyResult:
    """Complete morphology analysis result"""

    input_text: str
    solutions: list[HeritageSolution]
    word_analyses: list[HeritageWordAnalysis]
    total_solutions: int
    encoding: str = "velthuis"
    processing_time: float = 0.0
    metadata: JSONMapping = field(default_factory=dict)


@dataclass
class HeritageLemmaResult:
    """Lemmatization result"""

    input_word: str
    lemmas: list[str]
    best_lemma: str | None = None
    processing_time: float = 0.0


@dataclass
class HeritageDeclensionResult:
    """Declension generation result"""

    lemma: str
    gender: str
    case: int
    number: str
    forms: list[str]
    table: list[list[str]]
    metadata: JSONMapping = field(default_factory=dict)


@dataclass
class HeritageConjugationResult:
    """Conjugation generation result"""

    verb: str
    tense: str
    person: int
    number: str
    forms: list[str]
    table: list[list[str]]
    metadata: JSONMapping = field(default_factory=dict)


@dataclass
class HeritageErrorResponse:
    """Error response from Heritage Platform"""

    error: str
    code: str
    message: str
    details: str | None = None
    timestamp: str | None = None


class HeritageAPIError(Exception):
    """Exception raised for Heritage API errors"""

    pass
