"""
Full pipeline orchestrator for semantic reduction.

Converts DictionaryEntry objects to SenseBucket objects through
WSU extraction, sorting, similarity computation, and clustering.
"""

from langnet.schema import DictionaryEntry
from langnet.semantic_reducer.clusterer import cluster_wsus
from langnet.semantic_reducer.types import Mode, SenseBucket, WitnessSenseUnit
from langnet.semantic_reducer.wsu_extractor import extract_wsus_from_entries, sort_wsus_by_priority


def reduce_to_semantic_structs(
    entries: list[DictionaryEntry],
    mode: Mode = Mode.OPEN,
) -> list[SenseBucket]:
    """
    Full pipeline from DictionaryEntry to SenseBucket.

    Steps:
    1. Extract WSUs from entries
    2. Sort by priority
    3. Cluster into buckets

    Args:
        entries: List of DictionaryEntry objects
        mode: OPEN (learner-friendly) or SKEPTIC (conservative)

    Returns:
        List of SenseBucket objects
    """
    if not entries:
        return []

    wsus = extract_wsus_from_entries(entries)
    if not wsus:
        return []

    sorted_wsus = sort_wsus_by_priority(wsus)
    buckets = cluster_wsus(sorted_wsus, mode)

    return buckets


def reduce_entry_to_semantic_structs(
    entry: DictionaryEntry,
    mode: Mode = Mode.OPEN,
) -> list[SenseBucket]:
    """
    Reduce a single DictionaryEntry to SenseBuckets.

    Convenience wrapper for single-entry use cases.

    Args:
        entry: A DictionaryEntry object
        mode: OPEN or SKEPTIC

    Returns:
        List of SenseBucket objects
    """
    return reduce_to_semantic_structs([entry], mode)


def get_wsu_summary(wsus: list[WitnessSenseUnit]) -> dict:
    """
    Get summary statistics for WSU list.

    Args:
        wsus: List of WitnessSenseUnit objects

    Returns:
        Dict with count, sources, and domains
    """
    if not wsus:
        return {"count": 0, "sources": [], "domains": []}

    sources = sorted({wsu.source for wsu in wsus})
    domains = sorted({d for wsu in wsus for d in wsu.domains})

    return {
        "count": len(wsus),
        "sources": sources,
        "domains": domains,
    }


def get_bucket_summary(buckets: list[SenseBucket]) -> list[dict]:
    """
    Get summary for each bucket.

    Args:
        buckets: List of SenseBucket objects

    Returns:
        List of summary dicts
    """
    summaries = []
    for bucket in buckets:
        summaries.append(
            {
                "sense_id": bucket.sense_id,
                "display_gloss": bucket.display_gloss[:60] + "..."
                if len(bucket.display_gloss) > 60
                else bucket.display_gloss,
                "witness_count": len(bucket.witnesses),
                "sources": sorted({w.source for w in bucket.witnesses}),
                "confidence": bucket.confidence,
            }
        )
    return summaries
