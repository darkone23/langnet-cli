"""
WSU (Witness Sense Unit) extraction from dictionary entries.

Extracts structured WSUs from DictionaryEntry/DictionaryDefinition objects
for use in the semantic reduction pipeline.
"""

import re

from langnet.schema import DictionaryBlock, DictionaryDefinition, DictionaryEntry
from langnet.semantic_reducer.normalizer import normalize_gloss
from langnet.semantic_reducer.types import SOURCE_PRIORITY, Source, WitnessSenseUnit


def _preprocess_cdsl_gloss(gloss: str) -> str:
    """
    Strip grammatical metadata from CDSL glosses.

    CDSL glosses often start with headword and grammatical info:
    "agni/   m. (√ ag, Uṇ.) fire, sacrificial fire (of three kinds..."

    This strips the leading grammatical prefix to get the actual definition.
    """
    if "/" not in gloss[:20]:
        return gloss

    result = gloss

    match = re.match(r"^[^/]+/\s*(.+)$", gloss)
    if match:
        result = match.group(1)

    match = re.match(r"^(?:[mfn]+(?:\([^)]*\))?\.?\s*)+(.+)$", result)
    if match:
        result = match.group(1)

    match = re.match(r"^\([^)]+\)\s*(.+)$", result)
    if match:
        result = match.group(1)

    return result


def extract_wsu_from_definition(
    definition: DictionaryDefinition,
    source: str,
    ordering: int = 0,
) -> WitnessSenseUnit | None:
    """
    Extract a WSU from a DictionaryDefinition.

    Args:
        definition: The DictionaryDefinition to extract from
        source: Source identifier (e.g., "mw", "ap90", "heritage")
        ordering: Position in source (for deterministic ordering)

    Returns:
        WitnessSenseUnit or None if definition is empty
    """
    if not definition.definition.strip():
        return None

    sense_ref = definition.source_ref or f"{source}:{ordering}"
    gloss_raw = definition.definition

    if source.lower() in ("mw", "ap90", "cdsl"):
        gloss_raw = _preprocess_cdsl_gloss(gloss_raw)

    gloss_normalized = normalize_gloss(gloss_raw)

    return WitnessSenseUnit(
        source=source.lower(),
        sense_ref=sense_ref,
        gloss_raw=definition.definition,
        gloss_normalized=gloss_normalized,
        domains=list(definition.domains) if definition.domains else [],
        register=list(definition.register) if definition.register else [],
        confidence=definition.confidence,
        ordering=ordering,
    )


def extract_wsu_from_block(
    block: DictionaryBlock,
    source: str,
    ordering: int = 0,
) -> WitnessSenseUnit | None:
    """
    Extract a WSU from a DictionaryBlock (Diogenes format).

    Args:
        block: The DictionaryBlock to extract from
        source: Source identifier (e.g., "diogenes", "lsj")
        ordering: Position in source (for deterministic ordering)

    Returns:
        WitnessSenseUnit or None if block is empty
    """
    if not block.entry.strip():
        return None

    sense_ref = f"{source}:{block.entryid}" if block.entryid else f"{source}:{ordering}"
    gloss_raw = block.entry
    gloss_normalized = normalize_gloss(gloss_raw)

    return WitnessSenseUnit(
        source=source.lower(),
        sense_ref=sense_ref,
        gloss_raw=gloss_raw,
        gloss_normalized=gloss_normalized,
        domains=[],
        register=[],
        confidence=None,
        ordering=ordering,
    )


def extract_wsus_from_entry(entry: DictionaryEntry) -> list[WitnessSenseUnit]:
    """
    Extract all WSUs from a DictionaryEntry.

    Handles both definitions (CDSL, Heritage, Whitakers) and
    dictionary_blocks (Diogenes LSJ/Lewis-Short).

    Args:
        entry: The DictionaryEntry to extract from

    Returns:
        List of WitnessSenseUnit objects
    """
    wsus: list[WitnessSenseUnit] = []
    source = entry.source.lower() if entry.source else "unknown"

    for i, definition in enumerate(entry.definitions):
        wsu = extract_wsu_from_definition(definition, source, ordering=i)
        if wsu is not None:
            wsus.append(wsu)

    for i, block in enumerate(entry.dictionary_blocks):
        wsu = extract_wsu_from_block(block, source, ordering=len(wsus) + i)
        if wsu is not None:
            wsus.append(wsu)

    return wsus


def extract_wsus_from_entries(entries: list[DictionaryEntry]) -> list[WitnessSenseUnit]:
    """
    Extract all WSUs from multiple DictionaryEntry objects.

    Args:
        entries: List of DictionaryEntry objects

    Returns:
        List of all WitnessSenseUnit objects
    """
    wsus: list[WitnessSenseUnit] = []
    for entry in entries:
        wsus.extend(extract_wsus_from_entry(entry))
    return wsus


def wsu_to_dict(wsu: WitnessSenseUnit) -> dict:
    """Convert WitnessSenseUnit to dictionary for serialization."""
    return {
        "source": wsu.source,
        "sense_ref": wsu.sense_ref,
        "gloss_raw": wsu.gloss_raw,
        "gloss_normalized": wsu.gloss_normalized,
        "domains": wsu.domains,
        "register": wsu.register,
        "confidence": wsu.confidence,
        "ordering": wsu.ordering,
    }


def sort_wsus_by_priority(wsus: list[WitnessSenseUnit]) -> list[WitnessSenseUnit]:
    """
    Sort WSUs by source priority and sense_ref for deterministic ordering.

    Priority order: MW > AP90 > Heritage > LSJ > Lewis_Short > Whitakers > Diogenes > CLTK > CDSL
    """

    def sort_key(wsu: WitnessSenseUnit) -> tuple[int, str, int]:
        try:
            source_enum = Source(wsu.source.lower())
            priority = SOURCE_PRIORITY.get(source_enum, 999)
        except ValueError:
            priority = 999
        return (priority, wsu.sense_ref, wsu.ordering)

    return sorted(wsus, key=sort_key)
