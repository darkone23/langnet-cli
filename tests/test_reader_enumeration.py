from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest import mock

from langnet.reader import service as reader_service_module
from langnet.reader.builder import ReaderBuildConfig, ReaderBuilder
from langnet.reader.models import (
    ReaderAlias,
    ReaderBookArtifact,
    ReaderCitationMap,
    ReaderCitationReference,
    ReaderDivisionMetadata,
    ReaderEdition,
    ReaderMetadataOverlayEvidence,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderWork,
    ReaderWorkMapNode,
)
from langnet.reader.service import ReaderService
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    register_aliases,
    register_book,
    register_citation_maps,
    register_citation_references,
    register_division_metadata,
    register_segment_rows,
    register_work_map_nodes,
)

FIXTURES = Path("tests/fixtures/reader")
FIXTURE_WORK_COUNT = 2
FIXTURE_ALIAS_COUNT = 9


def _copy_fixture(name: str, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / name, target_dir / name)


def _build_fixture_catalog(root: Path) -> Path:
    perseus_dir = root / "perseus"
    sanskrit_dir = root / "sanskrit"
    _copy_fixture("perseus_odyssey.xml", perseus_dir)
    _copy_fixture("sanskrit_raghuvamsa.json", sanskrit_dir)
    output_root = root / "build" / "reader"
    result = ReaderBuilder(
        ReaderBuildConfig(
            perseus_dir=perseus_dir,
            sanskrit_dir=sanskrit_dir,
            alias_dir=Path("data/curated/reader_aliases"),
            output_root=output_root,
        )
    ).build()
    return result.output_path


def test_reader_service_enumerates_and_resolves_alias_addresses() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReaderService(_build_fixture_catalog(Path(tmpdir)))

        collections = service.collections()
        authors = service.authors(language="grc")
        works = service.works(language="grc")
        homer_works = service.works(author="Homer")
        contents = service.contents("Od.")
        direct = service.show("urn:cts:greekLit:tlg0012.tlg002:3.74")
        by_work = service.show_work_segment("Od.", "3.74")
        resolved = service.resolve_address("Od. 3.74")
        friendly = service.resolve_address("Odyssey book 1 line 8")
        friendly_show = service.show("Odyssey book 1 line 8")

        assert {item["collection_id"] for item in collections["items"]} == {
            "perseus",
            "sanskrit_json",
        }
        assert authors["items"][0]["author"] == "Homer"
        assert works["items"][0]["title"] == "Odyssey"
        assert homer_works["items"][0]["title"] == "Odyssey"
        assert {item["citation_path"] for item in contents["items"]} >= {"1.8", "3.74"}
        assert direct["segment"]["text"] == "ψυχὰς παρθέμενοι"
        assert by_work["segment"]["text"] == "ψυχὰς παρθέμενοι"
        assert resolved["resolved_address"] == "urn:cts:greekLit:tlg0012.tlg002:3.74"
        assert resolved["segment"]["text"] == "ψυχὰς παρθέμενοι"
        assert friendly["resolved_address"] == "urn:cts:greekLit:tlg0012.tlg002:1.8"
        assert friendly["segment"]["text"] == "νήπιοι, οἳ κατὰ βοῦς Ὑπερίονος Ἠελίοιο"
        assert friendly_show["segment"]["citation_path"] == "1.8"


def test_reader_service_structure_payload_merges_map_and_division_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "bhagavadgita.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:sanskritLit:mbh.bhg",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="mbh.bhg",
            canonical_text_id="urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS CoNLL-U",
            language="san",
            source_path=root / "bhg-9.conllu",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="bhg-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=2,
                token_count=8,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:231273",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231273",
                    text="rājavidyā rājaguhyaṃ pavitramidamuttamam",
                    normalized_text="rajavidya rajaguhyam pavitramidamuttamam",
                    sort_key=1,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:231341",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231341",
                    text="iti guhyatamaṃ śāstram",
                    normalized_text="iti guhyatamam sastram",
                    sort_key=2,
                ),
            ],
            addresses=[],
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id=work.work_id,
                    node_id="bhg-09",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Rāja Vidyā Rāja Guhya Yoga",
                    native_label="राजविद्याराजगुह्ययोग",
                    ordinal=9,
                    start_citation="231273",
                    end_citation="231341",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )
        register_division_metadata(
            catalog_path,
            [
                ReaderDivisionMetadata(
                    work_id=work.work_id,
                    node_id="bhg-09",
                    summary="A reviewed chapter note.",
                    short_label="Royal knowledge",
                    traditional_reference="BhG 9",
                    status="accepted",
                    confidence="high",
                    generator_model="",
                    review_status="reviewed",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        service = ReaderService(catalog_path)
        payload = service.structure_payload(work.work_id)
        shown = service.show_work_segment(work.work_id, "231273")

    assert payload["mode"] == "structure"
    assert payload["summary"]["node_count"] == 1
    item = payload["items"][0]
    assert item["node_id"] == "bhg-09"
    assert item["object_type"] == "chapter"
    assert item["summary"] == "A reviewed chapter note."
    assert item["short_label"] == "Royal knowledge"
    assert item["traditional_reference"] == "BhG 9"
    assert item["provenance_chips"] == ["Curated", "Reviewed"]
    assert shown["current_divisions"][0]["node_id"] == "bhg-09"


def test_reader_service_work_dossier_summarizes_structure_and_bios() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "bhagavadgita.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:sanskritLit:mbh.bhg",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="mbh.bhg",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS CoNLL-U",
            language="san",
            source_path=root / "bhg-9.conllu",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="bhg-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=2,
                token_count=8,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:231273",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231273",
                    text="idaṃ tu te guhyatamaṃ pravakṣyāmyanasūyave",
                    normalized_text="idam tu te guhyatamam pravaksyamy anasuyave",
                    sort_key=1,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:231341",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231341",
                    text="iti guhyatamaṃ śāstram",
                    normalized_text="iti guhyatamam sastram",
                    sort_key=2,
                ),
            ],
            addresses=[],
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id=work.work_id,
                    node_id="bhg-09",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Rāja Vidyā Rāja Guhya Yoga",
                    native_label="राजविद्याराजगुह्ययोग",
                    ordinal=9,
                    start_citation="231273",
                    end_citation="231341",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                ),
                ReaderWorkMapNode(
                    work_id=work.work_id,
                    node_id="bhg-10",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Vibhūti Yoga",
                    native_label="विभूतियोग",
                    ordinal=10,
                    start_citation="231342",
                    end_citation="231418",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                ),
            ],
        )
        register_division_metadata(
            catalog_path,
            [
                ReaderDivisionMetadata(
                    work_id=work.work_id,
                    node_id="bhg-09",
                    summary="Chapter 9 presents royal knowledge and royal secret.",
                    short_label="Royal knowledge",
                    traditional_reference="BhG 9",
                    status="accepted",
                    confidence="high",
                    generator_model="",
                    review_status="reviewed",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        dossier = ReaderService(catalog_path).work_dossier_payload(work.work_id)

    assert dossier["mode"] == "work-dossier"
    assert dossier["work"]["title"] == "Bhagavadgītā"
    assert dossier["summary"]["top_level_count"] == 2
    assert dossier["summary"]["top_level_kind"] == "chapter"
    assert dossier["summary"]["structure_label"] == "2 chapters"
    assert dossier["summary"]["division_bio_count"] == 1
    assert [item["label"] for item in dossier["headings"]] == [
        "Rāja Vidyā Rāja Guhya Yoga",
        "Vibhūti Yoga",
    ]
    assert dossier["division_bios"][0]["traditional_reference"] == "BhG 9"
    assert dossier["provenance_chips"] == ["Curated", "Reviewed"]


def test_reader_service_resolves_division_metadata_traditional_reference() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "bhagavadgita.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:sanskritLit:mbh.bhg",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="mbh.bhg",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS CoNLL-U",
            language="san",
            source_path=root / "bhg-9.conllu",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="bhg-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=8,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:231273",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231273",
                    text="idaṃ tu te guhyatamaṃ pravakṣyāmyanasūyave",
                    normalized_text="idam tu te guhyatamam pravaksyamy anasuyave",
                    sort_key=1,
                )
            ],
            addresses=[],
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id=work.work_id,
                    node_id="bhg-09",
                    parent_node_id=None,
                    level=1,
                    kind="chapter",
                    label="Rāja Vidyā Rāja Guhya Yoga",
                    native_label="राजविद्याराजगुह्ययोग",
                    ordinal=9,
                    start_citation="231273",
                    end_citation="231341",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )
        register_division_metadata(
            catalog_path,
            [
                ReaderDivisionMetadata(
                    work_id=work.work_id,
                    node_id="bhg-09",
                    summary="A reviewed chapter note.",
                    short_label="Royal knowledge",
                    traditional_reference="BhG 9",
                    status="accepted",
                    confidence="high",
                    generator_model="",
                    review_status="reviewed",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        resolved = ReaderService(catalog_path).resolve_address("BhG 9")

    assert resolved["resolution_status"] == "resolved"
    assert resolved["resolution_kind"] == "structure"
    assert resolved["resolved_address"] == f"{work.work_id}:231273"
    assert resolved["segment"]["citation_path"] == "231273"
    assert resolved["structure_node"]["node_id"] == "bhg-09"
    assert resolved["current_divisions"][0]["traditional_reference"] == "BhG 9"


def test_reader_service_resolves_alias_plus_book_ordinal_to_structure_node() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "republic.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0059.tlg030",
            collection_id="perseus",
            language="grc",
            title="Republic",
            author="Plato",
            author_id=None,
            source_id="tlg0059.tlg030",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="Greek",
            language="grc",
            source_path=root / "republic.xml",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="republic-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=6,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:595a",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="section",
                    citation_path="595a",
                    text="Τὰ μὲν δὴ περὶ θεοὺς",
                    normalized_text="ta men de peri theous",
                    sort_key=1,
                )
            ],
            addresses=[],
        )
        register_aliases(
            catalog_path,
            [
                ReaderAlias(
                    alias="Republic",
                    language="grc",
                    kind="work",
                    target=work.work_id,
                    display="Plato, Republic",
                    source_file="fixture",
                    sources=("fixture",),
                )
            ],
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id=work.work_id,
                    node_id="republic-10",
                    parent_node_id=None,
                    level=1,
                    kind="book",
                    label="Book 10",
                    native_label=None,
                    ordinal=10,
                    start_citation="595a",
                    end_citation="621d",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
                    note="fixture",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        resolved = ReaderService(catalog_path).resolve_address("Republic Book 10")

    assert resolved["resolution_status"] == "resolved"
    assert resolved["resolution_kind"] == "structure"
    assert resolved["resolved_address"] == f"{work.work_id}:595a"
    assert resolved["segment"]["text"] == "Τὰ μὲν δὴ περὶ θεοὺς"
    assert resolved["structure_node"]["label"] == "Book 10"


def test_reader_service_resolves_alias_before_segment_lookup() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReaderService(_build_fixture_catalog(Path(tmpdir)))
        lookup_calls: list[str] = []
        original_lookup = reader_service_module.lookup_segment_by_address

        def tracking_lookup(catalog_path: Path, address: str) -> dict[str, object] | None:
            lookup_calls.append(address)
            return original_lookup(catalog_path, address)

        with mock.patch.object(
            reader_service_module,
            "lookup_segment_by_address",
            side_effect=tracking_lookup,
        ):
            resolved = service.resolve_address("Od. 3.74")

        assert resolved["resolved_address"] == "urn:cts:greekLit:tlg0012.tlg002:3.74"
        assert lookup_calls
        assert lookup_calls[0] == "urn:cts:greekLit:tlg0012.tlg002:3.74"


def test_reader_service_resolve_address_returns_all_citation_reference_segments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "mahabharata.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:sanskrit_dcs:dcs_154",
            collection_id="sanskrit_dcs",
            language="san",
            title="Mahābhārata",
            author="Unknown",
            author_id=None,
            source_id="dcs_154",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS CoNLL-U",
            language="san",
            source_path=root / "bhg-9.conllu",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="mahabharata-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=2,
                token_count=8,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:231276",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231276",
                    text="rājavidyā rājaguhyaṃ pavitramidamuttamam",
                    normalized_text="rājavidyā rājaguhyaṃ pavitramidamuttamam",
                    sort_key=1,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:231277",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="231277",
                    text="pratyakṣāvagamaṃ dharmyaṃ susukhaṃ kartumavyayam",
                    normalized_text="pratyakṣāvagamaṃ dharmyaṃ susukhaṃ kartumavyayam",
                    sort_key=2,
                ),
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:231276",
                    address=f"{work.work_id}:231276",
                    address_kind="langnet",
                    citation_path="231276",
                ),
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:231277",
                    address=f"{work.work_id}:231277",
                    address_kind="langnet",
                    citation_path="231277",
                ),
            ],
        )
        register_citation_references(
            catalog_path,
            [
                ReaderCitationReference(
                    work_id=work.work_id,
                    segment_id=f"{work.work_id}:231276",
                    citation_path="231276",
                    citation_ref="BhG 9.2",
                    source_kind="dcs_native",
                    source_path="bhg-9.conllu",
                    sort_key=1,
                ),
                ReaderCitationReference(
                    work_id=work.work_id,
                    segment_id=f"{work.work_id}:231277",
                    citation_path="231277",
                    citation_ref="BhG 9.2",
                    source_kind="dcs_native",
                    source_path="bhg-9.conllu",
                    sort_key=2,
                ),
            ],
        )

        lookup_calls: list[str] = []
        original_lookup = reader_service_module.lookup_segment_by_address

        def tracking_lookup(catalog_path: Path, address: str) -> dict[str, object] | None:
            lookup_calls.append(address)
            return original_lookup(catalog_path, address)

        with mock.patch.object(
            reader_service_module,
            "lookup_segment_by_address",
            side_effect=tracking_lookup,
        ):
            resolved = ReaderService(catalog_path).resolve_address("BhG 9.2")

    assert resolved["resolution_status"] == "resolved"
    assert resolved["segment"]["citation_path"] == "231276"
    assert [segment["citation_path"] for segment in resolved["segments"]] == ["231276", "231277"]
    assert "BhG 9.2" not in lookup_calls


def test_reader_builder_registers_dcs_citation_references_for_resolution() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        sanskrit_dir.mkdir()
        (sanskrit_dir / "bhg-9.conllu").write_text(
            """## text: Mahābhārata
## text_id: 154
## chapter: MBh, 6, BhaGī 9
## chapter_id: 7697
# text = rājavidyā rājaguhyaṃ pavitramidamuttamam
# sent_id = 231276
# sent_counter = 2
# sent_subcounter = 1
1	rājavidyā	rājavidyā	NOUN	_	_	_	_	_	_

# text = pratyakṣāvagamaṃ dharmyaṃ susukhaṃ kartumavyayam
# sent_id = 231277
# sent_counter = 2
# sent_subcounter = 2
1	pratyakṣāvagamaṃ	pratyakṣāvagama	NOUN	_	_	_	_	_	_
""",
            encoding="utf-8",
        )
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                output_root=root / "build" / "reader",
                alias_dir=None,
                metadata_overlay_dir=None,
                metadata_attribution_dir=None,
                contained_work_dir=None,
                work_map_dir=None,
            )
        ).build()

        resolved = ReaderService(result.output_path).resolve_address("BhG 9.2")

    assert resolved["resolution_status"] == "resolved"
    assert [segment["citation_path"] for segment in resolved["segments"]] == ["231276", "231277"]


def test_reader_service_resolves_latin_compact_dictionary_reference_with_alias() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "lucretius.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:latinLit:phi0550.phi001",
            collection_id="perseus",
            language="lat",
            title="De Rerum Natura",
            author="Lucretius",
            author_id="urn:cts:latinLit:phi0550",
            source_id="phi0550.phi001",
            cts_work_urn="urn:cts:latinLit:phi0550.phi001",
        )
        edition = ReaderEdition(
            edition_id="urn:cts:latinLit:phi0550.phi001.perseus-lat1",
            work_id=work.work_id,
            label="Perseus Latin edition",
            language="lat",
            source_path=root / "lucretius.xml",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="lucretius-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=8,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:2.391",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="line",
                    citation_path="2.391",
                    text="et quamvis subito per colum vina videmus",
                    normalized_text="et quamvis subito per colum vina videmus",
                    sort_key=2391,
                )
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:2.391",
                    address=f"{work.work_id}:2.391",
                    address_kind="cts",
                    citation_path="2.391",
                )
            ],
        )
        register_aliases(
            catalog_path,
            [
                ReaderAlias(
                    alias="Lucr.",
                    language="lat",
                    kind="work_abbreviation",
                    target=work.work_id,
                    display="Lucretius, De Rerum Natura",
                    source_file="fixture",
                )
            ],
        )

        resolved = ReaderService(catalog_path).resolve_address("Lucr. 2, 391")

    assert resolved["resolved_address"] == "urn:cts:latinLit:phi0550.phi001:2.391"
    assert resolved["resolution_status"] == "resolved"
    assert resolved["segment"]["text"] == "et quamvis subito per colum vina videmus"
    assert [segment["citation_path"] for segment in resolved["segments"]] == ["2.391"]


def test_reader_service_resolves_dictionary_cts_address_to_less_granular_segment() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "cicero-inv.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:latinLit:phi0474.phi036",
            collection_id="perseus",
            language="lat",
            title="De Inventione",
            author="Marcus Tullius Cicero",
            author_id="urn:cts:latinLit:phi0474",
            source_id="phi0474.phi036",
            cts_work_urn="urn:cts:latinLit:phi0474.phi036",
        )
        edition = ReaderEdition(
            edition_id="urn:cts:latinLit:phi0474.phi036.perseus-lat1",
            work_id=work.work_id,
            label="Perseus Latin edition",
            language="lat",
            source_path=root / "cicero-inv.xml",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="cicero-inv-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=2,
                token_count=24,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:2.148",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="section",
                    citation_path="2.148",
                    text="paterfamilias uti super familia pecuniaque sua legassit",
                    normalized_text="paterfamilias uti super familia pecuniaque sua legassit",
                    sort_key=2148,
                ),
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:2.148",
                    address=f"{work.work_id}:2.148",
                    address_kind="cts",
                    citation_path="2.148",
                ),
            ],
        )
        register_citation_maps(
            catalog_path,
            [
                ReaderCitationMap(
                    citation_map_id="lewis-short-de-inventione-book-chapter-section",
                    source_id="lewis_short",
                    work_id=work.work_id,
                    source_pattern="book.chapter.section",
                    machine_pattern="book.section",
                    projection_rule="drop_middle_numeric_part",
                    example_source_reference="Cic. Inv. 2, 50, 148",
                    example_machine_citation="2.148",
                    status="accepted",
                    confidence="high",
                    note="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="fixture",
                            citation="fixture",
                            label="fixture",
                        ),
                    ),
                )
            ],
        )

        granular = ReaderService(catalog_path).resolve_address(
            "urn:cts:latinLit:phi0474.phi036:2.50.148"
        )
        roman = ReaderService(catalog_path).resolve_address(
            "urn:cts:latinLit:phi0474.phi036:ii.l.cxlviii"
        )

    assert granular["resolution_status"] == "resolved"
    assert granular["segment"]["citation_path"] == "2.148"
    assert granular["segment"]["stored_address"] == "urn:cts:latinLit:phi0474.phi036:2.148"
    assert granular["segment"]["address"] == "urn:cts:latinLit:phi0474.phi036:2.50.148"
    assert roman["resolution_status"] == "resolved"
    assert roman["segment"]["citation_path"] == "2.148"
    assert roman["segment"]["address"] == "urn:cts:latinLit:phi0474.phi036:ii.l.cxlviii"


def test_reader_service_resolves_roman_numeral_alias_reference() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "chup.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:sanskrit_texts:translations_ChUp-Olivelle",
            collection_id="sanskrit_texts",
            language="san",
            title="Chāndogyopaniṣad",
            author="Unknown",
            author_id=None,
            source_id="translations_ChUp-Olivelle",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="plain text",
            language="san",
            source_path=root / "ChUp-Olivelle.txt",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="chup-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=8,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:2.7.1",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="line",
                    citation_path="2.7.1",
                    text="that is the beginning of Chāndogya 2.7.1",
                    normalized_text="that is the beginning of chāndogya 2.7.1",
                    sort_key=2071,
                )
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:2.7.1",
                    address=f"{work.work_id}:2.7.1",
                    address_kind="langnet",
                    citation_path="2.7.1",
                )
            ],
        )
        register_aliases(
            catalog_path,
            [
                ReaderAlias(
                    alias="ChUp.",
                    language="san",
                    kind="work_abbreviation",
                    target=work.work_id,
                    display="Chāndogyopaniṣad",
                    source_file="fixture",
                )
            ],
        )

        resolved = ReaderService(catalog_path).resolve_address("ChUp. ii, 7, i")

    assert resolved["resolution_status"] == "resolved"
    assert resolved["resolved_address"] == f"{work.work_id}:2.7.1"
    assert resolved["segment"]["citation_path"] == "2.7.1"


def test_reader_service_show_resolves_friendly_address_before_segment_lookup() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReaderService(_build_fixture_catalog(Path(tmpdir)))
        lookup_calls: list[str] = []
        original_lookup = reader_service_module.lookup_segment_by_address

        def tracking_lookup(catalog_path: Path, address: str) -> dict[str, object] | None:
            lookup_calls.append(address)
            return original_lookup(catalog_path, address)

        with mock.patch.object(
            reader_service_module,
            "lookup_segment_by_address",
            side_effect=tracking_lookup,
        ):
            shown = service.show("Odyssey book 1 line 8")

        assert shown["resolved_address"] == "urn:cts:greekLit:tlg0012.tlg002:1.8"
        assert lookup_calls
        assert lookup_calls[0] == "urn:cts:greekLit:tlg0012.tlg002:1.8"


def test_reader_service_segment_budget_keeps_large_anchor() -> None:
    segments = [
        {"citation_path": "1.8", "text": "a" * 3_000, "sort_key": 8},
        {"citation_path": "1.9", "text": "b" * 9_000, "sort_key": 9},
        {"citation_path": "1.10", "text": "c" * 900, "sort_key": 10},
    ]

    budgeted = reader_service_module._budget_reader_segments(
        segments,
        char_budget=6_000,
        anchor="1.9",
        limit=9,
    )

    assert [item["citation_path"] for item in budgeted] == ["1.9"]


def test_reader_service_segment_budget_pages_forward_without_skipping() -> None:
    segments = [
        {"citation_path": "1.1", "text": "a" * 4_000, "sort_key": 1},
        {"citation_path": "1.2", "text": "b" * 4_000, "sort_key": 2},
        {"citation_path": "1.3", "text": "c" * 4_000, "sort_key": 3},
    ]

    budgeted = reader_service_module._budget_reader_segments(
        segments,
        char_budget=6_000,
        anchor=None,
        limit=14,
    )
    pagination = reader_service_module._pagination(
        limit=14,
        offset=0,
        has_more=len(segments) > len(budgeted),
        next_offset=len(budgeted),
    )

    assert [item["citation_path"] for item in budgeted] == ["1.1"]
    assert pagination is not None
    assert pagination["next_cursor"] == "1"


def test_reader_service_summary_aliases_and_conflicts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReaderService(_build_fixture_catalog(Path(tmpdir)))

        summary = service.summary()
        aliases = service.aliases()
        conflicts = service.alias_conflicts()

        assert summary["summary"]["work_count"] == FIXTURE_WORK_COUNT
        assert summary["summary"]["alias_count"] == FIXTURE_ALIAS_COUNT
        assert any(alias["alias"] == "Od." for alias in aliases["items"])
        assert any(alias["kind"] == "canonical_text_id" for alias in aliases["items"])
        assert conflicts["items"] == []
