from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import duckdb
from click.testing import CliRunner

from langnet.cli import main
from langnet.reader.builder import (
    ReaderBuildConfig,
    ReaderBuilder,
    _aliases_for_registrations,
    _dedupe_book_registrations_for_catalog,
    _ensure_unique_canonical_text_ids,
    _registrations_for_work_ids,
)
from langnet.reader.metadata_overlay import load_metadata_overlays
from langnet.reader.models import ReaderAlias, ReaderBookArtifact, ReaderEdition, ReaderWork
from langnet.reader.storage import ReaderBookRegistration, lookup_segment_by_address, register_book

FIXTURES = Path("tests/fixtures/reader")


def _copy_fixture(name: str, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / name, target_dir / name)


def _reader_registration(
    *,
    work_id: str,
    source_id: str,
    cts_work_urn: str | None = None,
    canonical_text_id: str | None = None,
    language: str = "grc",
) -> ReaderBookRegistration:
    edition = ReaderEdition(
        edition_id=f"{work_id}:edition",
        work_id=work_id,
        label="Fixture edition",
        language=language,
        source_path=Path(f"/tmp/{source_id}.xml"),
    )
    return ReaderBookRegistration(
        work=ReaderWork(
            work_id=work_id,
            collection_id="fixture",
            language=language,
            title="Fragmenta",
            author="Anonymous",
            author_id=None,
            source_id=source_id,
            cts_work_urn=cts_work_urn,
            canonical_text_id=canonical_text_id,
        ),
        edition=edition,
        artifact=ReaderBookArtifact(
            artifact_id=f"{work_id}:artifact",
            work_id=work_id,
            edition_id=edition.edition_id,
            artifact_path=Path(f"/tmp/{source_id}.duckdb"),
            source_path=edition.source_path,
            adapter="fixture",
            source_hash="hash",
            segment_count=1,
            token_count=1,
        ),
    )


def test_generated_ctsv2_ids_are_disambiguated_when_title_and_incipit_collide() -> None:
    first = _reader_registration(
        work_id="urn:cts:greekLit:tlg0001.tlg001",
        source_id="tlg0001.tlg001",
        canonical_text_id="urn:ctsv2:grc:fragmenta-agroikos",
    )
    second = _reader_registration(
        work_id="urn:cts:greekLit:tlg0002.tlg001",
        source_id="tlg0002.tlg001",
        canonical_text_id="urn:ctsv2:grc:fragmenta-agroikos",
    )

    registrations = _ensure_unique_canonical_text_ids([first, second])
    canonical_ids = [registration.work.canonical_text_id for registration in registrations]

    assert canonical_ids == [
        "urn:ctsv2:grc:fragmenta-agroikos-tlg0001-tlg001",
        "urn:ctsv2:grc:fragmenta-agroikos-tlg0002-tlg001",
    ]


def test_generated_aliases_skip_ambiguous_source_identifiers() -> None:
    first = _reader_registration(
        work_id="work-a",
        source_id="shared.source",
        cts_work_urn="urn:cts:greekLit:tlg0001.tlg001",
        canonical_text_id="urn:ctsv2:grc:first",
    )
    second = _reader_registration(
        work_id="work-b",
        source_id="shared.source",
        cts_work_urn="urn:cts:greekLit:tlg0001.tlg001",
        canonical_text_id="urn:ctsv2:grc:second",
    )

    aliases = _aliases_for_registrations([], [first, second])
    aliases_by_kind = {(alias.kind, alias.alias, alias.target) for alias in aliases}

    assert ("canonical_text_id", "urn:ctsv2:grc:first", "urn:ctsv2:grc:first") in aliases_by_kind
    assert (
        "canonical_text_id",
        "urn:ctsv2:grc:second",
        "urn:ctsv2:grc:second",
    ) in aliases_by_kind
    assert not any(alias.alias == "shared.source" for alias in aliases)
    assert not any(alias.alias == "urn:cts:greekLit:tlg0001.tlg001" for alias in aliases)


def test_generated_aliases_use_only_surviving_work_registrations() -> None:
    surviving = _reader_registration(
        work_id="surviving-work",
        source_id="surviving",
        canonical_text_id="urn:ctsv2:grc:surviving",
    )
    suppressed = _reader_registration(
        work_id="suppressed-work",
        source_id="suppressed",
        canonical_text_id="urn:ctsv2:grc:suppressed",
    )

    registrations = _registrations_for_work_ids([surviving, suppressed], {"surviving-work"})
    aliases = _aliases_for_registrations(
        [
            ReaderAlias(
                alias="Suppressed",
                language="grc",
                kind="manual",
                target="suppressed-work",
                display="Suppressed",
                source_file="fixture",
            )
        ],
        registrations,
    )

    assert registrations == [surviving]
    assert all(alias.target != "suppressed-work" for alias in aliases)


def test_catalog_dedupe_removes_overwritten_work_registrations_before_aliases() -> None:
    overwritten = _reader_registration(
        work_id="urn:cts:latinLit:phi0119.phi001",
        source_id="phi0119.phi001",
        canonical_text_id="urn:ctsv2:eng:amphitryon-translation",
        language="eng",
    )
    final = _reader_registration(
        work_id="urn:cts:latinLit:phi0119.phi001",
        source_id="phi0119.phi001",
        canonical_text_id="urn:ctsv2:lat:amphitruo-vt-vos-in",
        language="lat",
    )

    registrations = _dedupe_book_registrations_for_catalog([overwritten, final])
    aliases = _aliases_for_registrations([], registrations)

    assert registrations == [final]
    assert all(alias.language == "lat" for alias in aliases)
    assert all(alias.target == "urn:ctsv2:lat:amphitruo-vt-vos-in" for alias in aliases)


def test_reader_builder_writes_catalog_books_and_aliases() -> None:  # noqa: PLR0915
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        perseus_dir = root / "perseus"
        digiliblt_dir = root / "digiliblt"
        phi_dir = root / "phi"
        tlg_dir = root / "tlg"
        sanskrit_dir = root / "sanskrit"
        _copy_fixture("perseus_odyssey.xml", perseus_dir)
        _copy_fixture("digiliblt_sample.xml", digiliblt_dir)
        _copy_fixture("phi_legacy.txt", phi_dir)
        _copy_fixture("phi_legacy.txt", tlg_dir)
        _copy_fixture("sanskrit_raghuvamsa.json", sanskrit_dir)
        _copy_fixture("sanskrit_plain.txt", sanskrit_dir)
        _copy_fixture("dcs_sample.conllu", sanskrit_dir / "dcs")
        _copy_fixture("dcs_sample.conllu", sanskrit_dir / "dcs" / "parsed")
        (sanskrit_dir / "dcs" / "parsed" / "dcs_sample.conllu").rename(
            sanskrit_dir / "dcs" / "parsed" / "dcs_sample.conllu_parsed"
        )
        (perseus_dir / "__cts__.xml").write_text(
            "<TextGroup><groupname>Metadata only</groupname></TextGroup>",
            encoding="utf-8",
        )
        (phi_dir / "phi_legacy.idt").write_bytes(
            _idt_author_record("0001", "PHI Test Author")
            + _idt_work_record("001", "PHI Test Work", 0)
            + b"\x00"
        )
        (tlg_dir / "phi_legacy.idt").write_bytes(
            _idt_author_record("0001", "TLG Test Author")
            + _idt_work_record("001", "TLG Test Work", 0)
            + b"\x00"
        )
        (phi_dir / "authtab.dir").write_bytes(b"*LAT\x83l\xffLAT0001 PHI Test Author\x83l\xff")
        (tlg_dir / "authtab.dir").write_bytes(b"*TLG\x83g\xffTLG0001 TLG Test Author\x83g\xff")
        (tlg_dir / "cd.authors.php").write_text(
            "<html><body><h1>Authors included in TLG disks D and E</h1>"
            "<ul><li>TLG Test Author Hist.</li></ul></body></html>",
            encoding="utf-8",
        )
        (tlg_dir / "tlgwlist.inx").write_bytes(b"index-support")
        (tlg_dir / "authwkcd.bin").write_bytes(b"binary-support")

        output_root = root / "build" / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                perseus_dir=perseus_dir,
                digiliblt_dir=digiliblt_dir,
                phi_latin_dir=phi_dir,
                tlg_e_dir=tlg_dir,
                sanskrit_dir=sanskrit_dir,
                alias_dir=Path("data/curated/reader_aliases"),
                output_root=output_root,
            )
        ).build()

        catalog_path = output_root / "catalog.duckdb"
        assert result.output_path == catalog_path
        assert catalog_path.exists()
        assert list((output_root / "books").rglob("*.duckdb"))

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            artifacts = {row[0] for row in conn.execute("SELECT adapter FROM artifacts").fetchall()}
            greek_authors = conn.execute(
                "SELECT author FROM works WHERE language = 'grc' ORDER BY author"
            ).fetchall()
            alias_rows = conn.execute(
                "SELECT alias, target FROM aliases WHERE alias = 'Od.'"
            ).fetchall()
            odyssey_canonical = conn.execute(
                """
                SELECT canonical_text_id
                FROM works
                WHERE work_id = 'urn:cts:greekLit:tlg0012.tlg002'
                """
            ).fetchone()
            source_rows = conn.execute(
                """
                SELECT file_role, file_status, source_path
                FROM source_files
                ORDER BY file_role, source_path
                """
            ).fetchall()
            metadata_rows = conn.execute(
                """
                SELECT collection_id, subject_kind, subject_id, key, value
                FROM source_metadata
                ORDER BY collection_id, subject_kind, subject_id, key, value
                """
            ).fetchall()
        odyssey_lookup = lookup_segment_by_address(
            catalog_path,
            "urn:cts:greekLit:tlg0012.tlg002:3.74",
        )

        assert {
            "perseus_tei",
            "digiliblt_tei",
            "phi_idt_legacy",
            "tlg_idt_legacy",
            "sanskrit_json",
            "sanskrit_plain",
            "sanskrit_dcs_conllu",
        } <= artifacts
        assert ("Homer",) in greek_authors
        assert alias_rows == [("Od.", "urn:cts:greekLit:tlg0012.tlg002")]
        assert odyssey_canonical is not None
        assert str(odyssey_canonical[0]).startswith("urn:ctsv2:grc:odyssey-")
        assert ("diogenes_authtab", "metadata", str(phi_dir / "authtab.dir")) in source_rows
        assert ("diogenes_idt", "metadata", str(phi_dir / "phi_legacy.idt")) in source_rows
        assert ("diogenes_text", "text", str(phi_dir / "phi_legacy.txt")) in source_rows
        assert (
            "digiliblt_tei",
            "text",
            str(digiliblt_dir / "digiliblt_sample.xml"),
        ) in source_rows
        assert ("diogenes_word_index", "support", str(tlg_dir / "tlgwlist.inx")) in source_rows
        assert ("diogenes_binary_index", "support", str(tlg_dir / "authwkcd.bin")) in source_rows
        assert ("html_author_index", "metadata", str(tlg_dir / "cd.authors.php")) in source_rows
        assert (
            "digiliblt",
            "work",
            "digiliblt_sample",
            "author",
            "Siculus Flaccus",
        ) in metadata_rows
        assert (
            "digiliblt",
            "work",
            "digiliblt_sample",
            "edition",
            "Fixture",
        ) in metadata_rows
        assert (
            "digiliblt",
            "work",
            "digiliblt_sample",
            "language",
            "lat",
        ) in metadata_rows
        assert (
            "digiliblt",
            "work",
            "digiliblt_sample",
            "source_id",
            "digiliblt.siculus_flaccus.controversiae",
        ) in metadata_rows
        assert (
            "digiliblt",
            "work",
            "digiliblt_sample",
            "title",
            "De controuersiis agrorum",
        ) in metadata_rows
        assert (
            "phi",
            "author",
            "phi_legacy",
            "idt_author_name",
            "PHI Test Author",
        ) in metadata_rows
        assert (
            "phi",
            "work",
            "phi_legacy.001",
            "idt_start_block",
            "0",
        ) in metadata_rows
        assert (
            "phi",
            "author",
            "lat0001",
            "authtab_author_name",
            "PHI Test Author",
        ) in metadata_rows
        assert (
            "tlg",
            "collection",
            "cd.authors.php",
            "cd_index_author",
            "TLG Test Author Hist.",
        ) in metadata_rows
    assert odyssey_lookup


def test_reader_builder_imports_first1k_greek_with_ctsv2_aliases() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        first1k_dir = root / "First1KGreek"
        first1k_data = first1k_dir / "data" / "tlg9010" / "tlg001"
        _copy_fixture("first1k_suda.xml", first1k_data)
        alternate = (FIXTURES / "first1k_suda.xml").read_text(encoding="utf-8")
        (first1k_data / "first1k_suda_grc2.xml").write_text(
            alternate.replace("Suidae lexicon", "Fragmenta lexici")
            .replace(".1st1K-grc1", ".1st1K-grc2")
            .replace("ἄλφα λεξικὸν παράδειγμα", "βῆτα λεξικὸν παράδειγμα"),
            encoding="utf-8",
        )

        output_root = root / "build" / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                first1k_greek_dir=first1k_dir,
                output_root=output_root,
            )
        ).build()

        catalog_path = output_root / "catalog.duckdb"
        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            work_row = conn.execute(
                """
                SELECT collection_id, language, title, cts_work_urn, canonical_text_id
                FROM works
                WHERE work_id = 'urn:cts:greekLit:tlg9010.tlg001'
                """
            ).fetchone()
            source_file_row = conn.execute(
                """
                SELECT collection_id, file_role, COUNT(*)
                FROM source_files
                WHERE collection_id = 'first1kgreek'
                GROUP BY collection_id, file_role
                LIMIT 1
                """
            ).fetchone()
            alias_row = conn.execute(
                """
                SELECT target
                FROM aliases
                WHERE alias = 'urn:cts:greekLit:tlg9010.tlg001'
                LIMIT 1
                """
            ).fetchone()
            witness_row = conn.execute(
                """
                SELECT collection_id, witness_id, source_urn
                FROM source_witnesses
                WHERE work_id = 'urn:cts:greekLit:tlg9010.tlg001'
                LIMIT 1
                """
            ).fetchone()

    assert result.message is None
    assert work_row is not None
    assert work_row[0] == "first1kgreek"
    assert work_row[1] == "grc"
    assert work_row[2] == "Suidae lexicon"
    assert work_row[3] == "urn:cts:greekLit:tlg9010.tlg001"
    assert str(work_row[4]).startswith("urn:ctsv2:grc:suidae-lexicon-")
    assert source_file_row == ("first1kgreek", "first1kgreek_tei", 1)
    assert alias_row is not None
    assert str(alias_row[0]).startswith("urn:ctsv2:grc:suidae-lexicon-")
    assert witness_row == (
        "first1kgreek",
        "urn:cts:greekLit:tlg9010.tlg001",
        "urn:cts:greekLit:tlg9010.tlg001",
    )


def test_reader_builder_keeps_digiliblt_files_with_duplicate_tei_idno() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        digiliblt_dir = root / "digiliblt"
        _copy_fixture("digiliblt_sample.xml", digiliblt_dir)
        (digiliblt_dir / "digiliblt_sample001.png").write_bytes(b"not-reader-data")
        shutil.copyfile(
            digiliblt_dir / "digiliblt_sample.xml",
            digiliblt_dir / "digiliblt_duplicate_idno.xml",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                digiliblt_dir=digiliblt_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            works = conn.execute(
                "SELECT source_id FROM works WHERE collection_id = 'digiliblt' ORDER BY source_id"
            ).fetchall()
            idno_rows = conn.execute(
                """
                SELECT subject_id, value
                FROM source_metadata
                WHERE collection_id = 'digiliblt' AND key = 'source_id'
                ORDER BY subject_id
                """
            ).fetchall()
            source_rows = conn.execute(
                """
                SELECT source_id, file_role, file_status
                FROM source_files
                WHERE collection_id = 'digiliblt'
                ORDER BY source_id
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert works == [("digiliblt_duplicate_idno",), ("digiliblt_sample",)]
    assert idno_rows == [
        ("digiliblt_duplicate_idno", "digiliblt.siculus_flaccus.controversiae"),
        ("digiliblt_sample", "digiliblt.siculus_flaccus.controversiae"),
    ]
    assert source_rows == [
        ("digiliblt_duplicate_idno", "digiliblt_tei", "text"),
        ("digiliblt_sample", "digiliblt_tei", "text"),
    ]


def test_reader_builder_registers_dcs_corpus_and_chapter_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        dcs_files_dir = sanskrit_dir / "dcs" / "data" / "conllu" / "files"
        dcs_lookup_dir = sanskrit_dir / "dcs" / "data" / "conllu" / "lookup"
        _copy_fixture("dcs_sample.conllu", dcs_files_dir)
        dcs_lookup_dir.mkdir(parents=True)
        (dcs_lookup_dir / "chapter-info.xml").write_text(
            """
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
""",
            encoding="utf-8",
        )
        (dcs_lookup_dir / "dcs-corpus.tsv").write_text(
            "\n".join(
                [
                    "Text\tAuthor\tTime slot\tSubject\tCompleted\tShow\tBib.\tDict.\tFreq.",
                    "Abhidharmakośa\tVasubandhu\tclassical\tBuddhist\t\tS\tB\tD\tF",
                ]
            ),
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            metadata_rows = conn.execute(
                """
                SELECT key, value
                FROM source_metadata
                WHERE collection_id = 'sanskrit_dcs'
                  AND subject_kind = 'work'
                  AND subject_id = 'dcs_378'
                ORDER BY key, value
                """
            ).fetchall()
            source_rows = conn.execute(
                """
                SELECT file_role, file_status, source_path
                FROM source_files
                WHERE collection_id = 'sanskrit_dcs'
                ORDER BY file_role, source_path
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert ("dcs_author", "Vasubandhu") in metadata_rows
    assert ("dcs_subject", "Buddhist") in metadata_rows
    assert ("dcs_scope_hint", "Buddhist Scripture") in metadata_rows
    assert ("dcs_chapter_name", "AbhidhKo, 1") in metadata_rows
    assert ("dcs_chapter_position", "1") in metadata_rows
    assert (
        "sanskrit_dcs_chapter_info",
        "metadata",
        str(dcs_lookup_dir / "chapter-info.xml"),
    ) in source_rows
    assert (
        "sanskrit_dcs_corpus_table",
        "metadata",
        str(dcs_lookup_dir / "dcs-corpus.tsv"),
    ) in source_rows


def test_reader_builder_marks_blank_digiliblt_authors_as_unattributed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        digiliblt_dir = root / "digiliblt"
        _copy_fixture("digiliblt_sample.xml", digiliblt_dir)
        sample_path = digiliblt_dir / "digiliblt_sample.xml"
        sample_path.write_text(
            sample_path.read_text(encoding="utf-8").replace(
                "<author>Siculus Flaccus</author>",
                "<author></author>",
            ),
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                digiliblt_dir=digiliblt_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            work_author = conn.execute(
                """
                SELECT author
                FROM works
                WHERE collection_id = 'digiliblt'
                """
            ).fetchone()
            metadata_rows = conn.execute(
                """
                SELECT key, value
                FROM source_metadata
                WHERE collection_id = 'digiliblt' AND subject_id = 'digiliblt_sample'
                ORDER BY key, value
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert work_author == ("Unattributed",)
    assert ("author", "Unattributed") in metadata_rows
    assert ("metadata_issue", "source_author_blank") in metadata_rows


def test_reader_builder_records_normalized_digiliblt_source_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        digiliblt_dir = root / "digiliblt"
        _copy_fixture("digiliblt_sample.xml", digiliblt_dir)
        sample_path = digiliblt_dir / "digiliblt_sample.xml"
        sample_path.write_text(
            sample_path.read_text(encoding="utf-8").replace(
                "<author>Siculus Flaccus</author>",
                "<author>Donatus, Aelius</author>",
            ),
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                digiliblt_dir=digiliblt_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            work_author = conn.execute(
                """
                SELECT author
                FROM works
                WHERE collection_id = 'digiliblt'
                """
            ).fetchone()
            metadata_rows = conn.execute(
                """
                SELECT key, value
                FROM source_metadata
                WHERE collection_id = 'digiliblt' AND subject_id = 'digiliblt_sample'
                ORDER BY key, value
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert work_author == ("Aelius Donatus",)
    assert ("author", "Aelius Donatus") in metadata_rows
    assert ("author_resolution", "normalized_author") in metadata_rows
    assert ("source_author", "Donatus, Aelius") in metadata_rows


def test_reader_builder_canonicalizes_legacy_authors_from_cts_index() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tlg_dir = root / "tlg"
        tlg_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "phi_legacy.txt", tlg_dir / "tlg0012.txt")
        (tlg_dir / "tlg0012.idt").write_bytes(
            _idt_author_record("0012", "&1Homerus& Epic.")
            + _idt_work_record("001", "Ilias", 0)
            + b"\x00"
        )
        cts_path = root / "cts.duckdb"
        with duckdb.connect(str(cts_path)) as conn:
            conn.execute(
                """
                CREATE TABLE author_index (
                    author_id TEXT,
                    author_name TEXT,
                    language TEXT,
                    namespace TEXT,
                    author_urn TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO author_index
                VALUES ('tlg0012', 'Homer', 'grc', 'greekLit', 'urn:cts:greekLit:tlg0012')
                """
            )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                tlg_e_dir=tlg_dir,
                output_root=output_root,
                cts_index_path=cts_path,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT author, author_id, cts_work_urn
                FROM works
                WHERE collection_id = 'tlg'
                """
            ).fetchall()
        segment = lookup_segment_by_address(
            output_root / "catalog.duckdb",
            "urn:cts:greekLit:tlg0012.tlg001:1",
        )

    assert result.status.value == "success", result.message
    assert works == [("Homer", "urn:cts:greekLit:tlg0012", "urn:cts:greekLit:tlg0012.tlg001")]
    assert segment is not None


def test_reader_builder_ignores_malformed_cts_authority_for_legacy_idt() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tlg_dir = root / "tlg"
        tlg_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "phi_legacy.txt", tlg_dir / "tlg0734.txt")
        (tlg_dir / "tlg0734.idt").write_bytes(
            _idt_author_record("0734", "Lucas Apostolus Med.")
            + _idt_work_record("001", "*SKEUASÍA A(LATÍOU", 0)
            + b"\x00"
        )
        cts_path = root / "cts.duckdb"
        with duckdb.connect(str(cts_path)) as conn:
            conn.execute(
                """
                CREATE TABLE author_index (
                    author_id TEXT,
                    author_name TEXT,
                    language TEXT,
                    namespace TEXT,
                    author_urn TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO author_index
                VALUES ('tlg0734', '[2', 'grc', 'greekLit', '')
                """
            )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                tlg_e_dir=tlg_dir,
                output_root=output_root,
                cts_index_path=cts_path,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            row = conn.execute("SELECT author FROM works").fetchone()
            assert row is not None
            author = row[0]

    assert result.status.value == "success", result.message
    assert author == "Lucas Apostolus Med."


def test_reader_builder_excludes_tlg_canon_documents_from_reader_works() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tlg_dir = root / "tlg"
        tlg_dir.mkdir(parents=True)
        (tlg_dir / "doccan1.txt").write_bytes(b"0001\nAPOLLONIUS RHODIUS Epic.\n")
        (tlg_dir / "doccan1.idt").write_bytes(
            _idt_author_record("9999", "bibliography format TLG Canon")
            + _idt_work_record("001", "Canon of Greek Authors and Works", 0)
            + b"\x00"
        )
        shutil.copyfile(FIXTURES / "phi_legacy.txt", tlg_dir / "tlg0012.txt")
        (tlg_dir / "tlg0012.idt").write_bytes(
            _idt_author_record("0012", "Homer") + _idt_work_record("001", "Ilias", 0) + b"\x00"
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                tlg_e_dir=tlg_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT work_id, title
                FROM works
                ORDER BY work_id
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert works == [("langnet:reader:tlg:tlg0012.001", "Ilias")]


def test_reader_builder_cleans_legacy_markup_from_cts_authority() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tlg_dir = root / "tlg"
        tlg_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "phi_legacy.txt", tlg_dir / "tlg1309.txt")
        (tlg_dir / "tlg1309.idt").write_bytes(
            _idt_author_record("1309", "Dialexeis")
            + _idt_work_record("001", "Fragmenta", 0)
            + b"\x00"
        )
        cts_path = root / "cts.duckdb"
        with duckdb.connect(str(cts_path)) as conn:
            conn.execute(
                """
                CREATE TABLE author_index (
                    author_id TEXT,
                    author_name TEXT,
                    language TEXT,
                    namespace TEXT,
                    author_urn TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO author_index
                VALUES ('tlg1309', 'Dialexeis ($1*DISSOI\\ LO/GOI)', 'grc', 'greekLit', '')
                """
            )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                tlg_e_dir=tlg_dir,
                output_root=output_root,
                cts_index_path=cts_path,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            row = conn.execute(
                """
                SELECT author
                FROM works
                WHERE collection_id = 'tlg'
                """
            ).fetchone()
            assert row is not None
            author = row[0]

    assert result.status.value == "success", result.message
    assert author == "Dialexeis (*DISSOÌ LÓGOI)"


def test_databuild_reader_uses_builder_options() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        perseus_dir = root / "perseus"
        _copy_fixture("perseus_odyssey.xml", perseus_dir)
        output_root = root / "reader"

        result = CliRunner().invoke(
            main,
            [
                "databuild",
                "reader",
                "--perseus-dir",
                str(perseus_dir),
                "--alias-dir",
                "data/curated/reader_aliases",
                "--output-root",
                str(output_root),
                "--wipe",
            ],
        )

        assert result.exit_code == 0, result.output
        assert (output_root / "catalog.duckdb").exists()
        assert "artifact_count: 1" in result.output


def test_databuild_reader_can_print_progress() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        perseus_dir = root / "perseus"
        _copy_fixture("perseus_odyssey.xml", perseus_dir)
        output_root = root / "reader"

        result = CliRunner().invoke(
            main,
            [
                "databuild",
                "reader",
                "--perseus-dir",
                str(perseus_dir),
                "--output-root",
                str(output_root),
                "--progress-every",
                "1",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "progress: parsed_sources=1 artifact_count=1" in result.output


def test_reader_builder_applies_limit_before_parsing_later_sources() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        perseus_dir = root / "perseus"
        _copy_fixture("perseus_odyssey.xml", perseus_dir)
        (perseus_dir / "zzz_later_invalid.xml").write_text("<TEI />", encoding="utf-8")

        result = ReaderBuilder(
            ReaderBuildConfig(
                perseus_dir=perseus_dir,
                output_root=root / "reader",
                limit=1,
            )
        ).build()

    assert result.status.value == "success", result.message


def test_reader_builder_reports_optional_progress() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        perseus_dir = root / "perseus"
        _copy_fixture("perseus_odyssey.xml", perseus_dir)
        progress_items = []

        result = ReaderBuilder(
            ReaderBuildConfig(
                perseus_dir=perseus_dir,
                output_root=root / "reader",
                progress_every=1,
                progress_callback=progress_items.append,
            )
        ).build()

    assert result.status.value == "success", result.message
    assert progress_items
    assert progress_items[-1].parsed_sources == 1
    assert progress_items[-1].artifact_count == 1
    assert progress_items[-1].segment_count > 0
    assert progress_items[-1].latest_source.endswith("perseus_odyssey.xml")


def test_reader_builder_records_source_errors_without_blocking_other_sources() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        perseus_dir = root / "perseus"
        sanskrit_dir = root / "sanskrit"
        _copy_fixture("sanskrit_raghuvamsa.json", sanskrit_dir)
        perseus_dir.mkdir(parents=True)
        invalid_path = perseus_dir / "invalid.xml"
        invalid_path.write_text("<TEI />", encoding="utf-8")

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                perseus_dir=perseus_dir,
                sanskrit_dir=sanskrit_dir,
                output_root=output_root,
            )
        ).build()

        catalog_path = output_root / "catalog.duckdb"
        assert result.status.value == "success", result.message
        assert result.stats is not None
        stats = result.stats.unwrap()
        assert stats.artifact_count == 1
        assert stats.source_error_count == 1
        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            adapters = conn.execute("SELECT adapter FROM artifacts").fetchall()
            error_rows = conn.execute(
                """
                SELECT source_path, file_status
                FROM source_files
                WHERE file_status = 'error'
                """
            ).fetchall()
            metadata_rows = conn.execute(
                """
                SELECT key, value
                FROM source_metadata
                WHERE key = 'import_error'
                """
            ).fetchall()

    assert adapters == [("sanskrit_json",)]
    assert error_rows == [(str(invalid_path), "error")]
    assert "missing TEI text div" in metadata_rows[0][1]


def test_reader_builder_skips_zero_segment_sources() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        sanskrit_dir.mkdir(parents=True)
        empty_path = sanskrit_dir / "empty.json"
        empty_path.write_text(
            '{"text":"Empty Source","author":"Nobody","lines":[]}',
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            artifact_count_row = conn.execute("SELECT count(*) FROM artifacts").fetchone()
            work_count_row = conn.execute("SELECT count(*) FROM works").fetchone()
            assert artifact_count_row is not None
            assert work_count_row is not None
            artifact_count = artifact_count_row[0]
            work_count = work_count_row[0]
            source_rows = conn.execute(
                """
                SELECT file_role, file_status, source_path
                FROM source_files
                ORDER BY source_path
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert artifact_count == 0
    assert work_count == 0
    assert source_rows == [("sanskrit_json", "text", str(empty_path))]


def test_reader_builder_groups_sanskrit_split_texts_and_skips_ocr_chunks() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        split_dir = root / "sanskrit" / "texts" / "latyayanashrautasutra" / "split"
        ocr_dir = root / "sanskrit" / "texts" / "latyayanashrautasutra" / "ocr"
        split_dir.mkdir(parents=True)
        ocr_dir.mkdir(parents=True)
        (split_dir / "01-02.txt").write_text("mantravidhiś ca || 1.2.1 ||\n", encoding="utf-8")
        (split_dir / "01-01.txt").write_text("atha vidhyavyapadeśe || 1.1.1 ||\n", encoding="utf-8")
        (ocr_dir / "latyayana_1-10.txt").write_text("raw OCR duplicate\n", encoding="utf-8")

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=root / "sanskrit",
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT work_id, title, author
                FROM works
                ORDER BY work_id
                """
            ).fetchall()
            artifacts = conn.execute(
                """
                SELECT adapter, segment_count
                FROM artifacts
                ORDER BY artifact_id
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert works == [
        (
            "langnet:reader:sanskrit_texts:latyayanashrautasutra_split",
            "Lāṭyāyana Śrautasūtra",
            "Lāṭyāyana",
        )
    ]
    assert artifacts == [("sanskrit_split_plain", 2)]


def test_reader_builder_prefers_gretil_plain_text_over_duplicate_json_stem() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        gretil_dir = root / "sanskrit" / "GRETIL"
        corpus_dir = gretil_dir / "corpus"
        corpus_dir.mkdir(parents=True)
        corpus_json = corpus_dir / "sa_nAgArjuna-dharmasaMgraha.json"
        corpus_json.write_text(
            json.dumps(
                {
                    "text": "Dharmasaṃgraha",
                    "author": "Nāgārjuna",
                    "lines": [[{"w": "dharma"}, {"w": "saṃgraha"}]],
                }
            ),
            encoding="utf-8",
        )
        ashta_json = corpus_dir / "sa_aSTasAhasrikA-prajJApAramitA.json"
        ashta_json.write_text(
            json.dumps(
                {
                    "text": "Aṣṭasāhasrikā Prajñāpāramitā",
                    "lines": [[{"w": "evaṃ"}, {"w": "mayā"}, {"w": "śrutam"}]],
                }
            ),
            encoding="utf-8",
        )
        plain_text = gretil_dir / "sa_nAgArjuna-dharmasaMgraha.txt"
        plain_text.write_text(
            "\n".join(
                [
                    "#Author:Nāgārjuna",
                    "#Text:Dharmasaṃgraha",
                    "#Edition:P.L. Vaidya: Dharmasangraha. Darbhanga 1961.",
                    "",
                    "dharmasaṃgrahaḥ /",
                    "// namo ratnatrayāya //",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        ashta_text = gretil_dir / "sa_aSTasAhasrikA-prajJApAramitA.txt"
        ashta_text.write_text(
            "\n".join(
                [
                    "#Text:Aṣṭasāhasrikā Prajñāpāramitā",
                    "#Edition:P.L. Vaidya, Darbhanga: The Mithila Institute, 1960.",
                    '#Notes:"Missing portion" on page Vaidya 229 rediscovered.',
                    "",
                    "om namo bhagavatyai āryaprajñāpāramitāyai /",
                    "evaṃ mayā śrutam /",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=root / "sanskrit",
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT work_id, collection_id, source_id, title, author
                FROM works
                ORDER BY work_id
                """
            ).fetchall()
            artifacts = conn.execute(
                """
                SELECT adapter, segment_count
                FROM artifacts
                ORDER BY artifact_id
                """
            ).fetchall()
            metadata_rows = conn.execute(
                """
                SELECT subject_kind, subject_id, key, value
                FROM source_metadata
                WHERE collection_id = 'sanskrit_texts'
                ORDER BY key, value
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert works == [
        (
            "langnet:reader:sanskrit_texts:GRETIL_sa_aSTasAhasrikA-prajJApAramitA",
            "sanskrit_texts",
            "GRETIL_sa_aSTasAhasrikA-prajJApAramitA",
            "Aṣṭasāhasrikā Prajñāpāramitā",
            "Unknown",
        ),
        (
            "langnet:reader:sanskrit_texts:GRETIL_sa_nAgArjuna-dharmasaMgraha",
            "sanskrit_texts",
            "GRETIL_sa_nAgArjuna-dharmasaMgraha",
            "Dharmasaṃgraha",
            "Nāgārjuna",
        ),
    ]
    assert artifacts == [("sanskrit_plain", 2), ("sanskrit_plain", 2)]
    assert set(metadata_rows) == {
        (
            "work",
            "GRETIL_sa_aSTasAhasrikA-prajJApAramitA",
            "gretil_edition",
            "P.L. Vaidya, Darbhanga: The Mithila Institute, 1960.",
        ),
        (
            "work",
            "GRETIL_sa_aSTasAhasrikA-prajJApAramitA",
            "gretil_notes",
            '"Missing portion" on page Vaidya 229 rediscovered.',
        ),
        (
            "work",
            "GRETIL_sa_aSTasAhasrikA-prajJApAramitA",
            "gretil_text",
            "Aṣṭasāhasrikā Prajñāpāramitā",
        ),
        (
            "work",
            "GRETIL_sa_nAgArjuna-dharmasaMgraha",
            "gretil_author",
            "Nāgārjuna",
        ),
        (
            "work",
            "GRETIL_sa_nAgArjuna-dharmasaMgraha",
            "gretil_edition",
            "P.L. Vaidya: Dharmasangraha. Darbhanga 1961.",
        ),
        (
            "work",
            "GRETIL_sa_nAgArjuna-dharmasaMgraha",
            "gretil_text",
            "Dharmasaṃgraha",
        ),
    }


def test_reader_builder_source_slice_rebuild_replaces_stale_gretil_json_work() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        gretil_dir = sanskrit_dir / "GRETIL"
        corpus_dir = gretil_dir / "corpus"
        corpus_dir.mkdir(parents=True)
        corpus_json = corpus_dir / "sa_aSTasAhasrikA-prajJApAramitA.json"
        corpus_json.write_text(
            json.dumps(
                {
                    "text": "Aṣṭasāhasrikā Prajñāpāramitā",
                    "lines": [[{"w": "evaṃ"}, {"w": "mayā"}, {"w": "śrutam"}]],
                }
            ),
            encoding="utf-8",
        )
        output_root = root / "reader"
        initial_result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                output_root=output_root,
            )
        ).build()
        ashta_text = gretil_dir / "sa_aSTasAhasrikA-prajJApAramitA.txt"
        ashta_text.write_text(
            "\n".join(
                [
                    "#Text:Aṣṭasāhasrikā Prajñāpāramitā",
                    "#Edition:P.L. Vaidya, Darbhanga: The Mithila Institute, 1960.",
                    "",
                    "om namo bhagavatyai āryaprajñāpāramitāyai /",
                    "evaṃ mayā śrutam /",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        slice_result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                output_root=output_root,
                wipe_existing=False,
                source_paths=(ashta_text,),
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT collection_id, source_id
                FROM works
                WHERE language = 'san'
                ORDER BY collection_id, source_id
                """
            ).fetchall()
            artifact_path_row = conn.execute(
                """
                SELECT artifact_path
                FROM artifacts
                WHERE work_id =
                  'langnet:reader:sanskrit_texts:GRETIL_sa_aSTasAhasrikA-prajJApAramitA'
                """
            ).fetchone()
            assert artifact_path_row is not None
            artifact_path = artifact_path_row[0]
        with duckdb.connect(str(artifact_path), read_only=True) as conn:
            segments = conn.execute(
                """
                SELECT citation_path, text
                FROM segments
                ORDER BY sort_key
                LIMIT 2
                """
            ).fetchall()

    assert initial_result.status.value == "success", initial_result.message
    assert slice_result.status.value == "success", slice_result.message
    assert works == [("sanskrit_texts", "GRETIL_sa_aSTasAhasrikA-prajJApAramitA")]
    assert segments == [
        ("1", "om namo bhagavatyai āryaprajñāpāramitāyai /"),
        ("2", "evaṃ mayā śrutam /"),
    ]


def test_reader_builder_source_slice_cleans_all_existing_gretil_json_twins() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        output_root = root / "reader"
        catalog_path = output_root / "catalog.duckdb"
        sanskrit_dir = root / "sanskrit"
        gretil_dir = sanskrit_dir / "GRETIL"
        gretil_dir.mkdir(parents=True)
        ashta_text = gretil_dir / "sa_aSTasAhasrikA-prajJApAramitA.txt"
        dharma_text = gretil_dir / "sa_nAgArjuna-dharmasaMgraha.txt"
        ashta_text.write_text(
            "\n".join(
                [
                    "#Text:Aṣṭasāhasrikā Prajñāpāramitā",
                    "",
                    "om namo bhagavatyai āryaprajñāpāramitāyai /",
                ]
            ),
            encoding="utf-8",
        )
        dharma_text.write_text(
            "\n".join(
                [
                    "#Author:Nāgārjuna",
                    "#Text:Dharmasaṃgraha",
                    "",
                    "dharmasaṃgrahaḥ /",
                ]
            ),
            encoding="utf-8",
        )
        for collection_id, source_id in (
            ("sanskrit_json", "corpus_sa_aSTasAhasrikA-prajJApAramitA"),
            ("sanskrit_json", "corpus_sa_nAgArjuna-dharmasaMgraha"),
            ("sanskrit_texts", "GRETIL_sa_aSTasAhasrikA-prajJApAramitA"),
            ("sanskrit_texts", "GRETIL_sa_nAgArjuna-dharmasaMgraha"),
        ):
            work_id = f"langnet:reader:{collection_id}:{source_id}"
            source_path = (
                gretil_dir / f"{source_id.removeprefix('GRETIL_')}.txt"
                if collection_id == "sanskrit_texts"
                else gretil_dir / "corpus" / f"{source_id.removeprefix('corpus_')}.json"
            )
            register_book(
                catalog_path,
                ReaderWork(
                    work_id=work_id,
                    collection_id=collection_id,
                    language="san",
                    title=source_id,
                    author="Nāgārjuna",
                    author_id=None,
                    source_id=source_id,
                    cts_work_urn=None,
                ),
                ReaderEdition(
                    edition_id=f"{work_id}:edition",
                    work_id=work_id,
                    label="stale fixture",
                    language="san",
                    source_path=source_path,
                ),
                ReaderBookArtifact(
                    artifact_id=f"{work_id}:artifact",
                    work_id=work_id,
                    edition_id=f"{work_id}:edition",
                    artifact_path=output_root / "books" / f"{source_id}.duckdb",
                    source_path=source_path,
                    adapter="fixture",
                    source_hash="stale",
                    segment_count=1,
                    token_count=1,
                ),
            )

        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                output_root=output_root,
                wipe_existing=False,
                source_paths=(ashta_text,),
            )
        ).build()

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT collection_id, source_id
                FROM works
                WHERE language = 'san'
                ORDER BY collection_id, source_id
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert works == [
        ("sanskrit_texts", "GRETIL_sa_aSTasAhasrikA-prajJApAramitA"),
        ("sanskrit_texts", "GRETIL_sa_nAgArjuna-dharmasaMgraha"),
    ]


def test_reader_builder_removes_legacy_work_when_same_language_perseus_work_exists() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        output_root = root / "reader"
        catalog_path = output_root / "catalog.duckdb"
        legacy_source = root / "tlg0086.txt"
        perseus_source = root / "tlg0086.tlg003.perseus-grc1.xml"
        translation_source = root / "phi0550.phi001.perseus-eng1.xml"
        legacy_source.write_text("legacy", encoding="utf-8")
        perseus_source.write_text("perseus", encoding="utf-8")
        translation_source.write_text("translation", encoding="utf-8")

        for work, edition_source in (
            (
                ReaderWork(
                    work_id="langnet:reader:tlg:tlg0086.003",
                    collection_id="tlg",
                    language="grc",
                    title="*)AQHNAÍWN POLITEÍA",
                    author="Aristotle of Stagira",
                    author_id="tlg0086",
                    source_id="tlg0086.003",
                    cts_work_urn="urn:cts:greekLit:tlg0086.tlg003",
                ),
                legacy_source,
            ),
            (
                ReaderWork(
                    work_id="langnet:reader:tlg:tlg0086.001",
                    collection_id="tlg",
                    language="grc",
                    title="Analytica priora et posteriora",
                    author="Aristotle of Stagira",
                    author_id="tlg0086",
                    source_id="tlg0086.001",
                    cts_work_urn="urn:cts:greekLit:tlg0086.tlg001",
                ),
                legacy_source,
            ),
            (
                ReaderWork(
                    work_id="urn:cts:greekLit:tlg0086.tlg003",
                    collection_id="perseus",
                    language="grc",
                    title="Ἀθηναίων πολιτεία",
                    author="Aristotle",
                    author_id="urn:cts:greekLit:tlg0086",
                    source_id="tlg0086.tlg003",
                    cts_work_urn="urn:cts:greekLit:tlg0086.tlg003",
                ),
                perseus_source,
            ),
            (
                ReaderWork(
                    work_id="langnet:reader:phi:phi0550.001",
                    collection_id="phi",
                    language="lat",
                    title="De rerum natura",
                    author="Lucretius",
                    author_id="phi0550",
                    source_id="phi0550.001",
                    cts_work_urn="urn:cts:latinLit:phi0550.phi001",
                ),
                legacy_source,
            ),
            (
                ReaderWork(
                    work_id="urn:cts:latinLit:phi0550.phi001",
                    collection_id="perseus",
                    language="eng",
                    title="On the Nature of Things",
                    author="Lucretius",
                    author_id="urn:cts:latinLit:phi0550",
                    source_id="phi0550.phi001",
                    cts_work_urn="urn:cts:latinLit:phi0550.phi001",
                ),
                translation_source,
            ),
        ):
            register_book(
                catalog_path,
                work,
                ReaderEdition(
                    edition_id=f"{work.work_id}:edition",
                    work_id=work.work_id,
                    label="fixture",
                    language=work.language,
                    source_path=edition_source,
                ),
                ReaderBookArtifact(
                    artifact_id=f"{work.work_id}:artifact",
                    work_id=work.work_id,
                    edition_id=f"{work.work_id}:edition",
                    artifact_path=output_root / "books" / f"{work.source_id}.duckdb",
                    source_path=edition_source,
                    adapter="fixture",
                    source_hash="fixture",
                    segment_count=1,
                    token_count=1,
                ),
            )

        result = ReaderBuilder(
            ReaderBuildConfig(output_root=output_root, wipe_existing=False)
        ).build()

        with duckdb.connect(str(catalog_path), read_only=True) as conn:
            works = conn.execute(
                """
                SELECT work_id, collection_id, language, title
                FROM works
                ORDER BY collection_id, language, work_id
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert works == [
        (
            "urn:cts:latinLit:phi0550.phi001",
            "perseus",
            "eng",
            "On the Nature of Things",
        ),
        (
            "urn:cts:greekLit:tlg0086.tlg003",
            "perseus",
            "grc",
            "Ἀθηναίων πολιτεία",
        ),
        (
            "langnet:reader:phi:phi0550.001",
            "phi",
            "lat",
            "De rerum natura",
        ),
        (
            "langnet:reader:tlg:tlg0086.001",
            "tlg",
            "grc",
            "Analytica priora et posteriora",
        ),
    ], works


def test_reader_builder_applies_accepted_metadata_overlay() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        overlay_dir = root / "overlays"
        sanskrit_dir.mkdir()
        overlay_dir.mkdir()
        text_path = sanskrit_dir / "shiva.json"
        text_path.write_text(
            '{"text":"Śivasūtra","lines":[[{"w":"a"},{"w":"i"}]]}',
            encoding="utf-8",
        )
        (overlay_dir / "sanskrit.yaml").write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_shiva"
    field: "author"
    value: "Pāṇini"
    status: "accepted"
    confidence: "medium"
    note: "Accepted only for the grammatical Māheśvara/Śiva Sūtra fixture."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                metadata_overlay_dir=overlay_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            work = conn.execute(
                """
                SELECT author, title
                FROM works
                WHERE collection_id = 'sanskrit_json'
                """
            ).fetchone()
            overlays = conn.execute(
                """
                SELECT field, value, status, confidence, evidence_citation
                FROM metadata_overlays
                ORDER BY field, value
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert work == ("Pāṇini", "Śivasūtra")
    assert overlays == [
        (
            "author",
            "Pāṇini",
            "accepted",
            "medium",
            "https://learnsanskrit.org/panini/shivasutras/",
        )
    ]


def test_reader_builder_applies_accepted_author_id_metadata_overlay() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tlg_dir = root / "tlg"
        overlay_dir = root / "overlays"
        tlg_dir.mkdir(parents=True)
        overlay_dir.mkdir()
        shutil.copyfile(FIXTURES / "phi_legacy.txt", tlg_dir / "tlg0379.txt")
        (tlg_dir / "tlg0379.idt").write_bytes(
            _idt_author_record("0379", "Philoxenus")
            + _idt_work_record("001", "Fragmenta", 0)
            + b"\x00"
        )
        (overlay_dir / "tlg.yaml").write_text(
            """
overlays:
  - collection_id: "tlg"
    match_field: "author_id"
    match_value: "tlg0379"
    field: "author"
    value: "Philoxenus Cytherius"
    status: "accepted"
    confidence: "high"
    note: "Research-backed author-level canonicalization for all works in TLG 0379."
    evidence:
      - source_type: "web_source"
        citation: "https://catalog.perseus.org/catalog/urn:cite:perseus:author.1110"
        label: "Perseus Catalog maps TLG 0379 to Philoxenus Cytherius."
        retrieved_at: "2026-05-14"
""",
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                tlg_e_dir=tlg_dir,
                metadata_overlay_dir=overlay_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            work_author = conn.execute(
                """
                SELECT author
                FROM works
                WHERE collection_id = 'tlg'
                """
            ).fetchone()

    assert result.status.value == "success", result.message
    assert work_author == ("Philoxenus Cytherius",)


def test_curated_vulgate_overlay_maps_civ0004_to_jerome() -> None:
    overlay_path = Path("data/curated/reader_metadata/phi/vulgate_jerome.yaml")

    overlays = load_metadata_overlays(overlay_path.parent)
    vulgate_overlays = [
        overlay
        for overlay in overlays
        if overlay.collection_id == "phi"
        and overlay.match_field == "author_id"
        and overlay.match_value == "civ0004"
    ]
    values_by_field = {overlay.field: overlay.value for overlay in vulgate_overlays}

    assert values_by_field == {
        "author": "Saint Jerome",
        "author_id": "urn:cts:latinLit:stoa0162",
    }


def test_curated_gospel_overlays_map_individual_works_to_traditional_authors() -> None:
    overlay_path = Path("data/curated/reader_metadata/phi/greek_new_testament_gospels.yaml")

    overlays = load_metadata_overlays(overlay_path.parent)
    gospel_overlays = [
        overlay
        for overlay in overlays
        if overlay.collection_id == "phi"
        and overlay.match_field == "source_id"
        and overlay.match_value.startswith("civ0003.")
    ]
    values_by_work = {
        (overlay.match_value, overlay.field): overlay.value for overlay in gospel_overlays
    }

    assert values_by_work == {
        ("civ0003.001", "author"): "Matthew the Evangelist",
        ("civ0003.001", "author_id"): "urn:cts:langnet:author.grc.matthew-the-evangelist",
        ("civ0003.002", "author"): "Mark the Evangelist",
        ("civ0003.002", "author_id"): "urn:cts:langnet:author.grc.mark-the-evangelist",
        ("civ0003.003", "author"): "Luke the Evangelist",
        ("civ0003.003", "author_id"): "urn:cts:langnet:author.grc.luke-the-evangelist",
        ("civ0003.004", "author"): "John the Evangelist",
        ("civ0003.004", "author_id"): "urn:cts:langnet:author.grc.john-the-evangelist",
    }


def test_reader_builder_normalizes_accepted_author_overlay_for_display() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        digiliblt_dir = root / "digiliblt"
        overlay_dir = root / "overlays"
        digiliblt_dir.mkdir()
        overlay_dir.mkdir()
        _copy_fixture("digiliblt_sample.xml", digiliblt_dir)
        sample_path = digiliblt_dir / "digiliblt_sample.xml"
        sample_path.write_text(
            sample_path.read_text(encoding="utf-8").replace(
                "<author>Siculus Flaccus</author>",
                "<author></author>",
            ),
            encoding="utf-8",
        )
        (overlay_dir / "digiliblt.yaml").write_text(
            """
overlays:
  - collection_id: "digiliblt"
    match_field: "source_id"
    match_value: "digiliblt_sample"
    field: "author"
    value: "Anonymus"
    status: "accepted"
    confidence: "high"
    note: "Source authority uses Anonymus, but reader display should canonicalize to Anonymous."
    evidence:
      - source_type: "web_source"
        citation: "https://digiliblt.uniupo.it/teidocs/author/AUT000000"
        label: "digilibLT Anonymus author authority."
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                digiliblt_dir=digiliblt_dir,
                metadata_overlay_dir=overlay_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            work_author = conn.execute(
                """
                SELECT author
                FROM works
                WHERE collection_id = 'digiliblt'
                """
            ).fetchone()
            overlay_value = conn.execute(
                """
                SELECT value
                FROM metadata_overlays
                WHERE collection_id = 'digiliblt'
                """
            ).fetchone()

    assert result.status.value == "success", result.message
    assert work_author == ("Anonymous",)
    assert overlay_value == ("Anonymus",)


def test_reader_builder_registers_candidate_overlay_without_applying_it() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        overlay_dir = root / "overlays"
        sanskrit_dir.mkdir()
        overlay_dir.mkdir()
        (sanskrit_dir / "shiva.json").write_text(
            '{"text":"Śivasūtra","lines":[[{"w":"a"}]]}',
            encoding="utf-8",
        )
        (overlay_dir / "sanskrit.yaml").write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_shiva"
    field: "author"
    value: "Pāṇini"
    status: "candidate"
    confidence: "medium"
    note: "Ambiguous title; source text must be checked before acceptance."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                metadata_overlay_dir=overlay_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            author_row = conn.execute("SELECT author FROM works").fetchone()
            overlay_status_row = conn.execute("SELECT status FROM metadata_overlays").fetchone()
            assert author_row is not None
            assert overlay_status_row is not None
            author = author_row[0]
            overlay_status = overlay_status_row[0]

    assert result.status.value == "success", result.message
    assert author == "Unknown"
    assert overlay_status == "candidate"


def test_reader_builder_registers_attribution_without_applying_display_author() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        attribution_dir = root / "attributions"
        sanskrit_dir.mkdir()
        attribution_dir.mkdir()
        (sanskrit_dir / "ambiguous.json").write_text(
            '{"text":"Ambiguous fixture","lines":[[{"w":"a"}]]}',
            encoding="utf-8",
        )
        (attribution_dir / "sanskrit.yaml").write_text(
            """
attributions:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_ambiguous"
    relation_type: "possible_author"
    agent: "Aristotle"
    status: "accepted"
    confidence: "medium"
    note: "Accepted as a recorded attribution claim, not as display metadata."
    evidence:
      - source_type: "web_source"
        citation: "https://example.org/aristotle"
        label: "Source records Aristotle as a possible author."
        retrieved_at: "2026-05-13"
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_ambiguous"
    relation_type: "possible_author"
    agent: "Avicenna"
    status: "accepted"
    confidence: "medium"
    note: "Accepted as a recorded attribution claim, not as display metadata."
    evidence:
      - source_type: "web_source"
        citation: "https://example.org/avicenna"
        label: "Source records Avicenna as a possible author."
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                metadata_overlay_dir=None,
                metadata_attribution_dir=attribution_dir,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            row = conn.execute("SELECT author FROM works").fetchone()
            assert row is not None
            author = row[0]
            attributions = conn.execute(
                """
                SELECT relation_type, agent, status, confidence, evidence_citation
                FROM metadata_attributions
                ORDER BY agent
                """
            ).fetchall()

    assert result.status.value == "success", result.message
    assert author == "Unknown"
    assert attributions == [
        ("possible_author", "Aristotle", "accepted", "medium", "https://example.org/aristotle"),
        ("possible_author", "Avicenna", "accepted", "medium", "https://example.org/avicenna"),
    ]


def test_reader_builder_normalizes_pseudo_author_variants_at_import() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        sanskrit_dir.mkdir()
        (sanskrit_dir / "pseudo.json").write_text(
            '{"text":"Pseudo fixture","author":"Plato (Ps.)","lines":[[{"w":"a"}]]}',
            encoding="utf-8",
        )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                metadata_overlay_dir=None,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            row = conn.execute("SELECT author FROM works").fetchone()
            assert row is not None
            author = row[0]

    assert result.status.value == "success", result.message
    assert author == "Pseudo-Plato"


def test_reader_builder_enriches_legacy_tlg_pseudo_author_from_html_canon() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tlg_dir = root / "tlg"
        tlg_dir.mkdir()
        shutil.copyfile(FIXTURES / "phi_legacy.txt", tlg_dir / "tlg0530.txt")
        (tlg_dir / "tlg0530.idt").write_bytes(
            _idt_author_record("0530", "Pseudo-")
            + _idt_work_record("001", "De causa affectionum", 0)
            + b"\x00"
        )
        (tlg_dir / "cd.authors.php").write_text(
            "<html><body><ul><li>0530 Pseudo-Galenus Med.</li></ul></body></html>",
            encoding="utf-8",
        )
        cts_index = root / "cts_urn.duckdb"
        with duckdb.connect(str(cts_index)) as conn:
            conn.execute(
                """
                CREATE TABLE author_index (
                    author_id VARCHAR PRIMARY KEY,
                    author_name VARCHAR NOT NULL,
                    language VARCHAR,
                    namespace VARCHAR,
                    author_urn VARCHAR
                )
                """
            )
            conn.execute(
                "INSERT INTO author_index VALUES ('tlg0530', 'Pseudo-', 'grc', 'greekLit', '')"
            )

        output_root = root / "reader"
        result = ReaderBuilder(
            ReaderBuildConfig(
                tlg_e_dir=tlg_dir,
                cts_index_path=cts_index,
                metadata_overlay_dir=None,
                output_root=output_root,
            )
        ).build()

        with duckdb.connect(str(output_root / "catalog.duckdb"), read_only=True) as conn:
            row = conn.execute("SELECT author FROM works").fetchone()
            assert row is not None
            author = row[0]

    assert result.status.value == "success", result.message
    assert author == "Pseudo-Galenus"


def test_reader_cli_lists_metadata_overlays() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        overlay_dir = root / "overlays"
        sanskrit_dir.mkdir()
        overlay_dir.mkdir()
        (sanskrit_dir / "shiva.json").write_text(
            '{"text":"Śivasūtra","lines":[[{"w":"a"}]]}',
            encoding="utf-8",
        )
        (overlay_dir / "sanskrit.yaml").write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_shiva"
    field: "author"
    value: "Pāṇini"
    status: "candidate"
    confidence: "medium"
    note: "Ambiguous title; source text must be checked before acceptance."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )
        output_root = root / "reader"
        ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                metadata_overlay_dir=overlay_dir,
                output_root=output_root,
            )
        ).build()

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(output_root / "catalog.duckdb"),
                "overlays",
                "--status",
                "candidate",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "overlays"
    assert payload["items"][0]["field"] == "author"
    assert payload["items"][0]["value"] == "Pāṇini"
    assert payload["items"][0]["evidence_citation"].startswith("https://learnsanskrit.org/")


def test_reader_cli_lists_metadata_attributions() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sanskrit_dir = root / "sanskrit"
        attribution_dir = root / "attributions"
        sanskrit_dir.mkdir()
        attribution_dir.mkdir()
        (sanskrit_dir / "ambiguous.json").write_text(
            '{"text":"Ambiguous fixture","lines":[[{"w":"a"}]]}',
            encoding="utf-8",
        )
        (attribution_dir / "sanskrit.yaml").write_text(
            """
attributions:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_ambiguous"
    relation_type: "possible_author"
    agent: "Aristotle"
    status: "accepted"
    confidence: "medium"
    note: "Accepted as a recorded attribution claim, not as display metadata."
    evidence:
      - source_type: "web_source"
        citation: "https://example.org/aristotle"
        label: "Source records Aristotle as a possible author."
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )
        output_root = root / "reader"
        ReaderBuilder(
            ReaderBuildConfig(
                sanskrit_dir=sanskrit_dir,
                metadata_overlay_dir=None,
                metadata_attribution_dir=attribution_dir,
                output_root=output_root,
            )
        ).build()

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(output_root / "catalog.duckdb"),
                "attributions",
                "--agent",
                "Aristotle",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["mode"] == "attributions"
    assert payload["items"][0]["relation_type"] == "possible_author"
    assert payload["items"][0]["agent"] == "Aristotle"
    assert payload["items"][0]["evidence_citation"] == "https://example.org/aristotle"


def test_reader_cli_overlay_review_can_promote_candidate_interactively() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        overlay_dir = root / "overlays"
        overlay_dir.mkdir()
        overlay_path = overlay_dir / "sanskrit.yaml"
        overlay_path.write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_shiva"
    field: "author"
    value: "Pāṇini"
    status: "candidate"
    confidence: "medium"
    note: "Ambiguous title; source text must be checked before acceptance."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "overlay-review",
                "--metadata-overlay-dir",
                str(overlay_dir),
                "--reviewer",
                "rule",
                "--apply",
            ],
            input="y\n",
        )
        overlays = load_metadata_overlays(overlay_dir)

    assert result.exit_code == 0, result.output
    assert "Promote to accepted?" in result.output
    assert "applied" in result.output
    assert overlays[0].status == "accepted"
    assert overlays[0].evidence[-1].source_type == "rule_review"


def test_reader_cli_overlay_review_yes_does_not_promote_needs_review() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        overlay_dir = root / "overlays"
        overlay_dir.mkdir()
        (overlay_dir / "sanskrit.yaml").write_text(
            """
overlays:
  - collection_id: "sanskrit_json"
    match_field: "source_id"
    match_value: "sanskrit_shiva"
    field: "author"
    value: "Pāṇini"
    status: "candidate"
    confidence: "medium"
    note: "Ambiguous title; source text must be checked before acceptance."
    evidence:
      - source_type: "web"
        citation: "https://learnsanskrit.org/panini/shivasutras/"
        label: "Learn Sanskrit Online, The Shiva Sutras - Panini"
        retrieved_at: "2026-05-13"
""",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "overlay-review",
                "--metadata-overlay-dir",
                str(overlay_dir),
                "--reviewer",
                "rule",
                "--apply",
                "--yes",
            ],
        )
        overlays = load_metadata_overlays(overlay_dir)

    assert result.exit_code == 0, result.output
    assert "applied=0" in result.output
    assert overlays[0].status == "candidate"


def test_reader_cli_lists_diogenes_source_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        phi_dir = root / "phi"
        _copy_fixture("phi_legacy.txt", phi_dir)
        (phi_dir / "phi_legacy.idt").write_bytes(
            _idt_author_record("0001", "PHI Test Author")
            + _idt_work_record("001", "PHI Test Work", 0)
            + b"\x00"
        )
        (phi_dir / "authtab.dir").write_bytes(b"*LAT\x83l\xffLAT0001 PHI Test Author\x83l\xff")
        output_root = root / "reader"
        ReaderBuilder(ReaderBuildConfig(phi_latin_dir=phi_dir, output_root=output_root)).build()

        source_result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(output_root / "catalog.duckdb"),
                "sources",
                "--collection",
                "phi",
                "--output",
                "json",
            ],
        )
        metadata_result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(output_root / "catalog.duckdb"),
                "metadata",
                "--collection",
                "phi",
                "--output",
                "json",
            ],
        )

    assert source_result.exit_code == 0, source_result.output
    assert metadata_result.exit_code == 0, metadata_result.output
    assert "diogenes_authtab" in source_result.output
    assert "authtab_author_name" in metadata_result.output
    assert "idt_title" in metadata_result.output


def _idt_author_record(author_id: str, name: str) -> bytes:
    return _idt_record(1, 0, author_id, name, start_block=0)


def _idt_work_record(work_id: str, title: str, start_block: int) -> bytes:
    return _idt_record(2, 1, work_id, title, start_block=start_block)


def _idt_record(
    code: int,
    level: int,
    identifier: str,
    value: str,
    *,
    start_block: int,
) -> bytes:
    value_bytes = value.encode("latin-1")
    return (
        bytes([code, 0, 0, (start_block >> 8) & 0xFF, start_block & 0xFF, 0xEF, 0x80 | level])
        + identifier.encode("ascii")
        + b"\xff"
        + bytes([0x10, level, len(value_bytes)])
        + value_bytes
    )
