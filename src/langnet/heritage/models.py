from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class HeritageWordAnalysis:
    """Analysis result for a single word"""

    word: str
    lemma: str
    root: str
    pos: str
    case: Optional[str] = None
    gender: Optional[str] = None
    number: Optional[str] = None
    person: Optional[int] = None
    tense: Optional[str] = None
    voice: Optional[str] = None
    mood: Optional[str] = None
    stem: str = ""
    meaning: List[str] = field(default_factory=list)
    lexicon_refs: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class HeritageSolution:
    """Complete solution from morphological analysis"""

    type: str
    analyses: List[HeritageWordAnalysis]
    total_words: int
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeritageDictionaryEntry:
    """Dictionary entry from search results"""

    headword: str
    lemma: str
    definitions: List[str]
    pos: Optional[str] = None
    gender: Optional[str] = None
    number: Optional[str] = None
    case: Optional[int] = None
    etymology: Optional[str] = None
    stem: Optional[str] = None
    root: Optional[str] = None
    lexicon_refs: List[str] = field(default_factory=list)
    frequency: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeritageSearchResult:
    """Complete search result from dictionary lookup"""

    query: str
    lexicon: str
    entries: List[HeritageDictionaryEntry]
    total_results: int
    page: int = 1
    has_next: bool = False
    has_prev: bool = False
    suggestions: List[str] = field(default_factory=list)


@dataclass
class HeritageMorphologyResult:
    """Complete morphology analysis result"""

    input_text: str
    solutions: List[HeritageSolution]
    word_analyses: List[Dict[str, Any]]
    total_solutions: int
    encoding: str = "velthuis"
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeritageLemmaResult:
    """Lemmatization result"""

    input_word: str
    lemmas: List[str]
    best_lemma: Optional[str] = None
    confidence: float = 0.0
    processing_time: float = 0.0


@dataclass
class HeritageDeclensionResult:
    """Declension generation result"""

    lemma: str
    gender: str
    case: int
    number: str
    forms: List[str]
    table: List[List[str]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeritageConjugationResult:
    """Conjugation generation result"""

    verb: str
    tense: str
    person: int
    number: str
    forms: List[str]
    table: List[List[str]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeritageErrorResponse:
    """Error response from Heritage Platform"""

    error: str
    code: str
    message: str
    details: Optional[str] = None
    timestamp: Optional[str] = None
