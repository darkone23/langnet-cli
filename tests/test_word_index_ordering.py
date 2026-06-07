from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import duckdb

from langnet.word_index import (
    WordIndexPaths,
    word_index_browse_payload,
    word_index_list_payload,
    word_index_neighborhood_payload,
    word_index_wheel_payload,
)
from tests.test_word_index import _assert_matches_word_index_schema, _fixture_paths

CDSL_HOMOGRAPH_FIXTURE_COUNT = 3
CDSL_CROSS_DICTIONARY_HOMOGRAPH_COUNT = 4
CDSL_CROSS_DICTIONARY_SOURCE_COUNT = 2


def test_word_index_rows_explain_source_native_ordering() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_list_payload(
            "san",
            source="dico",
            prefix="dh",
            limit=1,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    order = cast(dict[str, object], items[0]["order"])
    assert order["policy"] == "source-native"
    assert order["label"] == "Sanskrit source order"
    assert order["collation"] == "source"
    assert order["key"] == items[0]["source_order_key"]
    assert order["display_key"] == "धर्म"
    assert "source order key" in str(order["explanation"])


def test_word_index_collapsed_cards_keep_source_entry_order_metadata() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_list_payload(
            "lat",
            source="all",
            prefix="lu",
            limit=5,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    card = items[0]
    card_order = cast(dict[str, object], card["order"])
    source_entries = cast(list[dict[str, object]], card["source_entries"])
    assert card_order["policy"] == "canonical-key"
    assert card_order["key"] == card["wheel_order_key"]
    assert all("order" in entry for entry in source_entries)
    assert {cast(dict[str, object], entry["order"])["policy"] for entry in source_entries} == {
        "source-native"
    }


def test_word_index_browse_groups_source_native_rows_for_all_sources() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_browse_payload(
            "lat",
            source="all",
            prefix="lu",
            limit=2,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    assert cast(dict[str, object], payload["request"])["mode"] == "browse"
    order = cast(dict[str, object], payload["order"])
    assert order["policy"] == "grouped-source-native"
    assert order["collation"] == "source"
    assert cast(list[dict[str, object]], payload["items"])
    groups = cast(list[dict[str, object]], payload["groups"])
    assert [(group["source"], group["dictionary"]) for group in groups] == [
        ("gaffiot", "gaffiot"),
        ("lewis_1890", "lewis_1890"),
        ("georges_1913", "georges_1913"),
        ("whitakers", "whitakers"),
        ("diogenes", "lewis_short"),
    ]
    for group in groups:
        group_order = cast(dict[str, object], group["order"])
        group_items = cast(list[dict[str, object]], group["items"])
        assert group_order["policy"] == "source-native"
        assert group_order["key"] == "lu"
        assert group["entry_count"] == len(group_items)
        assert group_items
        assert all(
            cast(dict[str, object], item["order"])["policy"] == "source-native"
            for item in group_items
        )


def test_word_index_browse_groups_homographs_across_dictionaries() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _insert_cdsl_cross_dictionary_homographs(paths)
        payload = word_index_browse_payload(
            "san",
            source="cdsl",
            prefix="ha",
            limit=5,
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    assert len(items) == 1
    card = items[0]
    assert card["canonical_key"] == "ha"
    assert cast(dict[str, object], card["display"])["primary"] == "ह"
    assert card["homograph_count"] == CDSL_CROSS_DICTIONARY_HOMOGRAPH_COUNT
    assert card["source_count"] == CDSL_CROSS_DICTIONARY_SOURCE_COUNT
    assert card["source_entry_count"] == CDSL_CROSS_DICTIONARY_HOMOGRAPH_COUNT
    assert card["homograph_policy"] == "cross-dictionary-homographs"
    assert card["source_counts"] == [
        {"source": "cdsl", "dictionary": "mw", "count": 3},
        {"source": "cdsl", "dictionary": "ap90", "count": 1},
    ]
    source_entries = cast(list[dict[str, object]], card["source_entries"])
    assert [entry["source_ref"] for entry in source_entries] == [
        "cdsl:mw:30.0",
        "cdsl:mw:31.0",
        "cdsl:mw:32.0",
        "cdsl:ap90:40.0",
    ]
    groups = cast(list[dict[str, object]], payload["groups"])
    assert [(group["dictionary"], group["entry_count"]) for group in groups] == [
        ("mw", 1),
        ("ap90", 1),
    ]


def test_word_index_browse_raw_keeps_top_level_items_empty() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _insert_cdsl_cross_dictionary_homographs(paths)
        payload = word_index_browse_payload(
            "san",
            source="cdsl",
            prefix="ha",
            limit=5,
            homographs="raw",
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    assert payload["items"] == []
    groups = cast(list[dict[str, object]], payload["groups"])
    assert [(group["dictionary"], group["entry_count"]) for group in groups] == [
        ("mw", 3),
        ("ap90", 1),
    ]


def test_word_index_browse_groups_adjacent_homographs_by_default() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _insert_cdsl_homographs(paths)
        payload = word_index_browse_payload(
            "san",
            source="cdsl",
            prefix="kha",
            limit=5,
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    request = cast(dict[str, object], payload["request"])
    assert request["homographs"] == "grouped"
    group = cast(list[dict[str, object]], payload["groups"])[0]
    assert group["homograph_policy"] == "adjacent-source-homographs"
    items = cast(list[dict[str, object]], group["items"])
    assert len(items) == 1
    item = items[0]
    assert item["canonical_key"] == "kha"
    assert item["homograph_count"] == CDSL_HOMOGRAPH_FIXTURE_COUNT
    assert item["source_entry_count"] == CDSL_HOMOGRAPH_FIXTURE_COUNT
    assert item["source_ref"] == "cdsl:mw:10.0"
    source_entries = cast(list[dict[str, object]], item["source_entries"])
    assert [entry["source_ref"] for entry in source_entries] == [
        "cdsl:mw:10.0",
        "cdsl:mw:11.0",
        "cdsl:mw:12.0",
    ]
    assert [entry["source_order_key"] for entry in source_entries] == [
        "ka:00000000000000010000:00000000000000000001",
        "ka:00000000000000011000:00000000000000000002",
        "ka:00000000000000012000:00000000000000000003",
    ]


def test_word_index_browse_raw_homographs_preserves_source_rows() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _insert_cdsl_homographs(paths)
        payload = word_index_browse_payload(
            "san",
            source="cdsl",
            prefix="kha",
            limit=5,
            homographs="raw",
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    request = cast(dict[str, object], payload["request"])
    assert request["homographs"] == "raw"
    group = cast(list[dict[str, object]], payload["groups"])[0]
    assert group["homograph_policy"] == "raw"
    items = cast(list[dict[str, object]], group["items"])
    assert len(items) == CDSL_HOMOGRAPH_FIXTURE_COUNT
    assert [item["source_ref"] for item in items] == [
        "cdsl:mw:10.0",
        "cdsl:mw:11.0",
        "cdsl:mw:12.0",
    ]
    assert all("homograph_count" not in item for item in items)


def test_word_index_browse_keeps_cdsl_slp1_case_distinctions() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _insert_cdsl_na_contrast(paths)
        payload = word_index_browse_payload(
            "san",
            source="cdsl",
            prefix="na",
            limit=5,
            homographs="raw",
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    group = cast(list[dict[str, object]], payload["groups"])[0]
    items = cast(list[dict[str, object]], group["items"])
    assert [item["source_name"] for item in items] == ["na"]
    assert cast(dict[str, object], items[0]["display"])["primary"] == "न"


def test_word_index_neighborhood_keeps_cdsl_slp1_case_distinctions() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _insert_cdsl_na_contrast(paths)
        payload = word_index_neighborhood_payload(
            "san",
            "na",
            source="cdsl",
            radius=1,
            merge="none",
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    groups = (
        cast(list[dict[str, object]], neighborhood["groups"])
        if "groups" in neighborhood
        else [neighborhood]
    )
    mw_group = next(group for group in groups if group["dictionary"] == "mw")
    anchor = cast(dict[str, object], mw_group["anchor"])
    before = cast(list[dict[str, object]], mw_group["before"])
    assert anchor["source_name"] == "na"
    assert cast(dict[str, object], anchor["display"])["primary"] == "न"
    assert [item["source_name"] for item in before] == ["mA"]


def _insert_cdsl_homographs(paths: WordIndexPaths) -> None:
    rows = [
        ("MW", "Ka", "ka", 10.0, 1, "334,1"),
        ("MW", "Ka", "ka", 11.0, 2, "334,1"),
        ("MW", "Ka", "ka", 12.0, 3, "334,2"),
    ]
    with duckdb.connect(str(paths.cdsl_mw)) as conn:
        conn.executemany(
            "INSERT INTO entries VALUES (?, ?, ?, NULL, NULL, ?, ?, NULL, '', '', '', ?)",
            rows,
        )
        conn.executemany(
            "INSERT INTO headwords VALUES (?, ?, ?, ?, ?, true, ?)",
            [
                (dict_id, key, key_norm, lnum, hom, key_norm)
                for dict_id, key, key_norm, lnum, hom, _page_ref in rows
            ],
        )


def _insert_cdsl_cross_dictionary_homographs(paths: WordIndexPaths) -> None:
    mw_rows = [
        ("MW", "ha", "ha", 30.0, 1, "900,1"),
        ("MW", "ha", "ha", 31.0, 2, "900,1"),
        ("MW", "ha", "ha", 32.0, 3, "900,2"),
    ]
    ap90_rows = [("AP90", "ha", "ha", 40.0, 0, "901-a")]
    _insert_cdsl_rows(paths.cdsl_mw, mw_rows)
    _insert_cdsl_rows(paths.cdsl_ap90, ap90_rows)


def _insert_cdsl_na_contrast(paths: WordIndexPaths) -> None:
    rows = [
        ("MW", "Na", "na", 10.0, 1, "335,1"),
        ("MW", "mA", "ma", 20.0, 1, "499,1"),
        ("MW", "na", "na", 21.0, 1, "500,1"),
    ]
    with duckdb.connect(str(paths.cdsl_mw)) as conn:
        _insert_cdsl_rows_into_connection(conn, rows)


def _insert_cdsl_rows(path: Path, rows: list[tuple[str, str, str, float, int, str]]) -> None:
    with duckdb.connect(str(path)) as conn:
        _insert_cdsl_rows_into_connection(conn, rows)


def _insert_cdsl_rows_into_connection(
    conn: duckdb.DuckDBPyConnection,
    rows: list[tuple[str, str, str, float, int, str]],
) -> None:
    conn.executemany(
        "INSERT INTO entries VALUES (?, ?, ?, NULL, NULL, ?, ?, NULL, '', '', '', ?)",
        rows,
    )
    conn.executemany(
        "INSERT INTO headwords VALUES (?, ?, ?, ?, ?, true, ?)",
        [
            (dict_id, key, key_norm, lnum, hom, key_norm)
            for dict_id, key, key_norm, lnum, hom, _page_ref in rows
        ],
    )


def test_word_index_source_all_neighborhood_labels_integrated_ordering() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "san",
            "satya",
            source="all",
            radius=2,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    order = cast(dict[str, object], neighborhood["order"])
    groups = cast(list[dict[str, object]], neighborhood["groups"])
    assert neighborhood["policy"] == "integrated_language_native"
    assert order["policy"] == "language-native"
    assert order["collation"] == "sa-varga"
    assert "integrated" in str(order["explanation"]).lower()
    assert groups
    assert {cast(dict[str, object], group["order"])["policy"] for group in groups} == {
        "source-native"
    }


def test_word_index_wheel_labels_seeded_discovery_ordering() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_wheel_payload(
            "all",
            source="all",
            count=4,
            seed="stable",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    order = cast(dict[str, object], payload["order"])
    assert order["policy"] == "seeded-discovery"
    assert order["collation"] == "seeded-discovery"
    assert order["key"] == "stable"
    assert "seed" in str(order["explanation"])
