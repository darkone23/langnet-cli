"""
Semantic Reducer module for langnet.

This module provides the semantic reduction pipeline that converts
raw lexical evidence into structured semantic output.

Key components:
- WitnessSenseUnit: Smallest semantic evidence unit from a source
- Gloss normalizer: Deterministic text normalization for comparison
- WSU extractor: Extract WSUs from DictionaryEntry objects
- Similarity: Pairwise similarity matrix construction
- Clusterer: Greedy agglomerative clustering into SenseBuckets
- Pipeline: Full orchestrator from entry to buckets
"""

from langnet.semantic_reducer.clusterer import cluster_wsus
from langnet.semantic_reducer.normalizer import (
    ABBREVIATIONS,
    DEFAULT_STOPWORDS,
    cosine_similarity,
    dice_similarity,
    get_similarity_function,
    jaccard_similarity,
    lemmatize_gloss,
    normalize_gloss,
    tokenize,
)
from langnet.semantic_reducer.pipeline import (
    get_bucket_summary,
    get_wsu_summary,
    reduce_entry_to_semantic_structs,
    reduce_to_semantic_structs,
)
from langnet.semantic_reducer.similarity import (
    build_similarity_matrix,
    get_neighbors,
    get_similar_pairs,
)
from langnet.semantic_reducer.types import (
    MODE_THRESHOLDS,
    SOURCE_PRIORITY,
    Mode,
    SenseBucket,
    Source,
    WitnessSenseUnit,
)
from langnet.semantic_reducer.wsu_extractor import (
    extract_wsu_from_block,
    extract_wsu_from_definition,
    extract_wsus_from_entries,
    extract_wsus_from_entry,
    sort_wsus_by_priority,
    wsu_to_dict,
)

__all__ = [
    "WitnessSenseUnit",
    "SenseBucket",
    "Mode",
    "Source",
    "MODE_THRESHOLDS",
    "SOURCE_PRIORITY",
    "normalize_gloss",
    "tokenize",
    "lemmatize_gloss",
    "jaccard_similarity",
    "dice_similarity",
    "cosine_similarity",
    "get_similarity_function",
    "ABBREVIATIONS",
    "DEFAULT_STOPWORDS",
    "extract_wsu_from_definition",
    "extract_wsu_from_block",
    "extract_wsus_from_entry",
    "extract_wsus_from_entries",
    "sort_wsus_by_priority",
    "wsu_to_dict",
    "build_similarity_matrix",
    "get_similar_pairs",
    "get_neighbors",
    "cluster_wsus",
    "reduce_to_semantic_structs",
    "reduce_entry_to_semantic_structs",
    "get_wsu_summary",
    "get_bucket_summary",
]
