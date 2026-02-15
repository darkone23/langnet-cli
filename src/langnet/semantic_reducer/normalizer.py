"""
Gloss normalization for semantic comparison.

Applies deterministic transformations to gloss text for similarity comparison.
Normalization is comparison-layer only - raw gloss is preserved for display.

Allowed transformations:
- Lowercasing
- Unicode normalization (NFKC)
- Whitespace normalization
- Abbreviation expansion (optional)
- Tokenization
- Lemmatization (via Stanza EN pipeline)

Prohibited:
- Paraphrasing
- Translation
- Semantic summarization
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Callable

ABBREVIATIONS: dict[str, str] = {
    "adj": "adjective",
    "adv": "adverb",
    "esp": "especially",
    "e.g": "for example",
    "i.e": "that is",
    "lit": "literally",
    "orig": "originally",
    "rel": "related",
    "syn": "synonym",
    "vs": "versus",
    "cf": "compare",
    "sg": "singular",
    "pl": "plural",
    "masc": "masculine",
    "fem": "feminine",
    "neut": "neuter",
    "nom": "nominative",
    "acc": "accusative",
    "gen": "genitive",
    "dat": "dative",
    "abl": "ablative",
    "loc": "locative",
    "voc": "vocative",
    "instr": "instrumental",
    "pres": "present",
    "past": "past",
    "fut": "future",
    "ppl": "participle",
    "inf": "infinitive",
}


def normalize_gloss(  # noqa: PLR0913
    gloss: str,
    *,
    lowercase: bool = True,
    unicode_normalize: bool = True,
    whitespace_normalize: bool = True,
    expand_abbreviations: bool = False,
    remove_punctuation: bool = False,
    stopwords: set[str] | None = None,
) -> str:
    """
    Normalize gloss text for similarity comparison.

    Args:
        gloss: Raw gloss text from source
        lowercase: Convert to lowercase
        unicode_normalize: Apply NFKC normalization
        whitespace_normalize: Collapse multiple whitespace to single space
        expand_abbreviations: Expand common abbreviations
        remove_punctuation: Remove punctuation characters
        stopwords: Optional set of stopwords to remove

    Returns:
        Normalized gloss string
    """
    result = gloss

    if unicode_normalize:
        result = unicodedata.normalize("NFKC", result)

    if lowercase:
        result = result.lower()

    if expand_abbreviations:
        for abbr, expansion in ABBREVIATIONS.items():
            pattern = r"\b" + re.escape(abbr) + r"\.?\b"
            result = re.sub(pattern, expansion, result, flags=re.IGNORECASE)

    if remove_punctuation:
        result = re.sub(r"[^\w\s]", " ", result)

    if whitespace_normalize:
        result = re.sub(r"\s+", " ", result).strip()

    if stopwords:
        tokens = result.split()
        tokens = [t for t in tokens if t.lower() not in stopwords]
        result = " ".join(tokens)

    return result


def tokenize(gloss: str) -> list[str]:
    """Split normalized gloss into tokens, removing punctuation."""
    normalized = normalize_gloss(gloss, remove_punctuation=True)
    return normalized.split()


def jaccard_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """
    Calculate Jaccard similarity between two token sets.

    Jaccard = |intersection| / |union|

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not tokens1 or not tokens2:
        return 0.0

    set1 = set(tokens1)
    set2 = set(tokens2)

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union)


def dice_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """
    Calculate Dice similarity between two token sets.

    Dice = 2 * |intersection| / (|set1| + |set2|)

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not tokens1 or not tokens2:
        return 0.0

    set1 = set(tokens1)
    set2 = set(tokens2)

    intersection = set1 & set2

    return (2.0 * len(intersection)) / (len(set1) + len(set2))


def cosine_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """
    Calculate cosine similarity between two token vectors.

    Uses term frequency as the vector weights.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not tokens1 or not tokens2:
        return 0.0

    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)

    common_terms = set(tf1.keys()) & set(tf2.keys())
    if not common_terms:
        return 0.0

    dot_product = sum(tf1[t] * tf2[t] for t in common_terms)

    magnitude1 = sum(v**2 for v in tf1.values()) ** 0.5
    magnitude2 = sum(v**2 for v in tf2.values()) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


DEFAULT_STOPWORDS: set[str] = {
    "a",
    "an",
    "the",
    "of",
    "in",
    "to",
    "for",
    "with",
    "on",
    "at",
    "from",
    "by",
    "as",
    "or",
    "and",
    "but",
    "not",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "shall",
    "can",
    "need",
    "dare",
    "ought",
    "used",
}


def get_similarity_function(name: str) -> Callable[[list[str], list[str]], float]:
    """Get similarity function by name."""
    functions = {
        "jaccard": jaccard_similarity,
        "dice": dice_similarity,
        "cosine": cosine_similarity,
    }
    if name not in functions:
        raise ValueError(
            f"Unknown similarity function: {name}. Available: {list(functions.keys())}"
        )
    return functions[name]


_stanza_en_pipeline = None


def _get_stanza_en_pipeline():
    """Lazy-load Stanza English pipeline for lemmatization."""
    global _stanza_en_pipeline
    if _stanza_en_pipeline is None:
        import stanza

        _stanza_en_pipeline = stanza.Pipeline("en", processors="tokenize,lemma", verbose=False)
    return _stanza_en_pipeline


def lemmatize_gloss(gloss: str) -> list[str]:
    """
    Lemmatize English gloss text using Stanza.

    Normalizes inflected forms for better similarity matching
    (e.g., "gods" -> "god", "sacrificial" -> "sacrificial").

    Args:
        gloss: Raw gloss text (English)

    Returns:
        List of lemmatized tokens
    """
    nlp = _get_stanza_en_pipeline()
    doc = nlp(gloss)

    lemmas = []
    for sent in doc.sentences:  # type: ignore[union-attr]
        for word in sent.words:
            if word.lemma and word.lemma.isalpha():
                lemmas.append(word.lemma.lower())

    return lemmas


def tokenize_with_lemmatization(gloss: str, stopwords: set[str] | None = None) -> list[str]:
    """
    Tokenize with lemmatization for improved similarity matching.

    Combines Stanza lemmatization with stopword removal.

    Args:
        gloss: Raw gloss text
        stopwords: Optional set of stopwords to remove

    Returns:
        List of lemmatized tokens
    """
    lemmas = lemmatize_gloss(gloss)

    if stopwords:
        lemmas = [l for l in lemmas if l not in stopwords]

    return lemmas
