from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from langnet.word_index import (
    word_index_list_payload,
    word_index_neighborhood_payload,
    word_index_wheel_payload,
)
from tests.test_word_index import _assert_matches_word_index_schema, _fixture_paths


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


def test_word_index_merged_neighborhood_labels_merged_ordering() -> None:
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
    assert order["policy"] == "source-window-merge"
    assert order["collation"] == "merged-source-window"
    assert "merged" in str(order["explanation"]).lower()
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
