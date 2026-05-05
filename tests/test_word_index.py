from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import duckdb
import jsonschema

from langnet.word_index import (
    WordIndexPaths,
    word_index_list_payload,
    word_index_neighborhood_payload,
    word_index_sources_payload,
    word_index_wheel_payload,
)
from langnet.word_index.service import _best_anchor

WORD_INDEX_SCHEMA_PATH = Path("docs/schemas/word_index.v1.schema.json")
SANSKRIT_SOURCE_BUCKET_COUNT = 3
LATIN_SOURCE_BUCKET_COUNT = 2
FULL_RADIUS_ONE_WINDOW_COUNT = 3
SATYA_HYDRATED_SOURCE_ENTRY_COUNT = 9


def _assert_matches_word_index_schema(payload: object) -> None:
    schema = json.loads(WORD_INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def _fixture_paths(tmp_path: Path) -> WordIndexPaths:
    cdsl_mw = tmp_path / "cdsl_mw.duckdb"
    cdsl_ap90 = tmp_path / "cdsl_ap90.duckdb"
    dico = tmp_path / "lex_dico.duckdb"
    gaffiot = tmp_path / "lex_gaffiot.duckdb"
    diogenes_lat = tmp_path / "lex_diogenes_lat.duckdb"
    diogenes_grc = tmp_path / "lex_diogenes_grc.duckdb"
    _write_cdsl_fixture(cdsl_mw, "MW", [("agni", 1.0), ("Darma", 2.0), ("deva", 3.0)])
    _write_cdsl_fixture(cdsl_ap90, "AP90", [("agni", 1.0), ("DArma", 2.0), ("yoga", 3.0)])
    _write_dico_fixture(dico)
    _write_gaffiot_fixture(gaffiot)
    _write_diogenes_fixture(diogenes_lat, "lat")
    _write_diogenes_fixture(diogenes_grc, "grc")
    return WordIndexPaths(
        cdsl_mw=cdsl_mw,
        cdsl_ap90=cdsl_ap90,
        dico=dico,
        gaffiot=gaffiot,
        diogenes_lat=diogenes_lat,
        diogenes_grc=diogenes_grc,
    )


def _write_cdsl_fixture(path: Path, dict_id: str, entries: list[tuple[str, float]]) -> None:
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE entries (
              dict_id VARCHAR, key VARCHAR, key_normalized VARCHAR, key2 VARCHAR,
              key2_normalized VARCHAR, lnum DOUBLE, hom INTEGER, h_type VARCHAR,
              data TEXT, body TEXT, plain_text TEXT, page_ref VARCHAR
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE headwords (
              dict_id VARCHAR, key VARCHAR, key_normalized VARCHAR, lnum DOUBLE,
              hom INTEGER, is_primary BOOLEAN, search_key VARCHAR
            )
            """
        )
        for key, lnum in entries:
            key_norm = key.lower()
            conn.execute(
                "INSERT INTO entries VALUES (?, ?, ?, NULL, NULL, ?, NULL, NULL, '', '', '', '')",
                [dict_id, key, key_norm, lnum],
            )
            conn.execute(
                "INSERT INTO headwords VALUES (?, ?, ?, ?, NULL, true, ?)",
                [dict_id, key, key_norm, lnum, key_norm],
            )


def _write_dico_fixture(path: Path) -> None:
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE entries_fr (
              entry_id VARCHAR, occurrence INTEGER, headword_deva VARCHAR,
              headword_roma VARCHAR, headword_norm VARCHAR, variant_num INTEGER,
              body_html TEXT, plain_text TEXT, source_page VARCHAR
            )
            """
        )
        conn.executemany(
            "INSERT INTO entries_fr VALUES (?, ?, ?, ?, ?, NULL, '', '', ?)",
            [
                ("agni", 0, "अग्नि", "agni", "agni", "1"),
                ("dharma", 0, "धर्म", "dharma", "dharma", "2"),
                ("deva", 0, "देव", "deva", "deva", "3"),
                ("pura.na", 0, "पुरण", "puraṇa", "pura.na", "41"),
                ("puraa.na", 0, "पुराण", "purāṇa", "puraa.na", "41"),
                ("praa.na", 0, "प्राण", "prāṇa", "praa.na", "45"),
                ("satvara", 0, "सत्वर", "satvara", "satvara", "51"),
                ("satya", 0, "सत्य", "satya", "satya", "52"),
                ("shatya", 0, "शत्य", "śatya", "shatya", "53"),
            ],
        )


def _write_gaffiot_fixture(path: Path) -> None:
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE entries_fr (
              entry_id VARCHAR, headword_raw VARCHAR, headword_norm VARCHAR,
              variant_num INTEGER, tei_xml TEXT, plain_text TEXT, entry_hash VARCHAR,
              updated_at TIMESTAMP
            )
            """
        )
        conn.executemany(
            "INSERT INTO entries_fr VALUES (?, ?, ?, NULL, '', '', ?, NULL)",
            [
                ("gaffiot_1", "amo", "amo", "h1"),
                ("gaffiot_2", "lupus", "lupus", "h2"),
                ("gaffiot_3", "nox", "nox", "h3"),
                ("gaffiot_4", "1 vulternus", "vulternus", "h4"),
                ("gaffiot_5", "2 Vulternus", "vulternus", "h5"),
            ],
        )


def _write_diogenes_fixture(path: Path, language: str) -> None:
    dictionary = "lsj" if language == "grc" else "lewis_short"
    rows = (
        [
            ("grc", dictionary, 10, "ἄγγελος", "αγγελοσ", "angelos", "αγγελοσ", None, 20),
            ("grc", dictionary, 20, "λόγος", "λογοσ", "logos", "λογοσ", 10, 30),
            ("grc", dictionary, 30, "νόμος", "νομοσ", "nomos", "νομοσ", 20, None),
        ]
        if language == "grc"
        else [
            ("lat", dictionary, 10, "amo", "amo", "amo", "amo", None, 20),
            ("lat", dictionary, 20, "lupus", "lupus", "lupus", "lupus", 10, 30),
            ("lat", dictionary, 30, "nox", "nox", "nox", "nox", 20, None),
        ]
    )
    _write_diogenes_rows(path, rows)


def _write_diogenes_rows(path: Path, rows: list[tuple[object, ...]]) -> None:
    with duckdb.connect(str(path)) as conn:
        conn.execute("DROP TABLE IF EXISTS entries")
        conn.execute(
            """
            CREATE TABLE entries (
              language VARCHAR, dictionary VARCHAR, entry_offset BIGINT, headword VARCHAR,
              headword_norm VARCHAR, lookup VARCHAR, sort_key VARCHAR, plain_text TEXT,
              html TEXT, entry_hash VARCHAR, previous_offset BIGINT, next_offset BIGINT,
              fetched_url VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', ?, ?, '', NULL)
            """,
            rows,
        )


def test_word_index_sources_report_local_statuses() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_sources_payload("all", paths=_fixture_paths(Path(tmpdir)))

    _assert_matches_word_index_schema(payload)
    assert payload["schema_version"] == "langnet.word_index.v1"
    sources = cast(list[dict[str, object]], payload["sources"])
    available = [source for source in sources if source["available"]]
    assert {
        (source["language"], source["source"], source["dictionary"]) for source in available
    } == {
        ("san", "cdsl", "mw"),
        ("san", "cdsl", "ap90"),
        ("san", "dico", "dico"),
        ("lat", "gaffiot", "gaffiot"),
        ("lat", "diogenes", "lewis_short"),
        ("grc", "diogenes", "lsj"),
    }


def test_word_index_list_projects_canonical_display() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_list_payload(
            "san",
            source="dico",
            prefix="dh",
            limit=5,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    first = items[0]
    display = cast(dict[str, object], first["display"])
    ids = cast(dict[str, object], first["ids"])
    assert first["lexeme_id"] == "lexeme:san:dharma"
    assert str(first["wheel_id"]).startswith("wheel:san:dharma:")
    assert first["wheel_order_key"] == "00000000000000000000:san:dharma"
    assert str(first["index_entry_id"]).startswith("word-index:san:dico:dico:")
    assert str(first["source_order_id"]).startswith("word-order:san:dico:dico:dharma-")
    assert first["source_order_key"] == "dharma:00000000000000000002:dharma:00000000000000000000"
    assert ids["lexeme"] == first["lexeme_id"]
    assert ids["wheel"] == first["wheel_id"]
    assert ids["index_entry"] == first["index_entry_id"]
    assert ids["source_order"] == first["source_order_id"]
    assert ids["source_ref"] == first["source_ref"]
    assert first["canonical_name"] == "धर्म"
    assert first["canonical_key"] == "dharma"
    assert first["source_name"] == "dharma"
    assert display["transliteration"] == "dharma"
    assert first["encounter"] == {
        "language": "san",
        "q": "dharma",
        "dictionary": "dico",
    }


def test_word_index_neighborhood_returns_before_and_after() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "lat",
            "lupus",
            source="gaffiot",
            radius=1,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    anchor = cast(dict[str, object], neighborhood["anchor"])
    before = cast(list[dict[str, object]], neighborhood["before"])
    after = cast(list[dict[str, object]], neighborhood["after"])
    window = cast(dict[str, object], neighborhood["window"])
    assert anchor["lookup"] == "lupus"
    assert [item["lookup"] for item in before] == ["amo"]
    assert [item["lookup"] for item in after] == ["nox"]
    assert window["policy"] == "source_entry_contiguous"
    assert window["contiguous"] is True
    assert window["collapsed"] is False
    assert window["source_entry_count"] == FULL_RADIUS_ONE_WINDOW_COUNT


def test_word_index_anchor_prefers_exact_headword_over_incidental_form_match() -> None:
    anchor = _best_anchor(
        [
            {
                "canonical_key": "disco",
                "source_name": "disco",
                "lookup": "discus",
                "display": {"source_key": "discus"},
            },
            {
                "canonical_key": "discus",
                "source_name": "discus",
                "lookup": "discus",
                "display": {"source_key": "discus"},
            },
        ],
        "discus",
    )

    assert anchor is not None
    assert anchor["canonical_key"] == "discus"


def test_word_index_list_all_collapses_sources_by_total_ordered_lexeme() -> None:
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
    assert [item["canonical_key"] for item in items] == ["lupus"]
    lupus = items[0]
    source_entries = cast(list[dict[str, object]], lupus["source_entries"])
    assert lupus["lexeme_id"] == "lexeme:lat:lupus"
    assert str(lupus["wheel_id"]).startswith("wheel:lat:lupus:")
    assert lupus["wheel_order_key"] == "00000000000000000002:lat:lupus"
    assert lupus["source_count"] == LATIN_SOURCE_BUCKET_COUNT
    assert {(entry["source"], entry["dictionary"]) for entry in source_entries} == {
        ("gaffiot", "gaffiot"),
        ("diogenes", "lewis_short"),
    }
    assert all(entry["wheel_id"] == lupus["wheel_id"] for entry in source_entries)
    assert all(entry["wheel_order_key"] == lupus["wheel_order_key"] for entry in source_entries)


def test_word_index_list_all_preserves_numbered_source_labels_as_metadata() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_list_payload(
            "lat",
            source="all",
            prefix="vult",
            limit=5,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    assert [item["canonical_key"] for item in items] == ["vulternus"]
    vulternus = items[0]
    display = cast(dict[str, object], vulternus["display"])
    source_entries = cast(list[dict[str, object]], vulternus["source_entries"])
    assert vulternus["canonical_name"] == "vulternus"
    assert display["primary"] == "vulternus"
    assert [entry["source_display"] for entry in source_entries] == [
        "1 vulternus",
        "2 Vulternus",
    ]


def test_word_index_neighborhood_prefers_dico_ascii_length_marks() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "san",
            "puraana",
            source="dico",
            radius=1,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    anchor = cast(dict[str, object], neighborhood["anchor"])
    assert anchor["lookup"] == "purāṇa"
    assert anchor["canonical_key"] == "puraana"
    assert anchor["source_name"] == "puraa.na"
    assert neighborhood["anchor_status"] == "exact"


def test_word_index_neighborhood_expands_unmarked_sanskrit_vowels_as_nearest() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "san",
            "prana",
            source="dico",
            radius=1,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    anchor = cast(dict[str, object], neighborhood["anchor"])
    assert anchor["lookup"] == "prāṇa"
    assert anchor["canonical_key"] == "praana"
    assert neighborhood["anchor_status"] == "nearest"


def test_word_index_neighborhood_bridges_ascii_canonical_to_cdsl_slp1_all_sources() -> None:
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        paths = WordIndexPaths(
            cdsl_mw=tmp_path / "cdsl_mw.duckdb",
            cdsl_ap90=tmp_path / "cdsl_ap90.duckdb",
            dico=tmp_path / "lex_dico.duckdb",
            gaffiot=tmp_path / "lex_gaffiot.duckdb",
            diogenes_lat=tmp_path / "lex_diogenes_lat.duckdb",
            diogenes_grc=tmp_path / "lex_diogenes_grc.duckdb",
        )
        cdsl_entries = [("prAR", 1.0), ("prARa", 2.0), ("prARin", 3.0)]
        _write_cdsl_fixture(paths.cdsl_mw, "MW", cdsl_entries)
        _write_cdsl_fixture(paths.cdsl_ap90, "AP90", cdsl_entries)
        _write_dico_fixture(paths.dico)
        _write_gaffiot_fixture(paths.gaffiot)
        _write_diogenes_fixture(paths.diogenes_lat, "lat")
        _write_diogenes_fixture(paths.diogenes_grc, "grc")

        payload = word_index_neighborhood_payload(
            "san",
            "praana",
            source="all",
            radius=1,
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    groups = cast(list[dict[str, object]], neighborhood["groups"])
    anchors = {
        (group["source"], group["dictionary"]): cast(dict[str, object], group["anchor"])
        for group in groups
    }
    assert anchors[("cdsl", "mw")]["canonical_key"] == "praana"
    assert anchors[("cdsl", "ap90")]["canonical_key"] == "praana"
    assert anchors[("dico", "dico")]["canonical_key"] == "praana"


def test_word_index_neighborhood_source_all_returns_merged_lexeme_layer() -> None:
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        paths = WordIndexPaths(
            cdsl_mw=tmp_path / "cdsl_mw.duckdb",
            cdsl_ap90=tmp_path / "cdsl_ap90.duckdb",
            dico=tmp_path / "lex_dico.duckdb",
            gaffiot=tmp_path / "lex_gaffiot.duckdb",
            diogenes_lat=tmp_path / "lex_diogenes_lat.duckdb",
            diogenes_grc=tmp_path / "lex_diogenes_grc.duckdb",
        )
        cdsl_entries = [("satvara", 1.0), ("satya", 2.0), ("Satya", 3.0)]
        _write_cdsl_fixture(paths.cdsl_mw, "MW", cdsl_entries)
        _write_cdsl_fixture(paths.cdsl_ap90, "AP90", cdsl_entries)
        _write_dico_fixture(paths.dico)
        _write_gaffiot_fixture(paths.gaffiot)
        _write_diogenes_fixture(paths.diogenes_lat, "lat")
        _write_diogenes_fixture(paths.diogenes_grc, "grc")

        payload = word_index_neighborhood_payload(
            "san",
            "satya",
            source="all",
            radius=2,
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    request = cast(dict[str, object], payload["request"])
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    items = cast(list[dict[str, object]], neighborhood["items"])
    groups = cast(list[dict[str, object]], neighborhood["groups"])
    satya_items = [item for item in items if item["lexeme_id"] == "lexeme:san:satya"]
    shatya_items = [item for item in items if item["lexeme_id"] == "lexeme:san:shatya"]
    assert request["merge"] == "lexeme"
    assert neighborhood["policy"] == "merged_lexeme"
    assert groups
    assert len(satya_items) == 1
    assert shatya_items
    satya = satya_items[0]
    source_entries = cast(list[dict[str, object]], satya["source_entries"])
    assert satya["position"] == "anchor"
    assert satya["match"] is True
    assert satya["canonical_key"] == "satya"
    assert {(entry["source"], entry["dictionary"]) for entry in source_entries} == {
        ("cdsl", "ap90"),
        ("cdsl", "mw"),
        ("dico", "dico"),
    }
    assert all(entry["source_display"] for entry in source_entries)


def test_word_index_merged_anchor_hydration_is_radius_independent() -> None:
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        paths = WordIndexPaths(
            cdsl_mw=tmp_path / "cdsl_mw.duckdb",
            cdsl_ap90=tmp_path / "cdsl_ap90.duckdb",
            dico=tmp_path / "lex_dico.duckdb",
            gaffiot=tmp_path / "lex_gaffiot.duckdb",
            diogenes_lat=tmp_path / "lex_diogenes_lat.duckdb",
            diogenes_grc=tmp_path / "lex_diogenes_grc.duckdb",
        )
        cdsl_entries = [
            ("satvara", 1.0),
            ("satya", 2.0),
            ("satya", 3.0),
            ("satya", 4.0),
            ("satya", 5.0),
            ("satyaka", 6.0),
        ]
        _write_cdsl_fixture(paths.cdsl_mw, "MW", cdsl_entries)
        _write_cdsl_fixture(paths.cdsl_ap90, "AP90", cdsl_entries)
        _write_dico_fixture(paths.dico)
        _write_gaffiot_fixture(paths.gaffiot)
        _write_diogenes_fixture(paths.diogenes_lat, "lat")
        _write_diogenes_fixture(paths.diogenes_grc, "grc")

        radius_one = word_index_neighborhood_payload(
            "san",
            "satya",
            source="all",
            radius=1,
            paths=paths,
        )
        radius_three = word_index_neighborhood_payload(
            "san",
            "satya",
            source="all",
            radius=3,
            paths=paths,
        )

    _assert_matches_word_index_schema(radius_one)
    _assert_matches_word_index_schema(radius_three)
    anchor_one = cast(
        dict[str, object],
        cast(dict[str, object], radius_one["neighborhood"])["anchor"],
    )
    anchor_three = cast(
        dict[str, object],
        cast(dict[str, object], radius_three["neighborhood"])["anchor"],
    )
    assert anchor_one["source_entry_count"] == SATYA_HYDRATED_SOURCE_ENTRY_COUNT
    assert anchor_three["source_entry_count"] == SATYA_HYDRATED_SOURCE_ENTRY_COUNT
    assert anchor_one["source_entries"] == anchor_three["source_entries"]


def test_word_index_neighborhood_resolves_greek_physis_to_diogenes_key() -> None:
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        paths = _fixture_paths(tmp_path)
        _write_diogenes_rows(
            paths.diogenes_grc,
            [
                ("grc", "lsj", 10, "φύω", "fuo", "fuo", "fuo", None, 20),
                ("grc", "lsj", 20, "φύσις", "fusis", "fusis", "fusis", 10, 30),
                ("grc", "lsj", 30, "φυσικός", "fusikos", "fusikos", "fusikos", 20, None),
            ],
        )

        payload = word_index_neighborhood_payload(
            "grc",
            "physis",
            source="all",
            radius=1,
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    anchor = cast(dict[str, object], neighborhood["anchor"])
    items = cast(list[dict[str, object]], neighborhood["items"])
    assert neighborhood["policy"] == "merged_lexeme"
    assert neighborhood["anchor_status"] == "exact"
    assert anchor["lookup"] == "fusis"
    assert anchor["canonical_name"] == "φύσις"
    assert anchor["lexeme_id"] == "lexeme:grc:fusis"
    assert any(item["lookup"] == "fusis" and item["position"] == "anchor" for item in items)
    assert any(item["position"] in {"before", "after"} for item in items)


def test_word_index_neighborhood_can_disable_merged_layer() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "san",
            "dharma",
            source="all",
            radius=1,
            merge="none",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    request = cast(dict[str, object], payload["request"])
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    assert request["merge"] == "none"
    assert "groups" in neighborhood
    assert "items" not in neighborhood


def test_word_index_neighborhood_marks_length_variant_as_nearest() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "san",
            "dharma",
            source="cdsl",
            radius=1,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    groups = cast(list[dict[str, object]], neighborhood["groups"])
    statuses = {
        (group["dictionary"], cast(dict[str, object], group["anchor"])["canonical_key"]): group[
            "anchor_status"
        ]
        for group in groups
    }
    assert statuses[("mw", "dharma")] == "exact"
    assert statuses[("ap90", "dhaarma")] == "nearest"


def test_word_index_neighborhood_accepts_native_script_queries() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        san_payload = word_index_neighborhood_payload(
            "san",
            "धर्म",
            source="cdsl",
            radius=1,
            paths=paths,
        )
        grc_payload = word_index_neighborhood_payload(
            "grc",
            "λόγος",
            source="diogenes",
            radius=1,
            paths=paths,
        )

    _assert_matches_word_index_schema(san_payload)
    san_groups = cast(dict[str, object], san_payload["neighborhood"])["groups"]
    san_anchors = [group["anchor"] for group in cast(list[dict[str, object]], san_groups)]
    assert any(
        cast(dict[str, object], anchor)["canonical_key"] == "dharma" for anchor in san_anchors
    )
    assert not any(
        cast(dict[str, object], anchor)["canonical_key"] == "darma" for anchor in san_anchors
    )
    san_statuses = {
        cast(dict[str, object], group["anchor"])["canonical_key"]: group["anchor_status"]
        for group in cast(list[dict[str, object]], san_groups)
    }
    assert san_statuses["dharma"] == "exact"
    assert san_statuses["dhaarma"] == "nearest"

    _assert_matches_word_index_schema(grc_payload)
    grc_neighborhood = cast(dict[str, object], grc_payload["neighborhood"])
    grc_anchor = cast(dict[str, object], grc_neighborhood["anchor"])
    assert grc_anchor["lookup"] == "logos"
    assert grc_neighborhood["anchor_status"] == "exact"


def test_word_index_wheel_interleaves_languages() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_wheel_payload(
            "all",
            source="all",
            count=4,
            seed="stable",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    languages = [item["language"] for item in items]
    assert "san" in languages
    assert "lat" in languages


def test_word_index_wheel_interleaves_sources_within_language() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_wheel_payload(
            "san",
            source="all",
            count=SANSKRIT_SOURCE_BUCKET_COUNT,
            seed="stable",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    assert len(items) == SANSKRIT_SOURCE_BUCKET_COUNT
    assert {(item["source"], item["dictionary"]) for item in items} == {
        ("cdsl", "ap90"),
        ("cdsl", "mw"),
        ("dico", "dico"),
    }


def test_word_index_wheel_collapses_sources_by_lexeme() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_wheel_payload(
            "san",
            source="all",
            count=10,
            seed="stable",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    items = cast(list[dict[str, object]], payload["items"])
    agni = next(item for item in items if item["canonical_key"] == "agni")
    source_entries = cast(list[dict[str, object]], agni["source_entries"])
    assert agni["lexeme_id"] == "lexeme:san:agni"
    assert agni["source_count"] == SANSKRIT_SOURCE_BUCKET_COUNT
    assert agni["source_entry_count"] == SANSKRIT_SOURCE_BUCKET_COUNT
    assert {(entry["source"], entry["dictionary"]) for entry in source_entries} == {
        ("cdsl", "ap90"),
        ("cdsl", "mw"),
        ("dico", "dico"),
    }


def test_word_index_wheel_returns_verified_rows_for_each_supported_language() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        payloads = [
            word_index_wheel_payload("san", source="all", count=4, seed="stable", paths=paths),
            word_index_wheel_payload("lat", source="all", count=4, seed="stable", paths=paths),
            word_index_wheel_payload("grc", source="all", count=4, seed="stable", paths=paths),
        ]

    for payload, language in zip(payloads, ["san", "lat", "grc"], strict=True):
        _assert_matches_word_index_schema(payload)
        items = cast(list[dict[str, object]], payload["items"])
        assert items
        assert {item["language"] for item in items} == {language}
        assert all(item["lexeme_id"] for item in items)
        assert all(item["wheel_id"] for item in items)
        assert all(item["wheel_order_key"] for item in items)
        assert all(item["index_entry_id"] for item in items)
        assert all(item["source_order_id"] for item in items)
        assert all(item["source_order_key"] for item in items)
        assert all(item["canonical_key"] for item in items)
        assert all(item["source_name"] for item in items)


def test_word_index_neighborhood_reads_diogenes_materialized_index() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_neighborhood_payload(
            "grc",
            "logos",
            source="diogenes",
            radius=1,
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    anchor = cast(dict[str, object], neighborhood["anchor"])
    before = cast(list[dict[str, object]], neighborhood["before"])
    after = cast(list[dict[str, object]], neighborhood["after"])
    assert anchor["canonical_name"] == "λόγος"
    assert anchor["lookup"] == "logos"
    assert before[0]["canonical_name"] == "ἄγγελος"
    assert after[0]["canonical_name"] == "νόμος"


def test_word_index_neighborhood_uses_diogenes_source_order() -> None:
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        paths = _fixture_paths(tmp_path)
        _write_diogenes_rows(
            paths.diogenes_grc,
            [
                ("grc", "lsj", 10, "ἀπό", "apo", "apo", "apo", None, 20),
                ("grc", "lsj", 20, "ἀποαγνέω", "apoagneo", "apoagneo", "apoagneo", 10, 30),
                ("grc", "lsj", 30, "ἀποαφύσσω", "apoafusso", "apoafusso", "apoafusso", 20, None),
            ],
        )
        payload = word_index_neighborhood_payload(
            "grc",
            "apo",
            source="diogenes",
            radius=2,
            paths=paths,
        )

    neighborhood = cast(dict[str, object], payload["neighborhood"])
    after = cast(list[dict[str, object]], neighborhood["after"])
    assert [item["lookup"] for item in after] == ["apoagneo", "apoafusso"]
