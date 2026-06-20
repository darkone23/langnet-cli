from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path

from click.testing import CliRunner

from langnet.cli import main
from langnet.reader.catalog_export import export_work_bundle, validate_catalog_export
from langnet.reader.models import (
    ReaderBookArtifact,
    ReaderEdition,
    ReaderSegment,
    ReaderSegmentAddress,
    ReaderSourceFile,
    ReaderSourceMetadata,
    ReaderSourceWitness,
    ReaderWork,
)
from langnet.reader.storage import (
    create_book_db,
    create_catalog_db,
    register_book,
    register_segment_rows,
    register_source_files,
    register_source_metadata,
    register_source_witnesses,
)

FIXTURE_SEGMENT_COUNT = 2


def _write_fixture_catalog(root: Path) -> Path:
    catalog_path = root / "catalog.duckdb"
    book_path = root / "books" / "fixture.duckdb"
    source_path = root / "sources" / "fixture.xml"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("<TEI>arma virumque cano</TEI>\n", encoding="utf-8")
    create_catalog_db(catalog_path)
    create_book_db(book_path)
    work = ReaderWork(
        work_id="urn:langnet:fixture:aeneid",
        collection_id="fixture",
        language="lat",
        title="Aeneid",
        author="Vergil",
        author_id="urn:cts:latinLit:phi0690",
        source_id="phi0690.phi003",
        cts_work_urn="urn:cts:latinLit:phi0690.phi003",
        canonical_text_id="urn:ctsv2:lat:aeneid-arma-virumque-cano",
    )
    edition = ReaderEdition(
        edition_id="urn:cts:latinLit:phi0690.phi003.fixture-lat1",
        work_id=work.work_id,
        label="Fixture Latin edition",
        language="lat",
        source_path=source_path,
        cts_edition_urn="urn:cts:latinLit:phi0690.phi003.fixture-lat1",
    )
    register_book(
        catalog_path,
        work,
        edition,
        ReaderBookArtifact(
            artifact_id="fixture-aeneid",
            work_id=work.work_id,
            edition_id=edition.edition_id,
            artifact_path=book_path,
            source_path=source_path,
            adapter="fixture",
            source_hash="source-sha256",
            segment_count=FIXTURE_SEGMENT_COUNT,
            token_count=7,
        ),
    )
    register_segment_rows(
        book_path,
        segments=[
            ReaderSegment(
                segment_id="fixture-aeneid-1",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                segment_kind="line",
                citation_path="1.1",
                text="Arma virumque cano",
                normalized_text="arma virumque cano",
                sort_key=1,
                source_text="Arma virumque cano",
            ),
            ReaderSegment(
                segment_id="fixture-aeneid-2",
                work_id=work.work_id,
                edition_id=edition.edition_id,
                segment_kind="line",
                citation_path="1.2",
                text="Troiae qui primus ab oris",
                normalized_text="troiae qui primus ab oris",
                sort_key=2,
                source_text="Troiae qui primus ab oris",
            ),
        ],
        addresses=[
            ReaderSegmentAddress(
                segment_id="fixture-aeneid-1",
                address="urn:ctsv2:lat:aeneid-arma-virumque-cano:1.1",
                address_kind="ctsv2",
                citation_path="1.1",
            ),
            ReaderSegmentAddress(
                segment_id="fixture-aeneid-2",
                address="urn:ctsv2:lat:aeneid-arma-virumque-cano:1.2",
                address_kind="ctsv2",
                citation_path="1.2",
            ),
        ],
    )
    register_source_files(
        catalog_path,
        [
            ReaderSourceFile(
                collection_id="fixture",
                source_path=source_path,
                file_role="fixture_tei",
                file_status="text",
                source_id="phi0690.phi003",
                source_hash="source-sha256",
                size_bytes=32,
            )
        ],
    )
    register_source_metadata(
        catalog_path,
        [
            ReaderSourceMetadata(
                collection_id="fixture",
                subject_kind="work",
                subject_id=work.work_id,
                key="import_note",
                value="Fixture import",
                source_path=source_path,
            )
        ],
    )
    register_source_witnesses(
        catalog_path,
        [
            ReaderSourceWitness(
                canonical_text_id=str(work.canonical_text_id),
                work_id=work.work_id,
                collection_id=work.collection_id,
                language=work.language,
                witness_id="fixture-witness",
                source_id=work.source_id,
                source_urn=str(work.cts_work_urn),
                source_path=source_path,
                status="accepted",
                confidence="fixture",
                note="Fixture witness",
            )
        ],
    )
    return catalog_path


def test_export_work_bundle_writes_canonical_files_and_valid_checksums() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_catalog(root)
        output_path = root / "export"

        payload = export_work_bundle(
            catalog_path,
            "urn:langnet:fixture:aeneid",
            output_path,
        )

        assert payload["mode"] == "reader-export-work"
        work_dir = output_path / "works" / "urn-langnet-fixture-aeneid"
        assert (output_path / "manifest.json").exists()
        assert (work_dir / "work.json").exists()
        assert (work_dir / "segments.jsonl").exists()
        assert (work_dir / "provenance.json").exists()
        assert (output_path / "checksums" / "SHA256SUMS").exists()

        manifest = json.loads((output_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["schema_version"] == "langnet.catalog_export.bundle.v1"
        assert manifest["work_count"] == 1
        assert manifest["segment_count"] == FIXTURE_SEGMENT_COUNT

        work = json.loads((work_dir / "work.json").read_text(encoding="utf-8"))
        assert work["schema_version"] == "langnet.catalog_export.work.v1"
        assert work["langnet_work_id"] == "urn:langnet:fixture:aeneid"
        assert work["canonical_text_id"] == "urn:ctsv2:lat:aeneid-arma-virumque-cano"
        assert work["authors"][0]["name"] == "Vergil"
        assert work["source_ids"]["cts_work_urn"] == "urn:cts:latinLit:phi0690.phi003"

        segments = [
            json.loads(line)
            for line in (work_dir / "segments.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert [segment["citation_path"] for segment in segments] == ["1.1", "1.2"]
        assert segments[0]["canonical_address"] == (
            "urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.1"
        )

        provenance = json.loads((work_dir / "provenance.json").read_text(encoding="utf-8"))
        assert provenance["schema_version"] == "langnet.catalog_export.provenance.v1"
        assert provenance["source_index"][0]["file_role"] == "fixture_tei"

        checksum_lines = (
            (output_path / "checksums" / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        )
        checksum_by_path = {
            line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in checksum_lines
        }
        segment_relpath = "works/urn-langnet-fixture-aeneid/segments.jsonl"
        assert (
            checksum_by_path[segment_relpath]
            == hashlib.sha256((work_dir / "segments.jsonl").read_bytes()).hexdigest()
        )

        validation = validate_catalog_export(output_path)
        assert validation["ok"] is True
        assert validation["error_count"] == 0


def test_reader_export_work_cli_writes_and_validates_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_catalog(root)
        output_path = root / "cli-export"

        result = CliRunner().invoke(
            main,
            [
                "reader",
                "--catalog",
                str(catalog_path),
                "export",
                "work",
                "urn:langnet:fixture:aeneid",
                "--output-path",
                str(output_path),
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["mode"] == "reader-export-work"
        assert payload["summary"]["work_count"] == 1
        assert payload["summary"]["segment_count"] == FIXTURE_SEGMENT_COUNT

        validate_result = CliRunner().invoke(
            main,
            [
                "reader",
                "export",
                "validate",
                str(output_path),
                "--output",
                "json",
            ],
        )

        assert validate_result.exit_code == 0, validate_result.output
        validation = json.loads(validate_result.output)
        assert validation["mode"] == "reader-export-validate"
        assert validation["ok"] is True


def test_export_work_bundle_is_checksum_stable_for_unchanged_catalog() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        catalog_path = _write_fixture_catalog(root)

        export_work_bundle(catalog_path, "urn:langnet:fixture:aeneid", root / "first")
        first_checksums = (root / "first" / "checksums" / "SHA256SUMS").read_text(encoding="utf-8")

        time.sleep(1.1)
        export_work_bundle(catalog_path, "urn:langnet:fixture:aeneid", root / "second")
        second_checksums = (root / "second" / "checksums" / "SHA256SUMS").read_text(
            encoding="utf-8"
        )

        assert second_checksums == first_checksums
