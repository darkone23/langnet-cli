from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReaderCollection:
    collection_id: str
    label: str
    source_root: Path | None = None


@dataclass(frozen=True)
class ReaderBookPathParts:
    collection: str
    namespace: str
    author_id: str
    work_id: str
    edition_id: str


@dataclass(frozen=True)
class ReaderAuthor:
    author_id: str
    collection_id: str
    language: str
    name: str
    source_id: str


@dataclass(frozen=True)
class ReaderWork:
    work_id: str
    collection_id: str
    language: str
    title: str
    author: str
    source_id: str
    author_id: str | None = None
    cts_work_urn: str | None = None


@dataclass(frozen=True)
class ReaderEdition:
    edition_id: str
    work_id: str
    label: str
    language: str
    source_path: Path
    cts_edition_urn: str | None = None


@dataclass(frozen=True)
class ReaderBookArtifact:
    artifact_id: str
    work_id: str
    edition_id: str
    artifact_path: Path
    source_path: Path
    adapter: str
    source_hash: str
    segment_count: int = 0
    token_count: int = 0


@dataclass(frozen=True)
class ReaderSourceFile:
    collection_id: str
    source_path: Path
    file_role: str
    file_status: str
    source_id: str
    source_hash: str | None = None
    size_bytes: int | None = None


@dataclass(frozen=True)
class ReaderSourceMetadata:
    collection_id: str
    subject_kind: str
    subject_id: str
    key: str
    value: str
    source_path: Path


@dataclass(frozen=True)
class ReaderMetadataOverlayEvidence:
    source_type: str
    citation: str
    label: str
    retrieved_at: str | None = None


@dataclass(frozen=True)
class ReaderMetadataOverlay:
    collection_id: str
    match_field: str
    match_value: str
    field: str
    value: str
    status: str
    confidence: str
    note: str
    source_file: str
    evidence: tuple[ReaderMetadataOverlayEvidence, ...]


@dataclass(frozen=True)
class ReaderMetadataAttribution:
    collection_id: str
    match_field: str
    match_value: str
    relation_type: str
    agent: str
    status: str
    confidence: str
    note: str
    source_file: str
    evidence: tuple[ReaderMetadataOverlayEvidence, ...]


@dataclass(frozen=True)
class ReaderContainedWork:
    contained_work_id: str
    parent_work_id: str
    collection_id: str
    language: str
    title: str
    author: str
    source_id: str
    start_citation: str
    end_citation: str
    status: str
    confidence: str
    note: str
    cts_work_urn: str | None = None
    source_file: str = ""
    evidence: tuple[ReaderMetadataOverlayEvidence, ...] = ()


@dataclass(frozen=True)
class ReaderSegment:
    segment_id: str
    work_id: str
    edition_id: str
    segment_kind: str
    citation_path: str
    text: str
    normalized_text: str
    sort_key: int
    source_text: str | None = None


@dataclass(frozen=True)
class ReaderSegmentAddress:
    segment_id: str
    address: str
    address_kind: str
    citation_path: str


@dataclass(frozen=True)
class ReaderAlias:
    alias: str
    language: str
    kind: str
    target: str
    display: str
    source_file: str
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReaderBuildStats:
    catalog_path: str
    artifact_count: int
    work_count: int
    segment_count: int
    alias_count: int
    source_error_count: int = 0
