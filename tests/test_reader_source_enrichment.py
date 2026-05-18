from __future__ import annotations

import tempfile
from pathlib import Path

from langnet.reader.models import (
    ReaderBookArtifact,
    ReaderEdition,
    ReaderWork,
)
from langnet.reader.source_enrichment import (
    parse_dcs_chapter_info_metadata,
    parse_dcs_corpus_table,
    parse_perseus_catalog_results,
    parse_perseus_subject_facets,
    sync_dcs_corpus_metadata,
)
from langnet.reader.storage import (
    create_catalog_db,
    list_source_metadata,
    register_book,
)


def test_parse_dcs_corpus_table_reads_author_time_slot_and_subject() -> None:
    table = """
Text\tAuthor\tTime slot\tSubject\tCompleted\tShow\tBib.\tDict.\tFreq.
Abhidharmakośa\tVasubandhu\tclassical\tBuddhist\t\tS\tB\tD\tF
Aṣṭādhyāyī\tPāṇini\tepic\tPaniniya\t\tS\tB\tD\tF
"""

    rows = parse_dcs_corpus_table(table, source_path=Path("dcs-corpus.tsv"))

    assert rows[0].text == "Abhidharmakośa"
    assert rows[0].author == "Vasubandhu"
    assert rows[0].time_slot == "classical"
    assert rows[0].subject == "Buddhist"
    assert rows[0].has_show is True
    assert rows[1].scope_hint == "Sanskrit Grammar"


def test_parse_dcs_corpus_table_reads_page_text_capture() -> None:
    table = """
DCS - Digital Corpus of Sanskrit
The DCS Corpus
Texts with supervised analysis
Text\tAuthor\tTime slot\tSubject\tCompleted\tShow\tBib.\tDict.\tFreq.
AMTest\t \t---\t---\t \tS\tB\tD\tF
Abhidharmakośa\tVasubandhu\tclassical\tBuddhist\t \tS\tB\tD\tF
February 2026 - Contact, copyright, disclaimer
"""

    rows = parse_dcs_corpus_table(table, source_path=Path("dcs-corpus-interact.txt"))

    assert [row.text for row in rows] == ["AMTest", "Abhidharmakośa"]
    assert rows[0].author == ""
    assert rows[0].subject == ""
    assert rows[1].scope_hint == "Buddhist Scripture"


def test_parse_dcs_chapter_info_metadata_reads_chapter_rows() -> None:
    xml = """
<info>
  <chapter>
    <path>Abhidharmakośa/Abhidharmakośa-0000-AbhidhKo, 1-7024.conllu</path>
    <textName>Abhidharmakośa</textName>
    <textId>378</textId>
    <chapterName>AbhidhKo, 1</chapterName>
    <chapterId>7024</chapterId>
    <chapterPosition>1</chapterPosition>
    <dcsTimeSlot>4</dcsTimeSlot>
  </chapter>
</info>
"""

    rows = parse_dcs_chapter_info_metadata(xml, source_path=Path("chapter-info.xml"))

    assert [(row.subject_id, row.key, row.value) for row in rows] == [
        ("dcs_378", "dcs_chapter_name", "AbhidhKo, 1"),
        ("dcs_378", "dcs_chapter_id", "7024"),
        ("dcs_378", "dcs_chapter_position", "1"),
        (
            "dcs_378",
            "dcs_chapter_path",
            "Abhidharmakośa/Abhidharmakośa-0000-AbhidhKo, 1-7024.conllu",
        ),
        ("dcs_378", "dcs_time_slot", "4"),
    ]


def test_parse_perseus_catalog_results_reads_subject_membership() -> None:
    markdown = """
##### 1. Ars grammatica

URN:
    urn:cts:latinLit:stoa0085b.stoa001.opp-lat2
Author:
    Charisius, Flavius Sosipater
Editor:
    Kühnert, Friedmar
Year Published:
    1964
Language:
    Latin
"""

    rows = parse_perseus_catalog_results(
        markdown,
        collection_id="perseus",
        subject="Latin language--Grammar--Early works to 1500",
        source_url=(
            "https://catalog.perseus.org/?f%5Bsubjects%5D%5B%5D="
            "Latin+language--Grammar--Early+works+to+1500"
        ),
    )

    assert [(row.subject_id, row.key, row.value) for row in rows] == [
        (
            "stoa0085b.stoa001",
            "perseus_subject",
            "Latin language--Grammar--Early works to 1500",
        ),
        (
            "stoa0085b.stoa001",
            "perseus_edition_urn",
            "urn:cts:latinLit:stoa0085b.stoa001.opp-lat2",
        ),
        ("stoa0085b.stoa001", "perseus_author", "Charisius, Flavius Sosipater"),
        ("stoa0085b.stoa001", "perseus_editor", "Kühnert, Friedmar"),
        ("stoa0085b.stoa001", "perseus_year_published", "1964"),
        ("stoa0085b.stoa001", "perseus_language", "Latin"),
        (
            "stoa0085b.stoa001",
            "perseus_catalog_url",
            "https://catalog.perseus.org/?f%5Bsubjects%5D%5B%5D="
            "Latin+language--Grammar--Early+works+to+1500",
        ),
    ]


def test_parse_perseus_catalog_results_reads_compact_firecrawl_fields() -> None:
    markdown = """
##### 1\\. [Grammatica](https://catalog.perseus.org/catalog/urn:cts:latinLit:phi0419.phi001.opp-lat1)

URN:urn:cts:latinLit:phi0419.phi001.opp-lat1Author:Orbilius PupillusEditor:Funaioli, Gino
Year Published:1907Language:Latin
"""

    rows = parse_perseus_catalog_results(
        markdown,
        collection_id="perseus",
        subject="Latin language--Grammar--Early works to 1500",
        source_url="https://catalog.perseus.org/example",
    )

    metadata_by_key = {row.key: row.value for row in rows}
    assert metadata_by_key["perseus_edition_urn"] == "urn:cts:latinLit:phi0419.phi001.opp-lat1"
    assert metadata_by_key["perseus_author"] == "Orbilius Pupillus"
    assert metadata_by_key["perseus_editor"] == "Funaioli, Gino"
    assert metadata_by_key["perseus_year_published"] == "1907"
    assert metadata_by_key["perseus_language"] == "Latin"


def test_parse_perseus_subject_facets_reads_subject_urls_and_counts() -> None:
    grammar_url = (
        "https://catalog.perseus.org/?f%5Bexp_language%5D%5B%5D=lat&"
        "f%5Bsubjects%5D%5B%5D=Latin+language--Grammar--Early+works+to+1500&"
        "per_page=100&sort=auth_name+asc%2C+work_title+asc"
    )
    epic_url = (
        "https://catalog.perseus.org/?f%5Bexp_language%5D%5B%5D=lat&"
        "f%5Bsubjects%5D%5B%5D=Epic+poetry%2C+Latin&per_page=100&"
        "sort=auth_name+asc%2C+work_title+asc"
    )
    markdown = f"""
### Subjects

- [Latin language--Grammar--Early works to 1500]({grammar_url}) 73
- [Epic poetry, Latin]({epic_url}) 148
"""

    rows = parse_perseus_subject_facets(markdown, language="lat")

    assert rows == [
        {
            "language": "lat",
            "subject": "Latin language--Grammar--Early works to 1500",
            "url": grammar_url,
            "count": 73,
        },
        {
            "language": "lat",
            "subject": "Epic poetry, Latin",
            "url": epic_url,
            "count": 148,
        },
    ]


def test_parse_perseus_catalog_results_can_use_local_capture_source_path() -> None:
    markdown = """
##### 1\\. [Aeneid](https://catalog.perseus.org/catalog/urn:cts:latinLit:phi0690.phi003.opp-lat2)

URN:urn:cts:latinLit:phi0690.phi003.opp-lat2Author:VirgilEditor:Knapp, Charles
Year Published:1923Language:Latin
"""

    rows = parse_perseus_catalog_results(
        markdown,
        collection_id="perseus",
        subject="Epic poetry, Latin",
        source_url="https://catalog.perseus.org/latin-epic",
        source_path=Path(".firecrawl/perseus-latin-epic-poetry.md"),
    )

    assert {row.source_path for row in rows} == {Path(".firecrawl/perseus-latin-epic-poetry.md")}
    assert {row.value for row in rows if row.key == "perseus_catalog_url"} == {
        "https://catalog.perseus.org/latin-epic"
    }


def test_sync_dcs_corpus_metadata_matches_catalog_works_by_title() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = root / "catalog.duckdb"
        book_path = root / "book.duckdb"
        source_path = root / "Abhidharmakośa.conllu"
        source_path.write_text("", encoding="utf-8")
        create_catalog_db(catalog_path)
        register_book(
            catalog_path,
            ReaderWork(
                work_id="langnet:reader:sanskrit_dcs:dcs_378",
                collection_id="sanskrit_dcs",
                language="san",
                title="Abhidharmakośa",
                author="Unknown",
                source_id="dcs_378",
            ),
            ReaderEdition(
                edition_id="edition",
                work_id="langnet:reader:sanskrit_dcs:dcs_378",
                label="DCS edition",
                language="san",
                source_path=source_path,
            ),
            ReaderBookArtifact(
                artifact_id="artifact",
                work_id="langnet:reader:sanskrit_dcs:dcs_378",
                edition_id="edition",
                artifact_path=book_path,
                source_path=source_path,
                adapter="sanskrit_dcs_conllu",
                source_hash="hash",
            ),
        )
        corpus_table = """
Text\tAuthor\tTime slot\tSubject\tCompleted\tShow\tBib.\tDict.\tFreq.
Abhidharmakośa\tVasubandhu\tclassical\tBuddhist\t\tS\tB\tD\tF
"""

        summary = sync_dcs_corpus_metadata(
            catalog_path,
            corpus_table,
            source_path=Path("dcs-corpus.tsv"),
        )
        metadata = list_source_metadata(
            catalog_path,
            collection_id="sanskrit_dcs",
            subject_kind="work",
            subject_id="dcs_378",
        )

    assert summary == {"matched_count": 1, "metadata_count": 9, "unmatched_texts": []}
    metadata_by_key = {row["key"]: row["value"] for row in metadata}
    assert metadata_by_key["dcs_author"] == "Vasubandhu"
    assert metadata_by_key["dcs_time_slot"] == "classical"
    assert metadata_by_key["dcs_subject"] == "Buddhist"
    assert metadata_by_key["dcs_scope_hint"] == "Buddhist Scripture"
