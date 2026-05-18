from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.legacy_metadata import parse_legacy_authtab, tlg_canon_metadata_from_segments
from langnet.reader.models import ReaderSegment


def test_tlg_canon_metadata_extracts_author_category_and_work_title() -> None:
    path = Path("tlg_e/doccan1.txt")
    segments = [
        _segment("1.a.1", "0001"),
        _segment("1.a.2", "APOLLONIUS RHODIUS Epic."),
        _segment("1.1.1", "0001 001"),
        _segment("1.1.2", "Argonautica, ed. H. Fraenkel, Apollonii Rhodii Argonautica."),
        _segment("2.a.1", "0086"),
        _segment("2.a.2", "PLUTARCHUS Biogr. et Phil."),
    ]

    rows = tlg_canon_metadata_from_segments(path, "tlg", segments)
    triples = {(row.subject_kind, row.subject_id, row.key, row.value) for row in rows}

    assert ("author", "tlg0001", "tlg_canon_author_name", "Apollonius Rhodius") in triples
    assert ("author", "tlg0001", "tlg_canon_category", "Epic.") in triples
    assert ("work", "tlg0001.tlg001", "tlg_canon_work_number", "001") in triples
    assert (
        "work",
        "tlg0001.tlg001",
        "tlg_canon_work_title",
        "Argonautica, ed. H. Fraenkel, Apollonii Rhodii Argonautica.",
    ) in triples
    assert ("author", "tlg0086", "tlg_canon_author_name", "Plutarchus") in triples
    assert ("author", "tlg0086", "tlg_canon_category", "Biogr. et Phil.") in triples


def test_legacy_authtab_maps_hebrew_marker_to_hebrew_language() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        authtab = Path(tmpdir) / "AUTHTAB.DIR"
        authtab.write_bytes(b"PHI0001 Hebrew Bible (MT or BHS) \x83h\xff")

        rows = parse_legacy_authtab(authtab, collection_id="phi")
    triples = {(row.subject_id, row.key, row.value) for row in rows}

    assert ("phi0001", "authtab_language", "heb") in triples


def test_legacy_authtab_maps_coptic_marker_to_coptic_language() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        authtab = Path(tmpdir) / "AUTHTAB.DIR"
        authtab.write_bytes(b"COP0001 Sahidic Coptic Bible \x83c\xff")

        rows = parse_legacy_authtab(authtab, collection_id="phi")
    triples = {(row.subject_id, row.key, row.value) for row in rows}

    assert ("cop0001", "authtab_language", "cop") in triples


def _segment(citation_path: str, text: str) -> ReaderSegment:
    return ReaderSegment(
        segment_id=f"doccan1:{citation_path}",
        work_id="langnet:reader:tlg:doccan1.001",
        edition_id="langnet:reader:tlg:doccan1.001:edition",
        segment_kind="line",
        citation_path=citation_path,
        text=text,
        normalized_text=text.lower(),
        sort_key=1,
    )
