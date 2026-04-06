"""Evidence block schema for provenance tracking in universal claims.

Every claim in the universal layer must carry a complete evidence block
tracing it back through all pipeline stages to the original tool response.

Design Principles:
- Evidence is IMMUTABLE - never modify after creation
- Evidence is COMPLETE - includes all stage IDs in the provenance chain
- Evidence is TRACEABLE - can reconstruct full lineage from any claim
- Evidence is SOURCE-TAGGED - includes tool-specific reference (mw:217497, etc.)

References:
- docs/technical/semantic_triples.md
- docs/technical/predicates_evidence.md
- docs/plans/active/tool-fact-indexing.md
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceBlock:
    """Complete provenance record for a claim.

    Attributes:
        source_tool: Tool name (diogenes, whitakers, cdsl, heritage, cltk, spacy)
        call_id: UUID of the tool call that initiated this claim
        response_id: UUID of the raw response (Stage 1: FETCH)
        extraction_id: UUID of the extraction (Stage 2: EXTRACT), or None if fetch-only
        derivation_id: UUID of the derivation (Stage 3: DERIVE), or None if extract-only
        claim_id: UUID of the claim itself (Stage 4: CLAIM)
        source_ref: Tool-specific source reference (e.g., "mw:217497", "diogenes:lsj:42690320")
        raw_blob_ref: Key for retrieving raw content ("raw_html", "raw_text", "raw_json")
        metadata: Optional additional context (timestamps, handler versions, etc.)

    Example:
        >>> evidence = EvidenceBlock(
        ...     source_tool="whitakers",
        ...     call_id="call-uuid-001",
        ...     response_id="resp-uuid-002",
        ...     extraction_id="ext-uuid-003",
        ...     derivation_id="deriv-uuid-004",
        ...     claim_id="claim-uuid-005",
        ...     source_ref="whitakers:lupus:nom_sg",
        ...     raw_blob_ref="raw_text",
        ... )
    """

    source_tool: str
    call_id: str
    response_id: str
    extraction_id: str | None
    derivation_id: str | None
    claim_id: str | None
    source_ref: str | None = None
    raw_blob_ref: str = "raw_html"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize evidence block to dictionary for JSON storage."""
        return {
            "source_tool": self.source_tool,
            "call_id": self.call_id,
            "response_id": self.response_id,
            "extraction_id": self.extraction_id,
            "derivation_id": self.derivation_id,
            "claim_id": self.claim_id,
            "source_ref": self.source_ref,
            "raw_blob_ref": self.raw_blob_ref,
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceBlock:
        """Deserialize evidence block from dictionary."""
        return cls(
            source_tool=data["source_tool"],
            call_id=data["call_id"],
            response_id=data["response_id"],
            extraction_id=data.get("extraction_id"),
            derivation_id=data.get("derivation_id"),
            claim_id=data.get("claim_id"),
            source_ref=data.get("source_ref"),
            raw_blob_ref=data.get("raw_blob_ref", "raw_html"),
            metadata=data.get("metadata", {}),
        )

    def with_claim_id(self, claim_id: str) -> EvidenceBlock:
        """Create new evidence block with claim_id set.

        Since EvidenceBlock is frozen, this creates a new instance.
        """
        return EvidenceBlock(
            source_tool=self.source_tool,
            call_id=self.call_id,
            response_id=self.response_id,
            extraction_id=self.extraction_id,
            derivation_id=self.derivation_id,
            claim_id=claim_id,
            source_ref=self.source_ref,
            raw_blob_ref=self.raw_blob_ref,
            metadata=self.metadata,
        )

    def stage_depth(self) -> int:
        """Count how many stages are in the provenance chain.

        Returns:
            1 (FETCH only), 2 (FETCH+EXTRACT), 3 (FETCH+EXTRACT+DERIVE), or 4 (full)
        """
        if self.claim_id is not None:
            return 4
        if self.derivation_id is not None:
            return 3
        if self.extraction_id is not None:
            return 2
        return 1


def build_evidence_from_effects(  # noqa: PLR0913
    tool: str,
    call_id: str,
    response_id: str,
    extraction_id: str | None = None,
    derivation_id: str | None = None,
    claim_id: str | None = None,
    source_ref: str | None = None,
    raw_blob_ref: str = "raw_html",
    **metadata,
) -> EvidenceBlock:
    """Convenience function for building evidence blocks from effect IDs.

    Args:
        tool: Source tool name
        call_id: Tool call UUID
        response_id: Raw response UUID
        extraction_id: Optional extraction UUID
        derivation_id: Optional derivation UUID
        claim_id: Optional claim UUID
        source_ref: Optional tool-specific reference
        raw_blob_ref: Key for raw content retrieval
        **metadata: Additional metadata fields

    Returns:
        Complete evidence block

    Example:
        >>> evidence = build_evidence_from_effects(
        ...     tool="diogenes",
        ...     call_id="call-001",
        ...     response_id="resp-002",
        ...     extraction_id="ext-003",
        ...     derivation_id="deriv-004",
        ...     source_ref="diogenes:lsj:42690320",
        ... )
    """
    return EvidenceBlock(
        source_tool=tool,
        call_id=call_id,
        response_id=response_id,
        extraction_id=extraction_id,
        derivation_id=derivation_id,
        claim_id=claim_id,
        source_ref=source_ref,
        raw_blob_ref=raw_blob_ref,
        metadata=metadata,
    )


def merge_evidence_metadata(
    evidence: EvidenceBlock,
    **additional_metadata,
) -> EvidenceBlock:
    """Add metadata to existing evidence block.

    Args:
        evidence: Original evidence block
        **additional_metadata: New metadata to merge

    Returns:
        New evidence block with merged metadata

    Example:
        >>> original = build_evidence_from_effects("diogenes", "call-1", "resp-1")
        >>> with_timing = merge_evidence_metadata(
        ...     original,
        ...     fetch_duration_ms=150,
        ...     extraction_duration_ms=25,
        ... )
    """
    merged_metadata = {**evidence.metadata, **additional_metadata}
    return EvidenceBlock(
        source_tool=evidence.source_tool,
        call_id=evidence.call_id,
        response_id=evidence.response_id,
        extraction_id=evidence.extraction_id,
        derivation_id=evidence.derivation_id,
        claim_id=evidence.claim_id,
        source_ref=evidence.source_ref,
        raw_blob_ref=evidence.raw_blob_ref,
        metadata=merged_metadata,
    )
