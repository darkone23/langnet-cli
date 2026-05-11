from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import duckdb
import jsonschema
from click.testing import CliRunner

from langnet.cli import main
from langnet.word_index import word_index_neighborhood_payload, word_index_sections_payload
from tests.test_word_index import (
    _assert_matches_word_index_schema,
    _fixture_paths,
    _write_diogenes_rows,
)

WORD_INDEX_SECTIONS_SCHEMA_PATH = Path("docs/schemas/word_index_sections.v1.schema.json")


def _assert_matches_sections_schema(payload: object) -> None:
    schema = json.loads(WORD_INDEX_SECTIONS_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def _write_cdsl_rows_preserving_source_keys(
    path: Path, dict_id: str, entries: list[tuple[str, float]]
) -> None:
    with duckdb.connect(str(path)) as conn:
        conn.execute("DROP TABLE IF EXISTS entries")
        conn.execute("DROP TABLE IF EXISTS headwords")
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
            conn.execute(
                "INSERT INTO entries VALUES (?, ?, ?, NULL, NULL, ?, NULL, NULL, '', '', '', '')",
                [dict_id, key, key, lnum],
            )
            conn.execute(
                "INSERT INTO headwords VALUES (?, ?, ?, ?, NULL, true, ?)",
                [dict_id, key, key, lnum, key],
            )


def test_word_index_sections_returns_greek_alphabet_anchors() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_sections_payload(
            "grc",
            source="diogenes",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_sections_schema(payload)
    sections = cast(list[dict[str, object]], payload["sections"])
    assert payload["schema_version"] == "langnet.word_index_sections.v1"
    assert cast(dict[str, object], payload["order"])["collation"] == "grc-lexical"
    assert [section["label"] for section in sections] == [
        "Α",
        "Β",
        "Γ",
        "Δ",
        "Ε",
        "Ζ",
        "Η",
        "Θ",
        "Ι",
        "Κ",
        "Λ",
        "Μ",
        "Ν",
        "Ξ",
        "Ο",
        "Π",
        "Ρ",
        "Σ",
        "Τ",
        "Υ",
        "Φ",
        "Χ",
        "Ψ",
        "Ω",
    ]
    assert [section["label"] for section in sections[:3]] == ["Α", "Β", "Γ"]
    alpha = sections[0]
    assert alpha["transliteration"] == "a"
    assert alpha["available"] is True
    assert cast(dict[str, object], alpha["anchor"])["canonical_key"] == "angelos"
    lambda_section = next(section for section in sections if section["label"] == "Λ")
    assert cast(dict[str, object], lambda_section["anchor"])["canonical_key"] == "logos"


def test_word_index_sections_greek_special_letters_use_source_native_prefixes() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _write_diogenes_rows(
            paths.diogenes_grc,
            [
                ("grc", "lsj", 10, "θ", "θ", "q", "q", None, 20),
                ("grc", "lsj", 20, "ξ", "ξ", "c", "c", 10, 30),
                ("grc", "lsj", 30, "φ", "φ", "f", "f", 20, 40),
                ("grc", "lsj", 40, "χ", "χ", "x", "x", 30, 50),
                ("grc", "lsj", 50, "ψ", "ψ", "y", "y", 40, 60),
                ("grc", "lsj", 60, "ω", "ω", "o", "ω", 50, None),
            ],
        )
        payload = word_index_sections_payload(
            "grc",
            source="diogenes",
            paths=paths,
        )

    _assert_matches_sections_schema(payload)
    sections = {
        str(section["label"]): cast(dict[str, object], section["anchor"])
        for section in cast(list[dict[str, object]], payload["sections"])
    }
    assert sections["Θ"]["query"] == "q"
    assert cast(dict[str, object], sections["Θ"]["display"])["primary"] == "θ"
    assert sections["Ξ"]["query"] == "c"
    assert cast(dict[str, object], sections["Ξ"]["display"])["primary"] == "ξ"
    assert sections["Φ"]["query"] == "f"
    assert cast(dict[str, object], sections["Φ"]["display"])["primary"] == "φ"
    assert sections["Χ"]["query"] == "x"
    assert cast(dict[str, object], sections["Χ"]["display"])["primary"] == "χ"
    assert sections["Ψ"]["query"] == "y"
    assert cast(dict[str, object], sections["Ψ"]["display"])["primary"] == "ψ"
    assert sections["Ω"]["query"] == "ō"
    assert cast(dict[str, object], sections["Ω"]["display"])["primary"] == "ω"


def test_word_index_neighborhood_accepts_greek_section_source_prefixes() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _write_diogenes_rows(
            paths.diogenes_grc,
            [
                ("grc", "lsj", 10, "υ", "υ", "u", "u", None, 20),
                ("grc", "lsj", 20, "ψ", "ψ", "y", "y", 10, 30),
                ("grc", "lsj", 30, "ω", "ω", "o", "ω", 20, None),
            ],
        )

        psi_payload = word_index_neighborhood_payload(
            "grc",
            "y",
            source="diogenes",
            radius=1,
            paths=paths,
        )
        omega_payload = word_index_neighborhood_payload(
            "grc",
            "ō",
            source="diogenes",
            radius=1,
            paths=paths,
        )

    _assert_matches_word_index_schema(psi_payload)
    _assert_matches_word_index_schema(omega_payload)
    psi_anchor = cast(
        dict[str, object], cast(dict[str, object], psi_payload["neighborhood"])["anchor"]
    )
    omega_anchor = cast(
        dict[str, object], cast(dict[str, object], omega_payload["neighborhood"])["anchor"]
    )
    assert cast(dict[str, object], psi_anchor["display"])["primary"] == "ψ"
    assert cast(dict[str, object], omega_anchor["display"])["primary"] == "ω"


def test_word_index_greek_nu_neighborhood_preserves_source_order() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _write_diogenes_rows(
            paths.diogenes_grc,
            [
                ("grc", "lsj", 10, "νοῦσος", "νουσοσ", "nousos", "nousos", None, 20),
                ("grc", "lsj", 20, "νυ", "νυ", "nu", "nu", 10, 30),
                ("grc", "lsj", 30, "νύγμα", "νυγμα", "nugma", "nugma", 20, None),
            ],
        )
        payload = word_index_neighborhood_payload(
            "grc",
            "nu",
            source="diogenes",
            radius=1,
            paths=paths,
        )

    _assert_matches_word_index_schema(payload)
    neighborhood = cast(dict[str, object], payload["neighborhood"])
    anchor = cast(dict[str, object], neighborhood["anchor"])
    before = cast(list[dict[str, object]], neighborhood["before"])
    after = cast(list[dict[str, object]], neighborhood["after"])
    order = cast(dict[str, object], anchor["order"])
    assert [item["lookup"] for item in before] == ["nousos"]
    assert anchor["lookup"] == "nu"
    assert cast(dict[str, object], anchor["display"])["primary"] == "νυ"
    assert [item["lookup"] for item in after] == ["nugma"]
    assert order["collation"] == "grc-lexical"
    assert anchor["source_order_key"] == "00000000000000000020"


def test_word_index_sections_returns_sanskrit_varnamala_groups() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_sections_payload(
            "san",
            source="all",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_sections_schema(payload)
    sections = cast(list[dict[str, object]], payload["sections"])
    assert cast(dict[str, object], payload["order"])["collation"] == "sa-varga"
    assert [section["label"] for section in sections] == [
        "अ",
        "आ",
        "इ",
        "ई",
        "उ",
        "ऊ",
        "ऋ",
        "ॠ",
        "ऌ",
        "ॡ",
        "ए",
        "ऐ",
        "ओ",
        "औ",
        "अं",
        "अः",
        "क",
        "ख",
        "ग",
        "घ",
        "ङ",
        "च",
        "छ",
        "ज",
        "झ",
        "ञ",
        "ट",
        "ठ",
        "ड",
        "ढ",
        "ण",
        "त",
        "थ",
        "द",
        "ध",
        "न",
        "प",
        "फ",
        "ब",
        "भ",
        "म",
        "य",
        "र",
        "ल",
        "व",
        "श",
        "ष",
        "स",
        "ह",
        "क्ष",
        "त्र",
        "ज्ञ",
    ]
    assert [section["label"] for section in sections[:4]] == ["अ", "आ", "इ", "ई"]
    assert sections[0]["group_label"] == "Vowels"
    a_section = sections[0]
    assert a_section["available"] is True
    assert cast(dict[str, object], a_section["anchor"])["canonical_key"] == "agni"
    dental_labels = [
        section["label"] for section in sections if section["group_label"] == "Dentals"
    ]
    assert dental_labels == ["त", "थ", "द", "ध", "न"]
    warnings = cast(list[dict[str, object]], payload["warnings"])
    assert any("section anchors" in str(warning["message"]) for warning in warnings)


def test_word_index_sections_sanskrit_uses_cdsl_native_slp1_prefixes() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _write_cdsl_rows_preserving_source_keys(
            paths.cdsl_mw,
            "MW",
            [
                ("agni", 1.0),
                ("Aman", 2.0),
                ("fzi", 3.0),
                ("Fzi", 4.0),
                ("xkAra", 5.0),
                ("XkAra", 6.0),
                ("eza", 7.0),
                ("Etihya", 8.0),
                ("okas", 9.0),
                ("Ozadhi", 10.0),
                ("aM", 11.0),
                ("aH", 12.0),
                ("ka", 20.0),
                ("Ka", 21.0),
                ("ga", 22.0),
                ("Ga", 23.0),
                ("Na", 24.0),
                ("ca", 30.0),
                ("Ca", 31.0),
                ("ja", 32.0),
                ("Ja", 33.0),
                ("Ya", 34.0),
                ("wa", 40.0),
                ("Wa", 41.0),
                ("qa", 42.0),
                ("Qa", 43.0),
                ("Ra", 44.0),
                ("ta", 50.0),
                ("Ta", 51.0),
                ("da", 52.0),
                ("Da", 53.0),
                ("na", 54.0),
                ("pa", 60.0),
                ("Pa", 61.0),
                ("ba", 62.0),
                ("Ba", 63.0),
                ("ma", 64.0),
                ("ya", 70.0),
                ("ra", 71.0),
                ("la", 72.0),
                ("va", 73.0),
                ("Sa", 80.0),
                ("za", 81.0),
                ("sa", 82.0),
                ("ha", 83.0),
                ("kza", 90.0),
                ("tra", 91.0),
                ("jYa", 92.0),
            ],
        )
        payload = word_index_sections_payload("san", source="cdsl", paths=paths)

    _assert_matches_sections_schema(payload)
    sections = {
        str(section["label"]): cast(dict[str, object], section["anchor"])
        for section in cast(list[dict[str, object]], payload["sections"])
    }
    expected = [
        ("ऋ", "f", "ऋ"),
        ("ॠ", "F", "ॠ"),
        ("ऌ", "x", "ऌ"),
        ("ॡ", "X", "ॡ"),
        ("अं", "aM", "अं"),
        ("अः", "aH", "अः"),
        ("ङ", "N", "ङ"),
        ("ञ", "Y", "ञ"),
        ("ट", "w", "ट"),
        ("ठ", "W", "ठ"),
        ("ड", "q", "ड"),
        ("ढ", "Q", "ढ"),
        ("ण", "R", "ण"),
        ("थ", "T", "थ"),
        ("ध", "D", "ध"),
        ("फ", "P", "फ"),
        ("भ", "B", "भ"),
        ("श", "S", "श"),
        ("ष", "z", "ष"),
        ("क्ष", "kz", "क्ष"),
        ("त्र", "tr", "त्र"),
        ("ज्ञ", "jY", "ज्ञ"),
    ]
    for label, query, primary_prefix in expected:
        assert sections[label]["query"] == query
        display = cast(dict[str, object], sections[label]["display"])
        assert str(display["primary"]).startswith(primary_prefix)


def test_word_index_neighborhood_accepts_sanskrit_section_source_prefixes() -> None:
    with TemporaryDirectory() as tmpdir:
        paths = _fixture_paths(Path(tmpdir))
        _write_cdsl_rows_preserving_source_keys(
            paths.cdsl_mw,
            "MW",
            [
                ("ta", 1.0),
                ("Ra", 2.0),
                ("Sa", 3.0),
                ("za", 4.0),
                ("kza", 5.0),
                ("tra", 6.0),
                ("jYa", 7.0),
            ],
        )

        payloads = {
            query: word_index_neighborhood_payload(
                "san", query, source="cdsl", radius=1, paths=paths
            )
            for query in ["R", "S", "z", "kz", "jY"]
        }

    for payload in payloads.values():
        _assert_matches_word_index_schema(payload)
    expected = {
        "R": "ण",
        "S": "श",
        "z": "ष",
        "kz": "क्ष",
        "jY": "ज्ञ",
    }
    for query, primary in expected.items():
        neighborhood = cast(dict[str, object], payloads[query]["neighborhood"])
        anchor = cast(dict[str, object], neighborhood["anchor"])
        display = cast(dict[str, object], anchor["display"])
        assert str(display["primary"]).startswith(primary)


def test_word_index_sections_returns_latin_alphabet_anchors() -> None:
    with TemporaryDirectory() as tmpdir:
        payload = word_index_sections_payload(
            "lat",
            source="all",
            paths=_fixture_paths(Path(tmpdir)),
        )

    _assert_matches_sections_schema(payload)
    sections = cast(list[dict[str, object]], payload["sections"])
    assert cast(dict[str, object], payload["order"])["collation"] == "lat-lexical"
    assert [section["label"] for section in sections[:3]] == ["A", "B", "C"]
    a_section = sections[0]
    assert a_section["available"] is True
    assert cast(dict[str, object], a_section["anchor"])["canonical_key"] == "amo"


def test_word_index_sections_cli_emits_json() -> None:
    result = CliRunner().invoke(
        main,
        ["word-index", "sections", "grc", "--source", "diogenes", "--output", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_sections_schema(payload)
    assert payload["request"] == {"language": "grc", "source": "diogenes"}
    assert payload["sections"][0]["label"] == "Α"
