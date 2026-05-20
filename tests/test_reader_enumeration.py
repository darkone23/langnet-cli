from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest import mock

from langnet.reader import service as reader_service_module
from langnet.reader.builder import ReaderBuildConfig, ReaderBuilder
from langnet.reader.service import ReaderService

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
