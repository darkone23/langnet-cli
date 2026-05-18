from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import duckdb

from langnet.reader.models import (
    ReaderAlias,
    ReaderAuthor,
    ReaderAuthorClassification,
    ReaderBookArtifact,
    ReaderBookPathParts,
    ReaderContainedWork,
    ReaderEdition,
    ReaderMetadataAttribution,
    ReaderMetadataOverlayEvidence,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceMetadata,
    ReaderWork,
    ReaderWorkClassification,
    ReaderWorkMapNode,
)
from langnet.reader.paths import reader_book_path, reader_catalog_path, reader_root
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    list_author_index,
    list_collections,
    list_discovery_group_summaries,
    list_discovery_shelves,
    list_discovery_tag_summaries,
    list_duplicate_audit,
    list_metadata_attributions,
    list_metadata_overlays,
    list_segments_for_work,
    list_works,
    lookup_artifact_for_address,
    lookup_segment_by_address,
    lookup_segment_by_work_and_citation,
    prune_stale_work_classifications,
    reader_discovery_coverage,
    reader_summary,
    register_author_classifications,
    register_book,
    register_books,
    register_contained_works,
    register_metadata_attributions,
    register_segment_rows,
    register_source_metadata,
    register_work_classifications,
    register_work_map_nodes,
    repair_work_languages,
    work_map_for_work,
)

ODYSSEY_FIXTURE_WORD_COUNT = 8
CONTAINED_BHG_FIXTURE_WORD_COUNT = 4
WORK_MAP_FIXTURE_WORD_COUNT = 7
CANONICAL_POPULARITY_SCORE = 100
CANONICAL_SCOPE_POPULARITY_SCORE = 95
DISCOVERY_GLOBAL_POPULARITY_SCORE = 72
DISCOVERY_GROUP_POPULARITY_SCORE = 96
AUTHOR_CANONICAL_PROMINENCE_SCORE = 100
MANDANA_FIXTURE_WORK_COUNT = 2
SANSKRIT_MEDICINE_FIXTURE_COUNT = 2


def _register_fixture_work(  # noqa: PLR0913
    catalog_path: Path,
    root: Path,
    *,
    work_id: str,
    collection_id: str,
    language: str,
    title: str,
    author: str,
    author_id: str | None,
    source_id: str,
) -> None:
    safe_source = source_id.replace(":", "_").replace(".", "_")
    book_path = root / "books" / f"{safe_source}.duckdb"
    create_book_db(book_path)
    edition = ReaderEdition(
        edition_id=f"{work_id}:edition",
        work_id=work_id,
        label="Fixture edition",
        language=language,
        source_path=root / f"{safe_source}.xml",
    )
    register_book(
        catalog_path,
        ReaderWork(
            work_id=work_id,
            collection_id=collection_id,
            language=language,
            title=title,
            author=author,
            author_id=author_id,
            source_id=source_id,
            cts_work_urn=work_id if work_id.startswith("urn:cts:") else None,
        ),
        edition,
        ReaderBookArtifact(
            artifact_id=f"{work_id}:artifact",
            work_id=work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=0,
            token_count=0,
        ),
    )


def test_reader_paths_are_under_build_reader() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        data_root = Path(tmpdir)
        root = reader_root(data_root)
        assert root == data_root / "build" / "reader"
        assert reader_catalog_path(data_root) == data_root / "build" / "reader" / "catalog.duckdb"
        assert reader_book_path(
            ReaderBookPathParts(
                collection="perseus",
                namespace="greekLit",
                author_id="tlg0012",
                work_id="tlg002",
                edition_id="perseus-grc2",
            ),
            data_root=data_root,
        ) == (
            data_root
            / "build"
            / "reader"
            / "books"
            / "perseus"
            / "greekLit"
            / "tlg0012"
            / "tlg002"
            / "perseus-grc2.duckdb"
        )


def test_reader_model_minimum_fields() -> None:
    segment = ReaderSegment(
        segment_id="seg-1",
        work_id="urn:cts:greekLit:tlg0012.tlg002",
        edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        segment_kind="line",
        citation_path="3.74",
        text="ψυχὰς παρθέμενοι",
        normalized_text="ψυχας παρθεμενοι",
        sort_key=74,
    )
    alias = ReaderAlias(
        alias="Od.",
        language="grc",
        kind="work_abbreviation",
        target="urn:cts:greekLit:tlg0012.tlg002",
        display="Homer, Odyssey",
        source_file="tests/fixtures/reader/aliases/greek/homer.yaml",
        sources=("lsj", "manual"),
    )
    author = ReaderAuthor(
        author_id="urn:cts:greekLit:tlg0012",
        collection_id="perseus",
        language="grc",
        name="Homer",
        source_id="tlg0012",
    )
    assert segment.citation_path == "3.74"
    assert alias.target.endswith("tlg002")
    assert author.name == "Homer"


def test_reader_catalog_surfaces_word_counts_from_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "odyssey.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0012.tlg002",
            collection_id="perseus",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
            cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
        )
        edition = ReaderEdition(
            edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
            work_id=work.work_id,
            label="Perseus Greek edition",
            language="grc",
            source_path=root / "odyssey.xml",
            cts_edition_urn="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="odyssey-grc2",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=2,
                token_count=ODYSSEY_FIXTURE_WORD_COUNT,
            ),
        )

        collections = list_collections(catalog_path)
        works = list_works(catalog_path, language="grc")
        authors = list_author_index(catalog_path, language="grc")
        summary = reader_summary(catalog_path)

    assert collections[0]["word_count"] == ODYSSEY_FIXTURE_WORD_COUNT
    assert collections[0]["word_count_method"] == "whitespace_tokens"
    assert works[0]["word_count"] == ODYSSEY_FIXTURE_WORD_COUNT
    assert works[0]["word_count_method"] == "whitespace_tokens"
    assert authors[0]["word_count"] == ODYSSEY_FIXTURE_WORD_COUNT
    assert authors[0]["word_count_method"] == "whitespace_tokens"
    assert authors[0]["representative_titles"] == "Odyssey"
    assert summary["word_count"] == ODYSSEY_FIXTURE_WORD_COUNT
    assert summary["word_count_method"] == "whitespace_tokens"


def test_reader_catalog_surfaces_generated_author_classifications() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0690.phi003",
            collection_id="phi",
            language="lat",
            title="Aeneis",
            author="P. Vergilius Maro (Virgil)",
            author_id="urn:cts:latinLit:phi0690",
            source_id="lat0690.003",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:civ0005.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="English Bible (KJV or AV)",
            author_id="civ0005",
            source_id="civ0005.001",
        )
        register_author_classifications(
            catalog_path,
            [
                ReaderAuthorClassification(
                    author_id="phi0690",
                    language="lat",
                    source_author_id="urn:cts:latinLit:phi0690",
                    canonical_name="Virgil",
                    agent_kind="person",
                    historicity_status="historical",
                    period="Augustan",
                    date_range="70-19 BCE",
                    region="Italy",
                    cultural_context="Roman poetry",
                    bio="Roman poet of the Eclogues, Georgics, and Aeneid.",
                    prominence_score=AUTHOR_CANONICAL_PROMINENCE_SCORE,
                    prominence_tier="canonical",
                    confidence="high",
                    note="Canonical Latin poet.",
                    generator_models="test-model",
                    generator_run_id="run-1",
                    source_file="authors.csv",
                ),
                ReaderAuthorClassification(
                    author_id="civ0005",
                    language="lat",
                    source_author_id="civ0005",
                    canonical_name="King James Bible",
                    agent_kind="collective",
                    historicity_status="not_applicable",
                    period="early modern",
                    date_range="1611 CE",
                    region="England",
                    cultural_context="English biblical translation",
                    bio="Source collection label for a Bible translation.",
                    prominence_score=20,
                    prominence_tier="specialist",
                    confidence="high",
                    note="Source collection label, not an ancient author.",
                    generator_models="test-model",
                    generator_run_id="run-1",
                    source_file="authors.csv",
                ),
            ],
        )

        people = list_author_index(
            catalog_path,
            language="lat",
            agent_kind="person",
            sort="prominence",
        )
        collectives = list_author_index(
            catalog_path,
            language="lat",
            agent_kind="collective",
        )

    assert [item["author_id"] for item in people] == ["phi0690"]
    assert people[0]["author"] == "Virgil"
    assert people[0]["source_author_name"] == "P. Vergilius Maro (Virgil)"
    assert people[0]["canonical_author_id"] == "urn:cts:latinLit:phi0690"
    assert people[0]["canonical_author_name"] == "Virgil"
    assert people[0]["author_canonical_name"] == "Virgil"
    assert people[0]["author_agent_kind"] == "person"
    assert people[0]["author_classification_source_author_id"] == "urn:cts:latinLit:phi0690"
    assert people[0]["author_historicity_status"] == "historical"
    assert people[0]["author_period"] == "Augustan"
    assert people[0]["author_region"] == "Italy"
    assert people[0]["author_bio"].startswith("Roman poet")
    assert people[0]["author_prominence_score"] == AUTHOR_CANONICAL_PROMINENCE_SCORE
    assert [item["author_id"] for item in collectives] == ["civ0005"]
    assert collectives[0]["author_canonical_name"] == "King James Bible"
    assert collectives[0]["canonical_author_name"] == "King James Bible"


def test_generated_canonical_author_ids_round_trip_for_author_navigation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="shankara-aitareya",
            collection_id="sanskrit_json",
            language="san",
            title="Aitareyopaniṣadbhāṣya",
            author="Śaṃkara",
            author_id=None,
            source_id="corpus_sa_aitareyopaniSad-comm",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="shankara-brhadaranyaka",
            collection_id="sanskrit_json",
            language="san",
            title="Bṛhadāraṇyakopaniṣadbhāṣya",
            author="Śaṃkara",
            author_id=None,
            source_id="corpus_sa_bRhadAraNyakopaniSadkANva-recension-comm",
        )
        register_author_classifications(
            catalog_path,
            [
                ReaderAuthorClassification(
                    author_id="langnet:reader:author:san:samkara",
                    language="san",
                    source_author_id="",
                    canonical_name="Śaṃkarācārya",
                    agent_kind="person",
                    historicity_status="traditional",
                    period="Classical",
                    date_range="c. 8th century CE",
                    region="India",
                    cultural_context="Advaita Vedanta",
                    bio="Traditional Advaita Vedanta teacher.",
                    prominence_score=90,
                    prominence_tier="canonical",
                    confidence="medium",
                    note="Generated canonical author identity.",
                    generator_models="test-model",
                    generator_run_id="run-1",
                    source_file="authors.csv",
                ),
            ],
        )

        works = list_works(catalog_path, language="san", query="Śaṃkara")
        canonical_author_id = str(works[0]["canonical_author_id"])
        by_canonical_author = list_works(
            catalog_path,
            language="san",
            author_id=canonical_author_id,
        )
        authors_by_canonical_name = list_author_index(
            catalog_path,
            language="san",
            query="Śaṃkarācārya",
        )
        authors_by_folded_name = list_author_index(
            catalog_path,
            language="san",
            query="samkaracarya",
        )
        authors_by_common_ascii_name = list_author_index(
            catalog_path,
            language="san",
            query="sankara",
        )

    assert canonical_author_id == "urn:cts:langnet:author.san.samkaracarya"
    assert [work["title"] for work in by_canonical_author] == [
        "Aitareyopaniṣadbhāṣya",
        "Bṛhadāraṇyakopaniṣadbhāṣya",
    ]
    assert [item["canonical_author_id"] for item in authors_by_canonical_name] == [
        canonical_author_id
    ]
    assert [item["canonical_author_id"] for item in authors_by_folded_name] == [canonical_author_id]
    assert [item["canonical_author_id"] for item in authors_by_common_ascii_name] == [
        canonical_author_id
    ]


def test_list_works_summarizes_gretil_source_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:sanskrit_texts:GRETIL_sa_nAgArjuna-dharmasaMgraha",
            collection_id="sanskrit_texts",
            language="san",
            title="Dharmasaṃgraha",
            author="Nāgārjuna",
            author_id=None,
            source_id="GRETIL_sa_nAgArjuna-dharmasaMgraha",
        )
        register_source_metadata(
            catalog_path,
            [
                ReaderSourceMetadata(
                    collection_id="sanskrit_texts",
                    subject_kind="work",
                    subject_id="GRETIL_sa_nAgArjuna-dharmasaMgraha",
                    key="gretil_text",
                    value="Dharmasaṃgraha",
                    source_path=root / "sa_nAgArjuna-dharmasaMgraha.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="sanskrit_texts",
                    subject_kind="work",
                    subject_id="GRETIL_sa_nAgArjuna-dharmasaMgraha",
                    key="gretil_author",
                    value="Nāgārjuna",
                    source_path=root / "sa_nAgArjuna-dharmasaMgraha.txt",
                ),
                ReaderSourceMetadata(
                    collection_id="sanskrit_texts",
                    subject_kind="work",
                    subject_id="GRETIL_sa_nAgArjuna-dharmasaMgraha",
                    key="gretil_edition",
                    value="P.L. Vaidya: Dharmasangraha. Darbhanga 1961.",
                    source_path=root / "sa_nAgArjuna-dharmasaMgraha.txt",
                ),
            ],
        )

        works = list_works(catalog_path, language="san")

    assert works[0]["source_metadata_summary"] == (
        "gretil_text=Dharmasaṃgraha; gretil_author=Nāgārjuna; "
        "gretil_edition=P.L. Vaidya: Dharmasangraha. Darbhanga 1961."
    )


def test_list_works_does_not_hide_stale_gretil_json_twins() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:sanskrit_json:corpus_sa_nAgArjuna-dharmasaMgraha",
            collection_id="sanskrit_json",
            language="san",
            title="Dharmasaṃgraha",
            author="Nāgārjuna",
            author_id=None,
            source_id="corpus_sa_nAgArjuna-dharmasaMgraha",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:sanskrit_texts:GRETIL_sa_nAgArjuna-dharmasaMgraha",
            collection_id="sanskrit_texts",
            language="san",
            title="Dharmasaṃgraha",
            author="Nāgārjuna",
            author_id=None,
            source_id="GRETIL_sa_nAgArjuna-dharmasaMgraha",
        )

        works = list_works(catalog_path, language="san", query="Nāgārjuna")

    assert [
        (work["collection_id"], work["source_id"])
        for work in sorted(works, key=lambda item: str(item["collection_id"]))
    ] == [
        ("sanskrit_json", "corpus_sa_nAgArjuna-dharmasaMgraha"),
        ("sanskrit_texts", "GRETIL_sa_nAgArjuna-dharmasaMgraha"),
    ]


def test_reader_catalog_maps_work_title_author_headings_to_unknown_authority() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:greekLit:tlg0317.tlg001",
            collection_id="tlg",
            language="grc",
            title="Acta Joannis",
            author="Acta Joannis",
            author_id="tlg0317",
            source_id="tlg0317.001",
        )
        register_author_classifications(
            catalog_path,
            [
                ReaderAuthorClassification(
                    author_id="tlg0317",
                    language="grc",
                    source_author_id="tlg0317",
                    canonical_name="Acta Joannis",
                    agent_kind="work_title",
                    historicity_status="not_applicable",
                    prominence_score=55,
                    prominence_tier="common",
                    confidence="high",
                    note="The source author slot is occupied by a work title.",
                    generator_models="test-model",
                    generator_run_id="run-1",
                    source_file="authors.csv",
                ),
            ],
        )

        authors = list_author_index(catalog_path, language="grc", agent_kind="work_title")
        works = list_works(catalog_path, language="grc", author="Acta Joannis")

    assert authors[0]["author"] == "Unknown"
    assert authors[0]["author_canonical_name"] == "Unknown"
    assert authors[0]["author_period"] == ""
    assert authors[0]["author_region"] == ""
    assert authors[0]["author_bio"] == ""
    assert authors[0]["source_author_name"] == "Acta Joannis"
    assert authors[0]["source_author_kind"] == "work_title"
    assert authors[0]["source_author_canonical_name"] == "Acta Joannis"
    assert authors[0]["source_author_classification_notes"] == (
        "The source author slot is occupied by a work title."
    )
    assert authors[0]["canonical_author_id"] == "urn:cts:langnet:author.grc.unknown"
    assert authors[0]["canonical_author_name"] == "Unknown"
    assert works[0]["author"] == "Unknown"
    assert works[0]["source_author"] == "Acta Joannis"
    assert works[0]["source_author_id"] == "tlg0317"
    assert works[0]["canonical_author_id"] == "urn:cts:langnet:author.grc.unknown"


def test_reader_catalog_surfaces_generated_work_classifications_and_popularity_sort() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "works.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        homer = ReaderWork(
            work_id="urn:cts:greekLit:tlg0012.tlg002",
            collection_id="perseus",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
            cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
        )
        fragment = ReaderWork(
            work_id="urn:cts:greekLit:tlg9999.tlg001",
            collection_id="perseus",
            language="grc",
            title="Fragmenta",
            author="Minor Poet",
            author_id="urn:cts:greekLit:tlg9999",
            source_id="tlg9999.tlg001",
            cts_work_urn="urn:cts:greekLit:tlg9999.tlg001",
        )
        unclassified = ReaderWork(
            work_id="urn:cts:greekLit:tlg0007.tlg001",
            collection_id="perseus",
            language="grc",
            title="Life of Theseus",
            author="Plutarch",
            author_id="urn:cts:greekLit:tlg0007",
            source_id="tlg0007.tlg001",
            cts_work_urn="urn:cts:greekLit:tlg0007.tlg001",
        )
        for work in (homer, fragment, unclassified):
            edition = ReaderEdition(
                edition_id=f"{work.work_id}.edition",
                work_id=work.work_id,
                label="Fixture edition",
                language="grc",
                source_path=root / f"{work.source_id}.xml",
            )
            register_book(
                catalog_path,
                work,
                edition,
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}.artifact",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    artifact_path=book_path,
                    source_path=edition.source_path,
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=0,
                    token_count=0,
                ),
            )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id=fragment.work_id,
                    category="fragment",
                    period="hellenistic",
                    date_range="3rd century BCE",
                    authorship_status="attributed",
                    popularity_score=10,
                    popularity_tier="specialist",
                    scope="Fragmentary Poetry",
                    scope_popularity_score=75,
                    scope_popularity_tier="major",
                    confidence="medium",
                    note="Generated by classifier",
                    generator_models="deepseek/deepseek-v3.2",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                ),
                ReaderWorkClassification(
                    work_id=homer.work_id,
                    category="epic",
                    period="archaic",
                    date_range="c. 8th-7th century BCE",
                    authorship_status="traditional",
                    popularity_score=CANONICAL_POPULARITY_SCORE,
                    popularity_tier="canonical",
                    scope="Epic Poetry",
                    scope_popularity_score=CANONICAL_POPULARITY_SCORE,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Generated by classifier",
                    generator_models="deepseek/deepseek-v3.2;openai/gpt-oss-120b",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                ),
            ],
        )

        works = list_works(catalog_path, language="grc", sort="popularity")

    assert [work["work_id"] for work in works] == [
        homer.work_id,
        fragment.work_id,
        unclassified.work_id,
    ]
    assert works[0]["classification_category"] == "epic"
    assert works[0]["classification_period"] == "archaic"
    assert works[0]["classification_date_range"] == "c. 8th-7th century BCE"
    assert works[0]["classification_authorship_status"] == "traditional"
    assert works[0]["classification_popularity_score"] == CANONICAL_POPULARITY_SCORE
    assert works[0]["classification_popularity_tier"] == "canonical"
    assert works[0]["classification_scope"] == "Epic Poetry"
    assert works[0]["classification_scope_popularity_score"] == CANONICAL_POPULARITY_SCORE
    assert works[0]["classification_scope_popularity_tier"] == "canonical"
    assert works[0]["classification_confidence"] == "high"
    assert works[0]["classification_generator_models"] == (
        "deepseek/deepseek-v3.2;openai/gpt-oss-120b"
    )
    assert works[2]["classification_popularity_score"] is None


def test_reader_catalog_filters_scope_and_sorts_by_scope_popularity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "works.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        grammar = ReaderWork(
            work_id="lat:grammar",
            collection_id="fixture",
            language="lat",
            title="Ars Grammatica",
            author="Grammarian",
            author_id="latgram",
            source_id="latgram.001",
            cts_work_urn=None,
        )
        niche_grammar = ReaderWork(
            work_id="lat:niche-grammar",
            collection_id="fixture",
            language="lat",
            title="De Casibus Raris",
            author="Minor Grammarian",
            author_id="latminor",
            source_id="latminor.001",
            cts_work_urn=None,
        )
        epic = ReaderWork(
            work_id="lat:epic",
            collection_id="fixture",
            language="lat",
            title="Aeneid",
            author="Virgil",
            author_id="vergil",
            source_id="vergil.001",
            cts_work_urn=None,
        )
        for work in (grammar, niche_grammar, epic):
            edition = ReaderEdition(
                edition_id=f"{work.work_id}.edition",
                work_id=work.work_id,
                label="Fixture edition",
                language="lat",
                source_path=root / f"{work.source_id}.xml",
            )
            register_book(
                catalog_path,
                work,
                edition,
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}.artifact",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    artifact_path=book_path,
                    source_path=edition.source_path,
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=0,
                    token_count=0,
                ),
            )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id=grammar.work_id,
                    category="Grammar",
                    period="Late Antique",
                    date_range="4th century CE",
                    authorship_status="single_attributed",
                    popularity_score=35,
                    popularity_tier="specialist",
                    scope="Latin Grammar",
                    scope_popularity_score=CANONICAL_SCOPE_POPULARITY_SCORE,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Central Latin grammar text.",
                    generator_models="test",
                    generator_run_id="run",
                    source_file="fixture.csv",
                ),
                ReaderWorkClassification(
                    work_id=niche_grammar.work_id,
                    category="Grammar",
                    period="Late Antique",
                    date_range="5th century CE",
                    authorship_status="single_attributed",
                    popularity_score=5,
                    popularity_tier="obscure",
                    scope="Latin Grammar",
                    scope_popularity_score=30,
                    scope_popularity_tier="specialist",
                    confidence="medium",
                    note="Specialist grammar text.",
                    generator_models="test",
                    generator_run_id="run",
                    source_file="fixture.csv",
                ),
                ReaderWorkClassification(
                    work_id=epic.work_id,
                    category="Epic",
                    period="Augustan",
                    date_range="1st century BCE",
                    authorship_status="single_attributed",
                    popularity_score=100,
                    popularity_tier="canonical",
                    scope="Epic Poetry",
                    scope_popularity_score=100,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Canonical epic.",
                    generator_models="test",
                    generator_run_id="run",
                    source_file="fixture.csv",
                ),
            ],
        )

        works = list_works(
            catalog_path,
            language="lat",
            classification_scope="grammar",
            sort="popularity",
        )

    assert [work["work_id"] for work in works] == [grammar.work_id, niche_grammar.work_id]
    assert works[0]["classification_scope_popularity_score"] == CANONICAL_SCOPE_POPULARITY_SCORE


def test_reader_catalog_filters_discovery_group_and_tag_with_group_popularity() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "works.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)
        caraka = ReaderWork(
            work_id="sanskrit_dcs:dcs_33",
            collection_id="sanskrit_dcs",
            language="san",
            title="Carakasaṃhitā",
            author="",
            author_id=None,
            source_id="dcs_33",
            cts_work_urn=None,
        )
        niche = ReaderWork(
            work_id="sanskrit_dcs:dcs_999",
            collection_id="sanskrit_dcs",
            language="san",
            title="Minor Medical Compendium",
            author="",
            author_id=None,
            source_id="dcs_999",
            cts_work_urn=None,
        )
        epic = ReaderWork(
            work_id="sanskrit_dcs:dcs_154",
            collection_id="sanskrit_dcs",
            language="san",
            title="Mahābhārata",
            author="",
            author_id=None,
            source_id="dcs_154",
            cts_work_urn=None,
        )
        for work in (niche, caraka, epic):
            edition = ReaderEdition(
                edition_id=f"{work.work_id}.edition",
                work_id=work.work_id,
                label="Fixture edition",
                language="san",
                source_path=root / f"{work.source_id}.xml",
            )
            register_book(
                catalog_path,
                work,
                edition,
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}.artifact",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    artifact_path=book_path,
                    source_path=edition.source_path,
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=0,
                    token_count=0,
                ),
            )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id=niche.work_id,
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=20,
                    popularity_tier="specialist",
                    scope="Ayurveda",
                    scope_popularity_score=40,
                    scope_popularity_tier="common",
                    confidence="medium",
                    note="Generated by classifier",
                    generator_models="deepseek/deepseek-v3.2",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|ayurveda|technical",
                    global_popularity_score=20,
                    global_popularity_tier="specialist",
                    group_popularity_score=40,
                    group_popularity_tier="common",
                ),
                ReaderWorkClassification(
                    work_id=caraka.work_id,
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=72,
                    popularity_tier="major",
                    scope="Ayurveda",
                    scope_popularity_score=96,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Generated by classifier",
                    generator_models="deepseek/deepseek-v3.2",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|ayurveda|technical",
                    global_popularity_score=72,
                    global_popularity_tier="major",
                    group_popularity_score=96,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id=epic.work_id,
                    category="Epic",
                    period="epic",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=98,
                    popularity_tier="canonical",
                    scope="Sanskrit Epic Literature",
                    scope_popularity_score=99,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Generated by classifier",
                    generator_models="deepseek/deepseek-v3.2",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|itihasa|mahabharata",
                    global_popularity_score=98,
                    global_popularity_tier="canonical",
                    group_popularity_score=99,
                    group_popularity_tier="canonical",
                ),
            ],
        )

        works = list_works(
            catalog_path,
            language="san",
            classification_group="medicine",
            classification_tag="ayurveda",
            sort="group-popularity",
        )

    assert [work["work_id"] for work in works] == [caraka.work_id, niche.work_id]
    assert works[0]["classification_discovery_group_id"] == "medicine"
    assert works[0]["classification_discovery_tags"] == "medicine|ayurveda|technical"
    assert works[0]["classification_global_popularity_score"] == DISCOVERY_GLOBAL_POPULARITY_SCORE
    assert works[0]["classification_global_popularity_tier"] == "major"
    assert works[0]["classification_group_popularity_score"] == DISCOVERY_GROUP_POPULARITY_SCORE
    assert works[0]["classification_group_popularity_tier"] == "canonical"


def test_reader_catalog_summarizes_discovery_groups_by_language() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="grc-epic-1",
            collection_id="fixture",
            language="grc",
            title="Iliad",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="grc-epic-2",
            collection_id="fixture",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="lat-epic-1",
            collection_id="fixture",
            language="lat",
            title="Aeneid",
            author="Virgil",
            author_id="urn:cts:latinLit:phi0690",
            source_id="lat0690.003",
        )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="grc-epic-1",
                    category="Epic",
                    period="archaic",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=100,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=100,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|poetry",
                    global_popularity_score=100,
                    global_popularity_tier="canonical",
                    group_popularity_score=100,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id="grc-epic-2",
                    category="Epic",
                    period="archaic",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=96,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=96,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|poetry",
                    global_popularity_score=96,
                    global_popularity_tier="canonical",
                    group_popularity_score=96,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id="lat-epic-1",
                    category="Epic",
                    period="augustan",
                    date_range="1st century BCE",
                    authorship_status="single_attributed",
                    popularity_score=99,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=99,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|poetry",
                    global_popularity_score=99,
                    global_popularity_tier="canonical",
                    group_popularity_score=99,
                    group_popularity_tier="canonical",
                ),
            ],
        )

        groups = list_discovery_group_summaries(catalog_path, language="grc")

    assert groups == [
        {
            "id": "epic",
            "label": "Epic",
            "description": "Epic and large-scale heroic narrative traditions.",
            "work_count": 2,
            "classified_work_count": 2,
            "author_count": 1,
            "max_group_popularity_score": 100,
        }
    ]


def test_reader_catalog_summarizes_discovery_tags_by_language() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="san-med-1",
            collection_id="fixture",
            language="san",
            title="Carakasaṃhitā",
            author="Caraka",
            author_id=None,
            source_id="dcs_33",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="san-med-2",
            collection_id="fixture",
            language="san",
            title="Suśrutasaṃhitā",
            author="Suśruta",
            author_id=None,
            source_id="dcs_88",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="grc-med-1",
            collection_id="fixture",
            language="grc",
            title="Aphorisms",
            author="Hippocrates",
            author_id="urn:cts:greekLit:tlg0627",
            source_id="tlg0627.tlg001",
        )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="san-med-1",
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=72,
                    popularity_tier="major",
                    scope="Ayurveda",
                    scope_popularity_score=96,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|ayurveda|technical",
                    global_popularity_score=72,
                    global_popularity_tier="major",
                    group_popularity_score=96,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id="san-med-2",
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=68,
                    popularity_tier="major",
                    scope="Ayurveda",
                    scope_popularity_score=91,
                    scope_popularity_tier="major",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|ayurveda",
                    global_popularity_score=68,
                    global_popularity_tier="major",
                    group_popularity_score=91,
                    group_popularity_tier="major",
                ),
                ReaderWorkClassification(
                    work_id="grc-med-1",
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=80,
                    popularity_tier="major",
                    scope="Greek Medicine",
                    scope_popularity_score=94,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|hippocratic_galenic_medicine",
                    global_popularity_score=80,
                    global_popularity_tier="major",
                    group_popularity_score=94,
                    group_popularity_tier="canonical",
                ),
            ],
        )

        tags = list_discovery_tag_summaries(catalog_path, language="san")

    assert [tag["id"] for tag in tags] == ["ayurveda", "medicine", "technical"]
    assert tags[0]["work_count"] == SANSKRIT_MEDICINE_FIXTURE_COUNT
    assert tags[0]["author_count"] == SANSKRIT_MEDICINE_FIXTURE_COUNT
    assert tags[1]["work_count"] == SANSKRIT_MEDICINE_FIXTURE_COUNT
    assert tags[2]["work_count"] == 1
    assert tags[0]["label"] == "Ayurveda"


def test_reader_catalog_builds_language_scoped_discovery_shelves() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        caraka = ReaderWork(
            work_id="sanskrit_dcs:dcs_33",
            collection_id="sanskrit_dcs",
            language="san",
            title="Carakasaṃhitā",
            author="Caraka",
            author_id=None,
            source_id="dcs_33",
            cts_work_urn=None,
        )
        niche = ReaderWork(
            work_id="sanskrit_dcs:dcs_999",
            collection_id="sanskrit_dcs",
            language="san",
            title="Minor Medical Compendium",
            author="Vāgbhaṭa",
            author_id=None,
            source_id="dcs_999",
            cts_work_urn=None,
        )
        epic = ReaderWork(
            work_id="sanskrit_dcs:dcs_154",
            collection_id="sanskrit_dcs",
            language="san",
            title="Mahābhārata",
            author="",
            author_id=None,
            source_id="dcs_154",
            cts_work_urn=None,
        )
        latin = ReaderWork(
            work_id="lat-epic-1",
            collection_id="phi",
            language="lat",
            title="Aeneid",
            author="Virgil",
            author_id="urn:cts:latinLit:phi0690",
            source_id="lat0690.003",
            cts_work_urn=None,
        )
        for work in (niche, caraka, epic, latin):
            edition = ReaderEdition(
                edition_id=f"{work.work_id}.edition",
                work_id=work.work_id,
                label="Fixture edition",
                language=work.language,
                source_path=root / f"{work.source_id}.xml",
            )
            register_book(
                catalog_path,
                work,
                edition,
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}.artifact",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    artifact_path=root / "books" / f"{work.source_id}.duckdb",
                    source_path=edition.source_path,
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=0,
                    token_count=0,
                ),
            )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id=niche.work_id,
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=20,
                    popularity_tier="specialist",
                    scope="Ayurveda",
                    scope_popularity_score=40,
                    scope_popularity_tier="common",
                    confidence="medium",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|ayurveda|technical",
                    global_popularity_score=20,
                    global_popularity_tier="specialist",
                    group_popularity_score=40,
                    group_popularity_tier="common",
                ),
                ReaderWorkClassification(
                    work_id=caraka.work_id,
                    category="Medicine",
                    period="classical",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=72,
                    popularity_tier="major",
                    scope="Ayurveda",
                    scope_popularity_score=96,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="medicine",
                    discovery_tags="medicine|ayurveda|technical",
                    global_popularity_score=72,
                    global_popularity_tier="major",
                    group_popularity_score=96,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id=epic.work_id,
                    category="Epic",
                    period="epic",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=98,
                    popularity_tier="canonical",
                    scope="Sanskrit Epic Literature",
                    scope_popularity_score=99,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|itihasa|mahabharata",
                    global_popularity_score=98,
                    global_popularity_tier="canonical",
                    group_popularity_score=99,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id=latin.work_id,
                    category="Epic",
                    period="augustan",
                    date_range="1st century BCE",
                    authorship_status="single_attributed",
                    popularity_score=99,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=99,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|poetry",
                    global_popularity_score=99,
                    global_popularity_tier="canonical",
                    group_popularity_score=99,
                    group_popularity_tier="canonical",
                ),
            ],
        )

        shelves = list_discovery_shelves(catalog_path, language="san", sample_limit=2)

    assert [shelf["id"] for shelf in shelves] == ["medicine", "epic"]
    assert shelves[0]["query"] == {"group": "medicine", "sort": "group-popularity"}
    assert shelves[0]["work_count"] == SANSKRIT_MEDICINE_FIXTURE_COUNT
    assert shelves[0]["author_count"] == SANSKRIT_MEDICINE_FIXTURE_COUNT
    assert [work["title"] for work in shelves[0]["sample_works"]] == [
        "Carakasaṃhitā",
        "Minor Medical Compendium",
    ]
    assert shelves[1]["sample_works"][0]["title"] == "Mahābhārata"


def test_reader_catalog_reports_discovery_coverage_by_language() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="grc-1",
            collection_id="fixture",
            language="grc",
            title="Iliad",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="eng-1",
            collection_id="fixture",
            language="eng",
            title="Paradise Lost",
            author="John Milton",
            author_id="milton",
            source_id="milton.paradise_lost",
        )
        with duckdb.connect(str(catalog_path), read_only=False) as conn:
            conn.execute(
                """
                UPDATE artifacts
                SET segment_count = CASE work_id WHEN 'grc-1' THEN 12 ELSE 8 END,
                    token_count = CASE work_id WHEN 'grc-1' THEN 120 ELSE 80 END
                """
            )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="grc-1",
                    category="Epic",
                    period="archaic",
                    date_range="uncertain",
                    authorship_status="traditional",
                    popularity_score=100,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=100,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                    source_file="fixture.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|poetry",
                    global_popularity_score=100,
                    global_popularity_tier="canonical",
                    group_popularity_score=100,
                    group_popularity_tier="canonical",
                )
            ],
        )
        register_author_classifications(
            catalog_path,
            [
                ReaderAuthorClassification(
                    author_id="urn:cts:greekLit:tlg0012",
                    language="grc",
                    source_author_id="tlg0012",
                    canonical_name="Homer",
                    agent_kind="person",
                    historicity_status="traditional",
                    prominence_score=100,
                    prominence_tier="canonical",
                    confidence="high",
                    note="Fixture",
                    generator_models="fixture",
                    generator_run_id="run-1",
                )
            ],
        )

        coverage = reader_discovery_coverage(catalog_path)

    by_language = {row["language"]: row for row in coverage}
    assert by_language["grc"] == {
        "language": "grc",
        "work_count": 1,
        "author_count": 1,
        "segment_count": 12,
        "token_count": 120,
        "classified_work_count": 1,
        "discoverable_work_count": 1,
        "classified_author_count": 1,
        "group_count": 1,
        "tag_count": 2,
        "has_discovery_facets": True,
        "has_author_classifications": True,
        "supported_reader_language": True,
    }
    assert by_language["eng"]["work_count"] == 1
    assert by_language["eng"]["classified_work_count"] == 0
    assert by_language["eng"]["has_discovery_facets"] is False
    assert by_language["eng"]["supported_reader_language"] is False


def test_register_work_classifications_can_merge_without_dropping_other_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        create_catalog_db(catalog_path)
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="lat-1",
                    category="Epic",
                    period="augustan",
                    date_range="1st century BCE",
                    authorship_status="single_attributed",
                    popularity_score=100,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=100,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Latin row",
                    generator_models="test",
                    generator_run_id="run-1",
                    source_file="latin.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic",
                    global_popularity_score=100,
                    global_popularity_tier="canonical",
                    group_popularity_score=100,
                    group_popularity_tier="canonical",
                )
            ],
        )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="grc-1",
                    category="Drama",
                    period="classical",
                    date_range="5th century BCE",
                    authorship_status="single_attributed",
                    popularity_score=88,
                    popularity_tier="major",
                    scope="Drama",
                    scope_popularity_score=91,
                    scope_popularity_tier="major",
                    confidence="high",
                    note="Greek row",
                    generator_models="test",
                    generator_run_id="run-2",
                    source_file="greek.csv",
                    discovery_group_id="drama",
                    discovery_tags="drama",
                    global_popularity_score=88,
                    global_popularity_tier="major",
                    group_popularity_score=91,
                    group_popularity_tier="major",
                )
            ],
            merge=True,
        )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="lat-1",
                    category="Epic",
                    period="augustan",
                    date_range="1st century BCE",
                    authorship_status="single_attributed",
                    popularity_score=99,
                    popularity_tier="canonical",
                    scope="Epic",
                    scope_popularity_score=99,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Updated Latin row",
                    generator_models="test",
                    generator_run_id="run-3",
                    source_file="latin-updated.csv",
                    discovery_group_id="epic",
                    discovery_tags="epic|poetry",
                    global_popularity_score=99,
                    global_popularity_tier="canonical",
                    group_popularity_score=99,
                    group_popularity_tier="canonical",
                )
            ],
            merge=True,
        )
        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT work_id, global_popularity_score
                FROM work_classifications
                ORDER BY work_id
                """
            ).fetchall()
            tags = conn.execute(
                """
                SELECT work_id, tag_id
                FROM work_classification_tags
                ORDER BY work_id, tag_id
                """
            ).fetchall()

    assert rows == [("grc-1", 88), ("lat-1", 99)]
    assert tags == [("grc-1", "drama"), ("lat-1", "epic"), ("lat-1", "poetry")]


def test_prune_stale_work_classifications_removes_wrong_language_generated_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = reader_catalog_path(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:phi:civ0007.001",
            collection_id="phi",
            language="eng",
            title="Paradise Lost (English)",
            author="John Milton (English and Latin)",
            author_id="civ0007",
            source_id="civ0007.001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="urn:cts:latinLit:phi0690.phi003",
            collection_id="phi",
            language="lat",
            title="Aeneis",
            author="Vergil",
            author_id="urn:cts:latinLit:phi0690",
            source_id="phi0690.phi003",
        )
        register_work_classifications(
            catalog_path,
            [
                ReaderWorkClassification(
                    work_id="langnet:reader:phi:civ0007.001",
                    category="Epic",
                    period="Early Modern",
                    date_range="",
                    authorship_status="single_attributed",
                    popularity_score=95,
                    popularity_tier="canonical",
                    scope="Latin Epic Poetry",
                    scope_popularity_score=95,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Generated while this row was still tagged as Latin.",
                    generator_models="test",
                    generator_run_id="reader-classifier-latin",
                    source_file="examples/debug/latin-generated-discovery-b50.csv",
                    discovery_group_id="poetry",
                    discovery_tags="poetry|epic",
                    global_popularity_score=95,
                    global_popularity_tier="canonical",
                    group_popularity_score=95,
                    group_popularity_tier="canonical",
                ),
                ReaderWorkClassification(
                    work_id="urn:cts:latinLit:phi0690.phi003",
                    category="Epic",
                    period="Augustan",
                    date_range="",
                    authorship_status="single_attributed",
                    popularity_score=100,
                    popularity_tier="canonical",
                    scope="Latin Epic Poetry",
                    scope_popularity_score=100,
                    scope_popularity_tier="canonical",
                    confidence="high",
                    note="Correct Latin row.",
                    generator_models="test",
                    generator_run_id="reader-classifier-latin",
                    source_file="examples/debug/latin-generated-discovery-b50.csv",
                    discovery_group_id="poetry",
                    discovery_tags="poetry|epic",
                    global_popularity_score=100,
                    global_popularity_tier="canonical",
                    group_popularity_score=100,
                    group_popularity_tier="canonical",
                ),
            ],
        )

        dry_run = prune_stale_work_classifications(catalog_path, dry_run=True)
        applied = prune_stale_work_classifications(catalog_path)
        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            rows = conn.execute(
                "SELECT work_id FROM work_classifications ORDER BY work_id"
            ).fetchall()
            tags = conn.execute(
                "SELECT work_id, tag_id FROM work_classification_tags ORDER BY work_id, tag_id"
            ).fetchall()

    assert dry_run["candidate_count"] == 1
    assert dry_run["removed_count"] == 0
    assert applied["candidate_count"] == 1
    assert applied["removed_count"] == 1
    assert rows == [("urn:cts:latinLit:phi0690.phi003",)]
    assert tags == [
        ("urn:cts:latinLit:phi0690.phi003", "epic"),
        ("urn:cts:latinLit:phi0690.phi003", "poetry"),
    ]


def test_list_works_handles_legacy_classification_table_without_scope_columns() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                CREATE TABLE works (
                    work_id VARCHAR PRIMARY KEY,
                    collection_id VARCHAR NOT NULL,
                    language VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    author VARCHAR NOT NULL,
                    author_id VARCHAR,
                    source_id VARCHAR NOT NULL,
                    cts_work_urn VARCHAR
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE artifacts (
                    artifact_id VARCHAR PRIMARY KEY,
                    work_id VARCHAR NOT NULL,
                    edition_id VARCHAR NOT NULL,
                    artifact_path VARCHAR NOT NULL,
                    source_path VARCHAR NOT NULL,
                    adapter VARCHAR NOT NULL,
                    source_hash VARCHAR NOT NULL,
                    segment_count INTEGER NOT NULL,
                    token_count INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE work_classifications (
                    work_id VARCHAR PRIMARY KEY,
                    category VARCHAR NOT NULL,
                    period VARCHAR NOT NULL,
                    date_range VARCHAR NOT NULL,
                    authorship_status VARCHAR NOT NULL,
                    popularity_score INTEGER,
                    popularity_tier VARCHAR NOT NULL,
                    confidence VARCHAR NOT NULL,
                    note TEXT NOT NULL,
                    generator_models TEXT NOT NULL,
                    generator_run_id VARCHAR NOT NULL,
                    source_file VARCHAR NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO works VALUES (
                    'work-1', 'fixture', 'grc', 'De materia medica',
                    'Dioscorides', 'tlg0001', 'tlg0001.001', NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO work_classifications VALUES (
                    'work-1', 'Medical Text', 'Roman Imperial', '1st century CE',
                    'single_attributed', 65, 'common', 'high',
                    'Important medical text.', 'test', 'run', 'legacy.csv'
                )
                """
            )

        works = list_works(catalog_path, language="grc")

    assert works[0]["classification_category"] == "Medical Text"
    assert works[0]["classification_scope"] is None
    assert works[0]["classification_scope_popularity_score"] is None


def test_catalog_routes_address_to_book_db() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "odyssey.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)

        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0012.tlg002",
            collection_id="perseus",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
            cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
        )
        edition = ReaderEdition(
            edition_id="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
            work_id=work.work_id,
            label="Perseus Greek edition",
            language="grc",
            source_path=root / "odyssey.xml",
            cts_edition_urn="urn:cts:greekLit:tlg0012.tlg002.perseus-grc2",
        )
        artifact = ReaderBookArtifact(
            artifact_id="odyssey-grc2",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=root / "odyssey.xml",
            adapter="fixture",
            source_hash="hash",
            segment_count=1,
            token_count=2,
        )
        register_book(catalog_path, work, edition, artifact)
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id="odyssey-3-74",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="line",
                    citation_path="3.74",
                    text="ψυχὰς παρθέμενοι",
                    source_text="ψυχὰς παρθέμενοι [source]",
                    normalized_text="ψυχας παρθεμενοι",
                    sort_key=74,
                )
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id="odyssey-3-74",
                    address="urn:cts:greekLit:tlg0012.tlg002:3.74",
                    address_kind="cts",
                    citation_path="3.74",
                ),
                ReaderSegmentAddress(
                    segment_id="odyssey-3-74",
                    address="Od. 3.74",
                    address_kind="alias",
                    citation_path="3.74",
                ),
            ],
        )

        routed = lookup_artifact_for_address(catalog_path, "urn:cts:greekLit:tlg0012.tlg002:3.74")
        segment = lookup_segment_by_address(catalog_path, "Od. 3.74")
        works = list_works(catalog_path, language="grc")

        assert routed is not None
        assert routed["artifact_path"] == str(book_path)
        assert segment is not None
        assert segment["text"] == "ψυχὰς παρθέμενοι"
        assert segment["source_text"] == "ψυχὰς παρθέμενοι [source]"
        assert works == [
            {
                "work_id": work.work_id,
                "collection_id": "perseus",
                "language": "grc",
                "title": "Odyssey",
                "author": "Homer",
                "author_id": "urn:cts:greekLit:tlg0012",
                "source_author": "Homer",
                "source_author_id": "urn:cts:greekLit:tlg0012",
                "canonical_author_id": "urn:cts:greekLit:tlg0012",
                "canonical_author_name": "Homer",
                "canonical_author_kind": "",
                "source_id": "tlg0012.tlg002",
                "source_label": "PERSEUS tlg0012.tlg002",
                "edition_label": "PERSEUS reader text",
                "short_disambiguation_label": "tlg0012.tlg002",
                "cts_work_urn": work.cts_work_urn,
                "work_kind": "work",
                "parent_work_id": None,
                "start_citation": None,
                "end_citation": None,
                "word_count": 2,
                "word_count_method": "whitespace_tokens",
                "classification_category": None,
                "classification_period": None,
                "classification_date_range": None,
                "classification_authorship_status": None,
                "classification_popularity_score": None,
                "classification_popularity_tier": None,
                "classification_scope": None,
                "classification_scope_popularity_score": None,
                "classification_scope_popularity_tier": None,
                "classification_discovery_group_id": None,
                "classification_discovery_tags": None,
                "classification_global_popularity_score": None,
                "classification_global_popularity_tier": None,
                "classification_group_popularity_score": None,
                "classification_group_popularity_tier": None,
                "classification_confidence": None,
                "classification_notes": None,
                "classification_generator_models": None,
                "classification_generator_run_id": None,
                "classification_source_file": None,
                "source_metadata_summary": "",
                "metadata_attributions": [],
                "translator_names": [],
                "traditional_author_names": [],
                "attributed_author_names": [],
            }
        ]


def test_contained_work_lists_and_reads_parent_segments() -> None:
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
            cts_work_urn=None,
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS edition",
            language="san",
            source_path=root / "mahabharata.conllu",
            cts_edition_urn=None,
        )
        register_book(
            catalog_path,
            work,
            edition,
            ReaderBookArtifact(
                artifact_id="mbh-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=4,
                token_count=20,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:a",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="before",
                    text="before",
                    normalized_text="before",
                    sort_key=1,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:start",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="start",
                    text="dharmakṣetre",
                    normalized_text="dharmaksetre",
                    sort_key=2,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:end",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="end",
                    text="yatra yogeśvaraḥ kṛṣṇaḥ",
                    normalized_text="yatra yogesvarah krsnah",
                    sort_key=3,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:after",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="sentence",
                    citation_path="after",
                    text="after",
                    normalized_text="after",
                    sort_key=4,
                ),
            ],
            addresses=[],
        )
        register_contained_works(
            catalog_path,
            [
                ReaderContainedWork(
                    contained_work_id="langnet:reader:contained:sanskrit:bhagavadgita",
                    parent_work_id=work.work_id,
                    collection_id="contained",
                    language="san",
                    title="Bhagavadgītā",
                    author="Vyāsa",
                    source_id="dcs_154:bhagavadgita",
                    cts_work_urn="urn:cts:sanskritLit:mbh.bhg",
                    start_citation="start",
                    end_citation="end",
                    status="accepted",
                    confidence="medium",
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

        works = list_works(catalog_path, language="san", query="gītā")
        segments = list_segments_for_work(
            catalog_path,
            "langnet:reader:contained:sanskrit:bhagavadgita",
            limit=10,
        )
        shown = lookup_segment_by_work_and_citation(
            catalog_path,
            "urn:cts:sanskritLit:mbh.bhg",
            "start",
        )
        authors = list_author_index(catalog_path, language="san", query="vyāsa")
        vyasa_author_id = next(
            item["author_id"] for item in authors if item["display_name"] == "Vyāsa"
        )
        author_works = list_works(catalog_path, language="san", author_id=vyasa_author_id)

    assert [work["title"] for work in works] == ["Bhagavadgītā"]
    assert works[0]["word_count"] == CONTAINED_BHG_FIXTURE_WORD_COUNT
    assert any(work["title"] == "Bhagavadgītā" for work in author_works)
    assert [segment["citation_path"] for segment in segments] == ["start", "end"]
    assert shown is not None
    assert shown["text"] == "dharmakṣetre"
    vyasa = next(item for item in authors if item["display_name"] == "Vyāsa")
    assert vyasa["word_count"] == CONTAINED_BHG_FIXTURE_WORD_COUNT, vyasa


def test_author_index_merges_duplicate_generated_selectors() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="mandana-1",
            collection_id="sanskrit",
            language="san",
            title="Brahmasiddhi",
            author="Mandanamiśra",
            author_id=None,
            source_id="mandana.1",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="mandana-2",
            collection_id="sanskrit",
            language="san",
            title="Vibhramaviveka",
            author="Maṇḍanamiśra",
            author_id=None,
            source_id="mandana.2",
        )

        authors = list_author_index(catalog_path, language="san", query="mandana")

    assert len(authors) == 1
    assert authors[0]["author_id"] == "langnet:reader:author:san:mandanamisra"
    assert authors[0]["display_name"] == "Maṇḍanamiśra"
    assert authors[0]["work_count"] == MANDANA_FIXTURE_WORK_COUNT
    assert authors[0]["representative_titles"] == "Brahmasiddhi | Vibhramaviveka"


def test_work_map_for_work_returns_curated_nodes_with_range_word_counts() -> None:
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
            source_id="dcs_bhg",
            cts_work_urn="urn:cts:sanskritLit:mbh.bhg",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS edition",
            language="san",
            source_path=root / "bhagavadgita.conllu",
            cts_edition_urn=None,
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
                segment_count=3,
                token_count=10,
            ),
        )
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:1",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="verse",
                    citation_path="start",
                    text="dharma kṣetre kurukṣetre",
                    normalized_text="dharma ksetre kuruksetre",
                    sort_key=1,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:2",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="verse",
                    citation_path="middle",
                    text="arjuna uvāca",
                    normalized_text="arjuna uvaca",
                    sort_key=2,
                ),
                ReaderSegment(
                    segment_id=f"{work.work_id}:3",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="verse",
                    citation_path="end",
                    text="saṃjaya uvāca",
                    normalized_text="samjaya uvaca",
                    sort_key=3,
                ),
            ],
            addresses=[],
        )
        register_work_map_nodes(
            catalog_path,
            [
                ReaderWorkMapNode(
                    work_id=work.work_id,
                    node_id="bhg-01",
                    level=1,
                    kind="chapter",
                    label="Arjuna Viṣāda Yoga",
                    native_label="अर्जुनविषादयोग",
                    ordinal=1,
                    start_citation="start",
                    end_citation="end",
                    provenance="curated",
                    confidence="high",
                    status="accepted",
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

        payload = work_map_for_work(catalog_path, work.work_id)

    assert len(payload) == 1
    assert payload[0]["node_id"] == "bhg-01"
    assert payload[0]["label"] == "Arjuna Viṣāda Yoga"
    assert payload[0]["word_count"] == WORK_MAP_FIXTURE_WORD_COUNT
    assert payload[0]["word_count_method"] == "whitespace_tokens"
    assert payload[0]["provenance"] == "curated"
    assert payload[0]["confidence"] == "high"


def test_duplicate_author_audit_reports_display_collisions_not_many_works() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "fixture.duckdb"
        create_catalog_db(catalog_path)
        create_book_db(book_path)

        for work in (
            ReaderWork(
                work_id="langnet:reader:tlg:tlg0532.001",
                collection_id="tlg",
                language="grc",
                title="Leucippe et Clitophon",
                author="Achilles Tatius",
                author_id="urn:cts:greekLit:tlg0532",
                source_id="tlg0532.001",
                cts_work_urn="urn:cts:greekLit:tlg0532.tlg001",
            ),
            ReaderWork(
                work_id="langnet:reader:tlg:tlg2133.001",
                collection_id="tlg",
                language="grc",
                title="Isagoga excerpta",
                author="Achilles Tatius",
                author_id="tlg2133",
                source_id="tlg2133.001",
                cts_work_urn=None,
            ),
            ReaderWork(
                work_id="langnet:reader:tlg:tlg0012.001",
                collection_id="tlg",
                language="grc",
                title="Ilias",
                author="Homer",
                author_id="tlg0012",
                source_id="tlg0012.001",
                cts_work_urn=None,
            ),
            ReaderWork(
                work_id="langnet:reader:tlg:tlg0012.002",
                collection_id="tlg",
                language="grc",
                title="Odyssea",
                author="Homer",
                author_id="tlg0012",
                source_id="tlg0012.002",
                cts_work_urn=None,
            ),
        ):
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="fixture",
                language=work.language,
                source_path=root / f"{work.source_id}.txt",
                cts_edition_urn=None,
            )
            register_book(
                catalog_path,
                work,
                edition,
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}:artifact",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    artifact_path=book_path,
                    source_path=edition.source_path,
                    adapter="fixture",
                    source_hash="hash",
                    segment_count=1,
                    token_count=1,
                ),
            )

        audit = list_duplicate_audit(catalog_path, kind="authors", language="grc")

    assert len(audit) == 1
    assert audit[0]["display"] == "Achilles Tatius"
    assert audit[0]["authority_count"] == len(audit[0]["author_ids"])
    assert audit[0]["suggested_policy"] == "review_authority_collision"


def test_register_books_bulk_writes_catalog_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        entries = []
        for index in range(2):
            work = ReaderWork(
                work_id=f"langnet:reader:test:work{index}",
                collection_id="test",
                language="lat",
                title=f"Work {index}",
                author="Author",
                author_id="urn:cts:latinLit:phi0001",
                source_id=f"work{index}",
                cts_work_urn=f"urn:cts:latinLit:phi0001.phi00{index}" if index else None,
            )
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="fixture",
                language="lat",
                source_path=root / f"work{index}.txt",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"artifact-{index}",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=root / f"work{index}.duckdb",
                source_path=edition.source_path,
                adapter="fixture",
                source_hash=f"hash-{index}",
                segment_count=1,
                token_count=2,
            )
            entries.append((work, edition, artifact))

        register_books(catalog_path, entries)

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            work_count_row = conn.execute("SELECT COUNT(*) FROM works").fetchone()
            edition_count_row = conn.execute("SELECT COUNT(*) FROM editions").fetchone()
            artifact_count_row = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()
            assert work_count_row is not None
            assert edition_count_row is not None
            assert artifact_count_row is not None
            work_count = work_count_row[0]
            edition_count = edition_count_row[0]
            artifact_count = artifact_count_row[0]

    assert (work_count, edition_count, artifact_count) == (2, 2, 2)


def test_register_segment_rows_preserves_missing_source_text_as_null() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        book_path = Path(tmpdir) / "book.duckdb"
        segment = ReaderSegment(
            segment_id="seg-1",
            work_id="work",
            edition_id="edition",
            segment_kind="line",
            citation_path="1",
            text="arma virumque",
            normalized_text="arma virumque",
            sort_key=1,
        )

        register_segment_rows(
            book_path,
            segments=[segment],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=segment.segment_id,
                    address="work:1",
                    address_kind="langnet",
                    citation_path="1",
                )
            ],
        )

        with duckdb.connect(str(book_path), read_only=True) as conn:
            row = conn.execute("SELECT source_text FROM segments").fetchone()
            assert row is not None
            source_text = row[0]

    assert source_text is None


def test_register_books_bulk_keeps_last_duplicate_catalog_row() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        entries = []
        for title, source_hash in [("First", "hash-1"), ("Second", "hash-2")]:
            work = ReaderWork(
                work_id="langnet:reader:test:duplicate",
                collection_id="test",
                language="lat",
                title=title,
                author="Author",
                author_id=None,
                source_id="duplicate",
                cts_work_urn=None,
            )
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="fixture",
                language="lat",
                source_path=root / f"{source_hash}.txt",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id="duplicate-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=root / "duplicate.duckdb",
                source_path=edition.source_path,
                adapter="fixture",
                source_hash=source_hash,
                segment_count=1,
                token_count=2,
            )
            entries.append((work, edition, artifact))

        register_books(catalog_path, entries)

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT w.title, a.source_hash
                FROM works w
                JOIN artifacts a ON a.work_id = w.work_id
                """
            ).fetchall()

    assert rows == [("Second", "hash-2")]


def test_catalog_routes_langnet_address_without_scanning_unrelated_books() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)
        target_book = root / "books" / "target.duckdb"
        other_book = root / "books" / "other.duckdb"

        for work_id, book_path in [
            ("langnet:reader:sanskrit_dcs:dcs_431", target_book),
            ("langnet:reader:sanskrit_dcs:dcs_000", other_book),
        ]:
            create_book_db(book_path)
            work = ReaderWork(
                work_id=work_id,
                collection_id="sanskrit_dcs",
                language="san",
                title=work_id.rsplit(":", 1)[-1],
                author="Unknown",
                author_id=None,
                source_id=work_id.rsplit(":", 1)[-1],
                cts_work_urn=None,
            )
            edition = ReaderEdition(
                edition_id=f"{work_id}:edition",
                work_id=work.work_id,
                label="DCS edition",
                language="san",
                source_path=root / f"{work.source_id}.conllu",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"{work.source_id}-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=2,
            )
            register_book(catalog_path, work, edition, artifact)

        probe_paths: list[Path] = []

        def fake_has_address(book_path: Path, address: str) -> bool:
            probe_paths.append(book_path)
            return book_path == target_book

        with mock.patch("langnet.reader.storage._book_has_address", side_effect=fake_has_address):
            routed = lookup_artifact_for_address(
                catalog_path,
                "langnet:reader:sanskrit_dcs:dcs_431:561939",
            )

        assert routed is not None
        assert routed["artifact_path"] == str(target_book)
        assert probe_paths == [target_book]


def test_catalog_routes_cts_urn_overlay_to_internal_work_address() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "books" / "bhagavadgita.duckdb"
        create_book_db(book_path)
        work = ReaderWork(
            work_id="langnet:reader:sanskrit_dcs:dcs_bhagavadgita",
            collection_id="sanskrit_dcs",
            language="san",
            title="Bhagavadgītā",
            author="Vyāsa",
            author_id=None,
            source_id="dcs_bhagavadgita",
            cts_work_urn="urn:cts:sanskritLit:mbh.bhg",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}:edition",
            work_id=work.work_id,
            label="DCS edition",
            language="san",
            source_path=root / "bhagavadgita.conllu",
            cts_edition_urn=None,
        )
        artifact = ReaderBookArtifact(
            artifact_id="bhagavadgita-artifact",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=1,
            token_count=4,
        )
        register_book(catalog_path, work, edition, artifact)
        register_segment_rows(
            book_path,
            segments=[
                ReaderSegment(
                    segment_id=f"{work.work_id}:1.1",
                    work_id=work.work_id,
                    edition_id=edition.edition_id,
                    segment_kind="verse",
                    citation_path="1.1",
                    text="dhṛtarāṣṭra uvāca",
                    normalized_text="dhrtarastra uvaca",
                    sort_key=1,
                )
            ],
            addresses=[
                ReaderSegmentAddress(
                    segment_id=f"{work.work_id}:1.1",
                    address=f"{work.work_id}:1.1",
                    address_kind="langnet",
                    citation_path="1.1",
                )
            ],
        )

        contents = list_segments_for_work(catalog_path, "urn:cts:sanskritLit:mbh.bhg")
        segment = lookup_segment_by_address(catalog_path, "urn:cts:sanskritLit:mbh.bhg:1.1")

    assert [row["citation_path"] for row in contents] == ["1.1"]
    assert segment is not None
    assert segment["work_id"] == work.work_id
    assert segment["text"] == "dhṛtarāṣṭra uvāca"


def test_list_works_filters_display_author_and_authorship_claims() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        create_catalog_db(catalog_path)

        for work_id, title, author, source_id in [
            ("urn:cts:greekLit:tlg0059.tlg001", "Euthyphro", "Plato", "tlg0059.tlg001"),
            (
                "urn:cts:greekLit:tlg0059.tlg999",
                "Pseudo-Platonic Test",
                "Pseudo-Plato",
                "tlg0059.tlg999",
            ),
            (
                "urn:cts:greekLit:tlg0086.tlg001",
                "Categories",
                "Aristotle",
                "tlg0086.tlg001",
            ),
        ]:
            book_path = root / "books" / f"{source_id}.duckdb"
            create_book_db(book_path)
            work = ReaderWork(
                work_id=work_id,
                collection_id="perseus",
                language="grc",
                title=title,
                author=author,
                author_id=None,
                source_id=source_id,
                cts_work_urn=work_id,
            )
            edition = ReaderEdition(
                edition_id=f"{work_id}.edition",
                work_id=work.work_id,
                label="Fixture edition",
                language="grc",
                source_path=root / f"{source_id}.xml",
                cts_edition_urn=f"{work_id}.edition",
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"{source_id}-artifact",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=0,
                token_count=0,
            )
            register_book(catalog_path, work, edition, artifact)

        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="perseus",
                    match_field="work_id",
                    match_value="urn:cts:greekLit:tlg0086.tlg001",
                    relation_type="possible_author",
                    agent="Plato",
                    status="accepted",
                    confidence="low",
                    note="Fixture possible authorship claim.",
                    source_file="fixture",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://example.org/plato-claim",
                            label="Fixture source records the possible attribution.",
                            retrieved_at="2026-05-14",
                        ),
                    ),
                )
            ],
        )

        display_matches = list_works(catalog_path, author="Plato")
        attribution_matches = list_works(catalog_path, attributed_to="Plato")
        filtered_attribution_matches = list_works(
            catalog_path,
            language="grc",
            attributed_to="Plato",
        )
        pseudo_matches = list_works(catalog_path, author="Pseudo-Plato")

    assert [row["title"] for row in display_matches] == ["Euthyphro"]
    assert {row["title"] for row in attribution_matches} == {"Categories", "Euthyphro"}
    assert {row["title"] for row in filtered_attribution_matches} == {
        "Categories",
        "Euthyphro",
    }
    assert [row["title"] for row in pseudo_matches] == ["Pseudo-Platonic Test"]


def test_list_metadata_overlays_tolerates_catalog_without_overlay_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "old_catalog.duckdb"
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                CREATE TABLE works (
                    work_id VARCHAR PRIMARY KEY,
                    collection_id VARCHAR NOT NULL,
                    language VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    author VARCHAR NOT NULL,
                    author_id VARCHAR,
                    source_id VARCHAR NOT NULL,
                    cts_work_urn VARCHAR
                )
                """
            )

        assert list_metadata_overlays(catalog_path) == []


def test_list_works_attributed_to_tolerates_catalog_without_attribution_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "old_catalog.duckdb"
        create_catalog_db(catalog_path)
        book_path = Path(tmpdir) / "book.duckdb"
        create_book_db(book_path)
        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0059.tlg001",
            collection_id="perseus",
            language="grc",
            title="Euthyphro",
            author="Plato",
            author_id=None,
            source_id="tlg0059.tlg001",
            cts_work_urn="urn:cts:greekLit:tlg0059.tlg001",
        )
        edition = ReaderEdition(
            edition_id=f"{work.work_id}.edition",
            work_id=work.work_id,
            label="Fixture edition",
            language="grc",
            source_path=Path(tmpdir) / "euthyphro.xml",
            cts_edition_urn=f"{work.work_id}.edition",
        )
        artifact = ReaderBookArtifact(
            artifact_id="euthyphro-artifact",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=0,
            token_count=0,
        )
        register_book(catalog_path, work, edition, artifact)
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute("DROP TABLE metadata_attributions")

        matches = list_works(catalog_path, attributed_to="Plato")

    assert [row["title"] for row in matches] == ["Euthyphro"]


def test_list_works_matches_author_id_attribution_after_display_author_overlay() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = reader_catalog_path(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:phi:civ0004.001",
            collection_id="phi",
            language="lat",
            title="Genesis",
            author="Saint Jerome",
            author_id="urn:cts:latinLit:stoa0162",
            source_id="civ0004.001",
        )
        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="phi",
                    match_field="author_id",
                    match_value="civ0004",
                    relation_type="translator",
                    agent="Saint Jerome",
                    status="accepted",
                    confidence="high",
                    note="Jerome is the Vulgate translator.",
                    source_file="data/curated/reader_attributions/phi/bible.yaml",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://catalog.perseus.org/catalog/urn:cite:perseus:author.785",
                            label="Perseus records Jerome as translator.",
                            retrieved_at="2026-05-17",
                        ),
                    ),
                )
            ],
        )

        matches = list_works(catalog_path, attributed_to="Jerome")

    assert [row["title"] for row in matches] == ["Genesis"]
    assert matches[0]["translator_names"] == ["Saint Jerome"]
    assert matches[0]["traditional_author_names"] == []
    assert matches[0]["attributed_author_names"] == []
    assert matches[0]["metadata_attributions"] == [
        {
            "relation_type": "translator",
            "agent": "Saint Jerome",
            "status": "accepted",
            "confidence": "high",
            "note": "Jerome is the Vulgate translator.",
            "evidence_citation": "https://catalog.perseus.org/catalog/urn:cite:perseus:author.785",
            "evidence_label": "Perseus records Jerome as translator.",
        }
    ]


def test_list_works_matches_septuagint_author_id_attributions_across_source_families() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = reader_catalog_path(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:phi:civ0002.001",
            collection_id="phi",
            language="grc",
            title="Genesis",
            author="Septuagint (Old Greek Bible)",
            author_id="civ0002",
            source_id="civ0002.001",
        )
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:tlg:tlg0527.001",
            collection_id="tlg",
            language="grc",
            title="Genesis",
            author="Unknown",
            author_id="urn:cts:greekLit:tlg0527",
            source_id="tlg0527.001",
        )
        evidence = (
            ReaderMetadataOverlayEvidence(
                source_type="web_source",
                citation="https://www.britannica.com/topic/Septuagint",
                label="Britannica records the Septuagint seventy-two translator tradition.",
                retrieved_at="2026-05-17",
            ),
        )
        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="phi",
                    match_field="author_id",
                    match_value="civ0002",
                    relation_type="translator",
                    agent="Seventy-two translators",
                    status="accepted",
                    confidence="medium",
                    note="Traditional Septuagint translator attribution.",
                    source_file="data/curated/reader_attributions/phi/bible.yaml",
                    evidence=evidence,
                ),
                ReaderMetadataAttribution(
                    collection_id="tlg",
                    match_field="author_id",
                    match_value="tlg0527",
                    relation_type="translator",
                    agent="Seventy-two translators",
                    status="accepted",
                    confidence="medium",
                    note="Traditional Septuagint translator attribution.",
                    source_file="data/curated/reader_attributions/phi/bible.yaml",
                    evidence=evidence,
                ),
            ],
        )

        matches = list_works(catalog_path, attributed_to="Seventy-two translators")

    assert {row["work_id"] for row in matches} == {
        "langnet:reader:phi:civ0002.001",
        "langnet:reader:tlg:tlg0527.001",
    }
    assert all(row["translator_names"] == ["Seventy-two translators"] for row in matches)


def test_registers_and_lists_metadata_attributions() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.duckdb"
        create_catalog_db(catalog_path)
        register_metadata_attributions(
            catalog_path,
            [
                ReaderMetadataAttribution(
                    collection_id="sanskrit_dcs",
                    match_field="source_id",
                    match_value="dcs_example",
                    relation_type="possible_author",
                    agent="Aristotle",
                    status="accepted",
                    confidence="medium",
                    note="Accepted as a recorded attribution claim.",
                    source_file="data/curated/reader_attributions/sanskrit/example.yaml",
                    evidence=(
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://example.org/source",
                            label="Source records the possible attribution.",
                            retrieved_at="2026-05-13",
                        ),
                        ReaderMetadataOverlayEvidence(
                            source_type="web_source",
                            citation="https://example.org/source-2",
                            label="Second source records the same possible attribution.",
                            retrieved_at="2026-05-14",
                        ),
                    ),
                )
            ],
        )

        rows = list_metadata_attributions(
            catalog_path,
            collection_id="sanskrit_dcs",
            relation_type="possible_author",
            agent="Aristotle",
        )

    assert rows == [
        {
            "collection_id": "sanskrit_dcs",
            "match_field": "source_id",
            "match_value": "dcs_example",
            "relation_type": "possible_author",
            "agent": "Aristotle",
            "status": "accepted",
            "confidence": "medium",
            "note": "Accepted as a recorded attribution claim.",
            "source_file": "data/curated/reader_attributions/sanskrit/example.yaml",
            "evidence_source_type": "web_source",
            "evidence_citation": "https://example.org/source",
            "evidence_label": "Source records the possible attribution.",
            "evidence_retrieved_at": "2026-05-13",
        }
    ]


def test_list_metadata_attributions_tolerates_catalog_without_table() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "old_catalog.duckdb"
        with duckdb.connect(str(catalog_path)) as conn:
            conn.execute(
                """
                CREATE TABLE works (
                    work_id VARCHAR PRIMARY KEY,
                    collection_id VARCHAR NOT NULL,
                    language VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    author VARCHAR NOT NULL,
                    author_id VARCHAR,
                    source_id VARCHAR NOT NULL,
                    cts_work_urn VARCHAR
                )
                """
            )

        assert list_metadata_attributions(catalog_path) == []


def test_catalog_routes_work_address_to_edition_containing_segment() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        work = ReaderWork(
            work_id="urn:cts:greekLit:tlg0012.tlg002",
            collection_id="perseus",
            language="grc",
            title="Odyssey",
            author="Homer",
            author_id="urn:cts:greekLit:tlg0012",
            source_id="tlg0012.tlg002",
            cts_work_urn="urn:cts:greekLit:tlg0012.tlg002",
        )
        for edition_suffix, citation_path, text in [
            ("perseus-eng3", "1.1", "Tell me, Muse"),
            ("perseus-grc2", "3.74", "ψυχὰς παρθέμενοι"),
        ]:
            book_path = root / "books" / f"{edition_suffix}.duckdb"
            edition = ReaderEdition(
                edition_id=f"{work.work_id}.{edition_suffix}",
                work_id=work.work_id,
                label=edition_suffix,
                language="eng" if "eng" in edition_suffix else "grc",
                source_path=root / f"{edition_suffix}.xml",
                cts_edition_urn=f"{work.work_id}.{edition_suffix}",
            )
            artifact = ReaderBookArtifact(
                artifact_id=edition_suffix,
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=book_path,
                source_path=edition.source_path,
                adapter="fixture",
                source_hash="hash",
                segment_count=1,
                token_count=2,
            )
            register_book(catalog_path, work, edition, artifact)
            register_segment_rows(
                book_path,
                segments=[
                    ReaderSegment(
                        segment_id=f"{work.work_id}:{citation_path}",
                        work_id=work.work_id,
                        edition_id=edition.edition_id,
                        segment_kind="line",
                        citation_path=citation_path,
                        text=text,
                        normalized_text=text.casefold(),
                        sort_key=1,
                    )
                ],
                addresses=[
                    ReaderSegmentAddress(
                        segment_id=f"{work.work_id}:{citation_path}",
                        address=f"{work.work_id}:{citation_path}",
                        address_kind="cts",
                        citation_path=citation_path,
                    )
                ],
            )

        segment = lookup_segment_by_address(catalog_path, f"{work.work_id}:3.74")

        assert segment is not None
        assert segment["edition_id"] == "urn:cts:greekLit:tlg0012.tlg002.perseus-grc2"
        assert segment["text"] == "ψυχὰς παρθέμενοι"


def test_shared_book_db_can_hold_multiple_work_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        shared_book_path = root / "books" / "shared.duckdb"
        create_catalog_db(catalog_path)
        entries = []
        for index, work_id in enumerate(
            ["langnet:reader:tlg:tlg0012.001", "langnet:reader:tlg:tlg0012.002"],
            start=1,
        ):
            work = ReaderWork(
                work_id=work_id,
                collection_id="tlg",
                language="grc",
                title=f"Work {index}",
                author="Homer",
                author_id="urn:cts:greekLit:tlg0012",
                source_id=f"tlg0012.00{index}",
                cts_work_urn=f"urn:cts:greekLit:tlg0012.tlg00{index}",
            )
            edition = ReaderEdition(
                edition_id=f"{work.work_id}:edition",
                work_id=work.work_id,
                label="legacy text dump + IDT",
                language="grc",
                source_path=root / "tlg0012.txt",
                cts_edition_urn=None,
            )
            artifact = ReaderBookArtifact(
                artifact_id=f"artifact-{index}",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                artifact_path=shared_book_path,
                source_path=edition.source_path,
                adapter="tlg_idt_legacy",
                source_hash="hash",
                segment_count=1,
                token_count=2,
            )
            register_segment_rows(
                shared_book_path,
                segments=[
                    ReaderSegment(
                        segment_id=f"{work.work_id}:1.1",
                        work_id=work.work_id,
                        edition_id=edition.edition_id,
                        segment_kind="line",
                        citation_path="1.1",
                        text=f"text {index}",
                        normalized_text=f"text {index}",
                        sort_key=index,
                    )
                ],
                addresses=[
                    ReaderSegmentAddress(
                        segment_id=f"{work.work_id}:1.1",
                        address=f"{work.work_id}:1.1",
                        address_kind="langnet",
                        citation_path="1.1",
                    )
                ],
                replace_work_id=work.work_id,
            )
            entries.append((work, edition, artifact))
        register_books(catalog_path, entries)

        first = lookup_segment_by_address(catalog_path, "langnet:reader:tlg:tlg0012.001:1.1")
        second = lookup_segment_by_address(catalog_path, "urn:cts:greekLit:tlg0012.tlg002:1.1")
        second_contents = list_segments_for_work(
            catalog_path,
            "urn:cts:greekLit:tlg0012.tlg002",
            limit=5,
        )
        with mock.patch("langnet.reader.storage._book_has_address") as book_has_address:
            missing = lookup_segment_by_work_and_citation(
                catalog_path,
                "urn:cts:greekLit:tlg0012.tlg002",
                "9.9",
            )

    assert first is not None
    assert first["text"] == "text 1"
    assert second is not None
    assert second["text"] == "text 2"
    assert [row["text"] for row in second_contents] == ["text 2"]
    assert missing is None
    book_has_address.assert_not_called()


def test_repair_work_languages_dry_run_uses_read_only_catalog_connection() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = reader_catalog_path(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:phi:civ0005.058",
            collection_id="phi",
            language="lat",
            title="John",
            author="English Bible (KJV or AV)",
            author_id="civ0005",
            source_id="civ0005.058",
        )
        original_connect = duckdb.connect
        catalog_calls: list[dict[str, object]] = []

        def tracking_connect(database=":memory:", *args, **kwargs):
            if str(database) == str(catalog_path):
                catalog_calls.append(dict(kwargs))
            return original_connect(database, *args, **kwargs)

        with mock.patch("duckdb.connect", side_effect=tracking_connect):
            result = repair_work_languages(catalog_path, dry_run=True)

    assert result["candidate_count"] == 1
    assert catalog_calls
    assert all(call.get("read_only") is True for call in catalog_calls)


def test_repair_work_languages_uses_phi_source_family_after_author_overlay() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = reader_catalog_path(root)
        _register_fixture_work(
            catalog_path,
            root,
            work_id="langnet:reader:phi:civ0003.002",
            collection_id="phi",
            language="lat",
            title="Mark",
            author="Mark the Evangelist",
            author_id="urn:cts:langnet:author.grc.mark-the-evangelist",
            source_id="civ0003.002",
        )

        result = repair_work_languages(catalog_path, dry_run=True)

    assert result["candidate_count"] == 1
    assert result["repairs"][0]["to_language"] == "grc"
