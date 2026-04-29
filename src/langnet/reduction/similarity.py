from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from langnet.reduction.models import SenseBucket, WitnessSenseUnit

DEFAULT_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)

SOURCE_PRIORITY = {
    "dico": 1,
    "gaffiot": 1,
    "cdsl": 2,
    "mw": 2,
    "ap90": 3,
    "whitaker": 4,
    "whitakers": 4,
    "diogenes": 5,
    "lsj": 5,
    "lewis_short": 5,
    "heritage": 6,
    "cltk": 7,
}


class SimilarityMode(StrEnum):
    OPEN = "open"
    SKEPTIC = "skeptic"


MODE_THRESHOLDS = {
    SimilarityMode.OPEN: 0.25,
    SimilarityMode.SKEPTIC: 0.5,
}


@dataclass(frozen=True, slots=True)
class SimilarPair:
    left: int
    right: int
    score: float


def normalize_similarity_text(text: str) -> str:
    """Normalize gloss text for deterministic lexical similarity comparison."""
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"[^0-9a-z]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_similarity_text(text: str) -> tuple[str, ...]:
    tokens = normalize_similarity_text(text).split()
    return tuple(token for token in tokens if token not in DEFAULT_STOPWORDS)


def jaccard_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def dice_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return (2.0 * len(left_set & right_set)) / (len(left_set) + len(right_set))


def cosine_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    if not left or not right:
        return 0.0
    left_counts = Counter(left)
    right_counts = Counter(right)
    common = set(left_counts) & set(right_counts)
    if not common:
        return 0.0
    dot = sum(left_counts[token] * right_counts[token] for token in common)
    left_mag = math.sqrt(sum(count * count for count in left_counts.values()))
    right_mag = math.sqrt(sum(count * count for count in right_counts.values()))
    if left_mag == 0.0 or right_mag == 0.0:
        return 0.0
    return dot / (left_mag * right_mag)


def similarity_function(name: str) -> Callable[[Sequence[str], Sequence[str]], float]:
    functions: dict[str, Callable[[Sequence[str], Sequence[str]], float]] = {
        "jaccard": jaccard_similarity,
        "dice": dice_similarity,
        "cosine": cosine_similarity,
    }
    try:
        return functions[name]
    except KeyError as exc:
        raise ValueError(f"Unknown similarity function: {name}") from exc


def source_priority(source_tool: str) -> int:
    return SOURCE_PRIORITY.get(source_tool, 100)


def sort_witnesses_by_priority(witnesses: Sequence[WitnessSenseUnit]) -> list[WitnessSenseUnit]:
    return sorted(
        witnesses,
        key=lambda witness: (
            source_priority(witness.source_tool),
            witness.source_tool,
            witness.sense_anchor,
            witness.wsu_id,
        ),
    )


def build_similarity_matrix(
    witnesses: Sequence[WitnessSenseUnit],
    *,
    metric: str = "jaccard",
) -> list[list[float]]:
    score = similarity_function(metric)
    tokens = [tokenize_similarity_text(witness.normalized_gloss) for witness in witnesses]
    matrix = [[0.0 for _ in witnesses] for _ in witnesses]
    for idx in range(len(witnesses)):
        matrix[idx][idx] = 1.0
    for left in range(len(witnesses)):
        for right in range(left + 1, len(witnesses)):
            value = score(tokens[left], tokens[right])
            matrix[left][right] = value
            matrix[right][left] = value
    return matrix


def get_similar_pairs(
    matrix: Sequence[Sequence[float]],
    *,
    threshold: float,
) -> list[SimilarPair]:
    pairs: list[SimilarPair] = []
    for left, row in enumerate(matrix):
        for right in range(left + 1, len(row)):
            score = row[right]
            if score >= threshold:
                pairs.append(SimilarPair(left=left, right=right, score=score))
    return sorted(pairs, key=lambda pair: (-pair.score, pair.left, pair.right))


def _similarity_bucket_id(language: str, witnesses: Sequence[WitnessSenseUnit]) -> str:
    material = "\x1f".join(sorted(witness.wsu_id for witness in witnesses))
    digest = hashlib.sha256(f"{language}\x1f{material}".encode()).hexdigest()[:16]
    return f"bucket:sim:{digest}"


def cluster_similar_witnesses(
    witnesses: Sequence[WitnessSenseUnit],
    *,
    language: str,
    mode: SimilarityMode = SimilarityMode.OPEN,
    metric: str = "jaccard",
) -> list[SenseBucket]:
    """
    Opt-in lexical clustering for current WSUs.

    The default runtime reducer still uses exact glosses. This helper exists for
    tested experiments where broader grouping is explicitly requested.
    """
    if not witnesses:
        return []

    ordered = sort_witnesses_by_priority(witnesses)
    threshold = MODE_THRESHOLDS[mode]
    matrix = build_similarity_matrix(ordered, metric=metric)
    pairs = get_similar_pairs(matrix, threshold=threshold)
    neighbors: dict[int, set[int]] = {index: set() for index in range(len(ordered))}
    for pair in pairs:
        neighbors[pair.left].add(pair.right)
        neighbors[pair.right].add(pair.left)

    used: set[int] = set()
    buckets: list[SenseBucket] = []

    for index in range(len(ordered)):
        if index in used:
            continue

        component: list[int] = []
        stack = [index]
        while stack:
            current = stack.pop()
            if current in used:
                continue
            used.add(current)
            component.append(current)
            stack.extend(sorted(neighbors[current] - used, reverse=True))

        component.sort()
        bucket_witnesses = [ordered[component_index] for component_index in component]

        buckets.append(
            SenseBucket(
                bucket_id=_similarity_bucket_id(language, bucket_witnesses),
                normalized_gloss=bucket_witnesses[0].normalized_gloss,
                display_gloss=bucket_witnesses[0].gloss,
                witnesses=bucket_witnesses,
                confidence_label=(
                    "similarity-multi-witness"
                    if len(bucket_witnesses) > 1
                    else "similarity-single-witness"
                ),
                notes=[f"similarity:{mode.value}:{metric}:{threshold:g}"],
            )
        )
    return buckets
