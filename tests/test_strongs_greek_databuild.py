from __future__ import annotations

import json
import tempfile
from pathlib import Path

import duckdb

from langnet.databuild.base import BuildStatus
from langnet.databuild.strongs_greek import (
    StrongsGreekBuildConfig,
    StrongsGreekBuilder,
    lookup_strongs_greek_entries,
    lookup_strongs_greek_entries_by_headword,
    normalize_strongs_greek_key,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<entries>
  <entry strongs="00066">
    <strongs>66</strongs>
    <greek BETA="A)/GRIOS" unicode="ἄγριος" translit="ágrios"/>
    <strongs_def>wild</strongs_def>
  </entry>
  <entry strongs="02268">
    <strongs>2268</strongs>
    <greek BETA="*(HSAI/+AS" unicode="Ἡσαΐας" translit="Hēsaḯas"/>
    <pronunciation strongs="hay-sah-ee'-as"/>
    <strongs_derivation>of Hebrew origin (
      <strongsref language="HEBREW" strongs="03470"/>
    );</strongs_derivation>
    <strongs_def>Hesaias (i.e. Jeshajah), an Israelite</strongs_def>
    <kjv_def>Esaias.</kjv_def>
  </entry>
  <entry strongs="00065">
    <strongs>65</strongs>
    <greek BETA="A)GRIE/LAIOS" unicode="ἀγριέλαιος" translit="agriélaios"/>
    <strongs_derivation>from
      <strongsref language="GREEK" strongs="66"/>
      and
      <strongsref language="GREEK" strongs="1636"/>
    ;</strongs_derivation>
    <strongs_def>wild olive</strongs_def>
  </entry>
  <entry strongs="00001">
    <strongs>1</strongs>
    <greek BETA="A" unicode="Α" translit="A"/>
    <strongs_def>Alpha</strongs_def>
  </entry>
</entries>
"""

COMBINED_STRONGS_JSON = [
    {
        "number": "G66",
        "lemma": "ἄγριος",
        "xlit": "ágrios",
        "pronounce": "ag'-ree-os",
        "description": "wild",
    },
    {
        "number": "G1636",
        "lemma": "ἐλαία",
        "xlit": "elaía",
        "pronounce": "el-ah-yah",
        "description": "an olive",
    },
    {
        "number": "H3470",
        "lemma": "יְשַׁעְיָה",
        "xlit": "Yᵉshaʻyâh",
        "pronounce": "yesh-ah-yaw'",
        "description": "Jah has saved",
    },
]


def test_strongs_greek_build_imports_xml_entries_and_aliases_forms() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "strongsgreek.xml"
        output = base / "lex_strongs_greek.duckdb"
        source.write_text(SAMPLE_XML, encoding="utf-8")

        result = StrongsGreekBuilder(
            StrongsGreekBuildConfig(source_path=source, output_path=output, batch_size=1)
        ).build()
        entries = lookup_strongs_greek_entries("Ἠσαίᾳ", output)

    assert result.status == BuildStatus.SUCCESS, result.message
    assert len(entries) == 1
    assert entries[0]["entry_id"] == "strongs-greek:G2268"
    assert entries[0]["strongs_number"] == "G2268"
    assert entries[0]["lemma_unicode"] == "Ἡσαΐας"
    assert entries[0]["matched_alias_display"] == "Ἡσαΐᾳ"
    assert "Hesaias" in entries[0]["display_gloss"]
    assert "Esaias" in entries[0]["display_gloss"]
    assert "H3470" in entries[0]["display_gloss"]
    assert "()" not in entries[0]["display_gloss"]


def test_strongs_greek_build_imports_combined_lexicon_and_resolves_embedded_refs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "strongsgreek.xml"
        combined_source = base / "strongs.json"
        output = base / "lex_strongs_greek.duckdb"
        source.write_text(SAMPLE_XML, encoding="utf-8")
        combined_source.write_text(
            json.dumps(COMBINED_STRONGS_JSON, ensure_ascii=False), encoding="utf-8"
        )

        result = StrongsGreekBuilder(
            StrongsGreekBuildConfig(
                source_path=source,
                combined_lexicon_path=combined_source,
                output_path=output,
            )
        ).build()
        agrielaios = lookup_strongs_greek_entries_by_headword(["G65"], output)
        hesaias = lookup_strongs_greek_entries_by_headword(["G2268"], output)

        with duckdb.connect(str(output)) as conn:
            reference_rows = conn.execute(
                """
                SELECT strongs_number, language, lemma_unicode
                FROM strongs_lexicon
                ORDER BY strongs_number
                """
            ).fetchall()

    assert result.status == BuildStatus.SUCCESS, result.message
    assert set(reference_rows) == {
        ("G66", "grc", "ἄγριος"),
        ("G1636", "grc", "ἐλαία"),
        ("H3470", "heb", "יְשַׁעְיָה"),
    }
    assert "ἄγριος and ἐλαία" in agrielaios[0]["display_gloss"]
    assert "G66" not in agrielaios[0]["display_gloss"]
    assert "יְשַׁעְיָה" in hesaias[0]["display_gloss"]
    assert "H3470" not in hesaias[0]["display_gloss"]


def test_strongs_greek_lookup_accepts_ordered_candidates_and_numbers() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "strongsgreek.xml"
        output = base / "lex_strongs_greek.duckdb"
        source.write_text(SAMPLE_XML, encoding="utf-8")
        result = StrongsGreekBuilder(
            StrongsGreekBuildConfig(source_path=source, output_path=output)
        ).build()

        entries = lookup_strongs_greek_entries_by_headword(["missing", "G2268"], output)

    assert result.status == BuildStatus.SUCCESS, result.message
    assert [entry["strongs_number"] for entry in entries] == ["G2268"]
    assert entries[0]["matched_alias_kind"] == "strongs_number"


def test_strongs_greek_normalization_strips_greek_diacritics_and_sigma_variants() -> None:
    assert normalize_strongs_greek_key("Ἡσαΐας") == "ησαιασ"
    assert normalize_strongs_greek_key("Ἠσαίᾳ") == "ησαια"
    assert normalize_strongs_greek_key("Hēsaḯas") == "hesaias"
    assert normalize_strongs_greek_key("G2268") == "g2268"


def test_strongs_greek_build_creates_alias_index() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        source = base / "strongsgreek.xml"
        output = base / "lex_strongs_greek.duckdb"
        source.write_text(SAMPLE_XML, encoding="utf-8")
        result = StrongsGreekBuilder(
            StrongsGreekBuildConfig(source_path=source, output_path=output)
        ).build()

        with duckdb.connect(str(output)) as conn:
            indexes = {
                row[0] for row in conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()
            }

    assert result.status == BuildStatus.SUCCESS, result.message
    assert "strongs_greek_alias_key_idx" in indexes
    assert "strongs_greek_strongs_number_idx" in indexes
