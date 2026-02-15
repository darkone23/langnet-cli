"""
Greedy agglomerative clustering for semantic reduction pipeline.

Clusters WitnessSenseUnits into SenseBuckets based on gloss similarity
using deterministic greedy algorithm.
"""

from langnet.semantic_reducer.similarity import build_similarity_matrix, get_neighbors
from langnet.semantic_reducer.types import MODE_THRESHOLDS, Mode, SenseBucket, WitnessSenseUnit


def cluster_wsus(
    wsus: list[WitnessSenseUnit],
    mode: Mode = Mode.OPEN,
    similarity_func: str = "jaccard",
) -> list[SenseBucket]:
    """
    Cluster WSUs using greedy agglomerative algorithm.

    Algorithm:
    1. Sort WSUs by source priority, stable sense_ref
    2. Start new bucket with next unused WSU
    3. Add WSUs with similarity >= threshold
    4. Repeat until exhausted

    Args:
        wsus: List of WitnessSenseUnit objects (should be pre-sorted)
        mode: OPEN (lower threshold) or SKEPTIC (higher threshold)
        similarity_func: Similarity function name

    Returns:
        List of SenseBucket with deterministic sense_id (B1, B2, ...)
    """
    if not wsus:
        return []

    threshold = MODE_THRESHOLDS[mode]
    matrix = build_similarity_matrix(wsus, similarity_func)

    used: set[int] = set()
    buckets: list[SenseBucket] = []

    for i in range(len(wsus)):
        if i in used:
            continue

        bucket_wsus = [wsus[i]]
        used.add(i)

        neighbors = get_neighbors(matrix, i, threshold)
        for neighbor_idx, _sim in neighbors:
            if neighbor_idx not in used:
                bucket_wsus.append(wsus[neighbor_idx])
                used.add(neighbor_idx)

        bucket = _create_bucket(bucket_wsus, len(buckets) + 1)
        buckets.append(bucket)

    return buckets


def _create_bucket(wsus: list[WitnessSenseUnit], bucket_num: int) -> SenseBucket:
    """
    Create a SenseBucket from a list of WSUs.

    Args:
        wsus: WSUs to include in bucket
        bucket_num: Bucket number for sense_id

    Returns:
        SenseBucket with calculated fields
    """
    sense_id = f"B{bucket_num}"
    display_gloss = _compute_display_gloss(wsus)
    confidence = _compute_confidence(wsus)

    all_domains: list[str] = []
    all_registers: list[str] = []
    for wsu in wsus:
        all_domains.extend(wsu.domains)
        all_registers.extend(wsu.register)

    unique_domains = list(dict.fromkeys(all_domains))
    unique_registers = list(dict.fromkeys(all_registers))

    return SenseBucket(
        sense_id=sense_id,
        semantic_constant=None,
        display_gloss=display_gloss,
        confidence=confidence,
        witnesses=wsus,
        domains=unique_domains,
        register=unique_registers,
    )


def _compute_display_gloss(wsus: list[WitnessSenseUnit]) -> str:
    """
    Compute display gloss for a bucket.

    Uses the gloss from the highest-priority WSU.
    """
    if not wsus:
        return ""
    return wsus[0].gloss_raw


def _compute_confidence(wsus: list[WitnessSenseUnit]) -> float:
    """
    Compute confidence score for a bucket.

    Factors:
    - Number of independent sources
    - Average confidence of witnesses
    """
    if not wsus:
        return 0.0

    sources = {wsu.source for wsu in wsus}
    source_factor = min(len(sources) / 3.0, 1.0)

    confidences = [wsu.confidence for wsu in wsus if wsu.confidence is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.7

    return round(0.6 * source_factor + 0.4 * avg_confidence, 2)
