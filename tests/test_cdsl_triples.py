from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast
from unittest.mock import patch

import duckdb
import orjson
from query_spec import ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers import cdsl
from tests.claim_contract import assert_claim_contract, claim_triples, find_triple, make_call


def test_cdsl_claim_preserves_source_ref_and_evidence() -> None:
    fetch_call = make_call(
        "fetch.cdsl",
        "fetch-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"lemma": "agni", "dict": "mw"},
        endpoint="duckdb://cdsl/mw",
    )
    rows = [
        {
            "key": "agni",
            "key2": "agni",
            "dict_id": "mw",
            "lnum": "123",
            "plain_text": "fire; sacrificial fire",
            "body": "<H><s>agni</s><lex>m.</lex></H>",
        }
    ]
    raw = RawResponseEffect(
        response_id="resp-cdsl",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(rows),
    )

    extract_call = make_call(
        "extract.cdsl.xml",
        "extract-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = cdsl.extract_xml(extract_call, raw)

    derive_call = make_call(
        "derive.cdsl.sense",
        "derive-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = cdsl.derive_sense(derive_call, extraction)

    claim_call = make_call(
        "claim.cdsl.sense",
        "claim-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = cdsl.claim_sense(claim_call, derivation)

    assert_claim_contract(claim)
    triples = claim_triples(claim)
    has_sense = find_triple(triples, "lex:agni", "has_sense")
    assert has_sense is not None
    sense_anchor = has_sense["object"]
    assert isinstance(sense_anchor, str)
    assert sense_anchor.startswith("sense:lex:agni#")

    gloss = find_triple(triples, sense_anchor, "gloss", "fire; sacrificial fire")
    assert gloss is not None
    metadata = gloss["metadata"]
    assert isinstance(metadata, Mapping)
    assert metadata["source_ref"] == "mw:123"
    assert metadata["display_gloss"] == "fire; sacrificial fire"
    assert metadata["source_entry"] == {
        "dict": "mw",
        "line_number": "123",
        "source_ref": "mw:123",
        "key_slp1": "agni",
        "key_iast": "agni",
        "key2_slp1": "agni",
        "key2_iast": "agni",
    }
    assert metadata["source_segments"] == [
        {
            "index": 0,
            "raw_text": "fire",
            "display_text": "fire",
            "segment_type": "unclassified",
            "labels": [],
        },
        {
            "index": 1,
            "raw_text": "sacrificial fire",
            "display_text": "sacrificial fire",
            "segment_type": "unclassified",
            "labels": [],
        },
    ]
    assert "source_notes" not in metadata
    evidence = metadata["evidence"]
    assert isinstance(evidence, Mapping)
    assert evidence["source_tool"] == "cdsl"
    assert evidence["source_ref"] == "mw:123"
    assert evidence["response_id"] == raw.response_id
    assert evidence["raw_blob_ref"] == "raw_json"


def test_cdsl_claim_adds_display_iast_without_losing_raw_source_form() -> None:
    fetch_call = make_call(
        "fetch.cdsl",
        "fetch-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"lemma": "Darma", "dict": "mw"},
        endpoint="duckdb://cdsl/mw",
    )
    rows = [
        {
            "key": "Darma",
            "key2": "Darma",
            "dict_id": "mw",
            "lnum": "100",
            "plain_text": "law, duty",
            "body": "<H><s>Darma</s><lex>m.</lex></H>",
        },
        {
            "key": "agni",
            "key2": "agni",
            "dict_id": "mw",
            "lnum": "101",
            "plain_text": "fire",
            "body": "<H><s>agni</s><lex>m.</lex></H>",
        },
        {
            "key": "kfzRa",
            "key2": "kfzRa",
            "dict_id": "mw",
            "lnum": "102",
            "plain_text": "dark",
            "body": "<H><s>kfzRa</s><lex>m.</lex></H>",
        },
    ]
    raw = RawResponseEffect(
        response_id="resp-cdsl-display",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(rows),
    )

    extract_call = make_call(
        "extract.cdsl.xml",
        "extract-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
        params={"source_call_id": fetch_call.call_id},
    )
    extraction = cdsl.extract_xml(extract_call, raw)
    derive_call = make_call(
        "derive.cdsl.sense",
        "derive-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
        params={"source_call_id": extract_call.call_id},
    )
    derivation = cdsl.derive_sense(derive_call, extraction)
    claim_call = make_call(
        "claim.cdsl.sense",
        "claim-cdsl",
        cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
        params={"source_call_id": derive_call.call_id},
    )
    claim = cdsl.claim_sense(claim_call, derivation)

    triples = claim_triples(claim)
    dharma = find_triple(triples, "lex:darma", "has_sense")
    assert dharma is not None
    assert dharma["metadata"]["display_iast"] == "dharma"
    assert dharma["metadata"]["display_slp1"] == "Darma"
    assert dharma["metadata"]["source_encoding"] == "slp1"

    agni = find_triple(triples, "lex:agni", "has_sense")
    assert agni is not None
    assert agni["metadata"]["display_iast"] == "agni"
    assert agni["metadata"]["display_slp1"] == "agni"

    krsna = find_triple(triples, "lex:kfzra", "has_sense")
    assert krsna is not None
    assert krsna["metadata"]["display_iast"] == "kṛṣṇa"
    assert krsna["metadata"]["display_slp1"] == "kfzRa"

    dharma_feature = find_triple(
        triples,
        cast(str, dharma["object"]),
        "has_feature",
    )
    assert dharma_feature is not None
    grammar = dharma_feature["object"]["grammar"]
    assert grammar["sanskrit_form"] == "Darma"
    assert grammar["sanskrit_form_slp1"] == "Darma"
    assert grammar["sanskrit_form_iast"] == "dharma"


def test_cdsl_slp1_iast_round_trip_covers_common_sanskrit_letters() -> None:
    assert cdsl._slp1_to_iast("DarmaH") == "dharmaḥ"
    assert cdsl._slp1_to_iast("Da/rma") == "dharma"
    assert cdsl._slp1_to_iast("saMskfta") == "saṃskṛta"
    assert cdsl._slp1_to_iast("aNga") == "aṅga"
    assert cdsl._slp1_to_iast("Pala") == "phala"
    assert cdsl._slp1_to_iast("Bakti") == "bhakti"
    assert cdsl._slp1_to_iast("jYAna") == "jñāna"

    assert cdsl._to_slp1("dharma") == "Darma"
    assert cdsl._to_slp1("aṅga") == "aNga"
    assert cdsl._to_slp1("phala") == "Pala"
    assert cdsl._to_slp1("bhakti") == "Bakti"
    assert cdsl._to_slp1("jñāna") == "jYAna"
    assert cdsl._to_slp1("duḥkha") == "duHKa"
    assert cdsl._to_slp1("śraddhā") == "SradDA"
    assert cdsl._to_slp1("du.hkha") == "duHKa"
    assert "duHKa" in cdsl._candidate_keys("du.hkha")
    assert cdsl._to_slp1("zrAddha") == "SrAdDa"
    assert "SrAdDa" in cdsl._candidate_keys("zrAddha")
    assert "SradDA" in cdsl._candidate_keys("śraddhā")
    assert cdsl._to_slp1("vi.s.nu") == "vizRu"


def test_cdsl_display_text_converts_source_tokens_without_rewriting_english() -> None:
    text = "1. kfzRa/ mf( A/ )n. black, dark-blue; Darma and Da/rma are source forms."

    display = cdsl.cdsl_text_to_iast_display(
        text,
        source_slp1="kfzRa",
        display_iast="kṛṣṇa",
    )

    assert "kṛṣṇa" in display
    assert "black" in display
    assert "dark-blue" in display
    assert "dharma" in display
    assert "dhark" not in display
    assert "of" in cdsl.cdsl_text_to_iast_display("the older form of the RV.")
    assert "steadfast" in cdsl.cdsl_text_to_iast_display("steadfast decree")
    assert "cf." in cdsl.cdsl_text_to_iast_display("cf. above")
    assert "PadmaP." in cdsl.cdsl_text_to_iast_display("MBh. ; PadmaP. ; NārP.")


def test_cdsl_display_text_handles_citation_heavy_gloss_conservatively() -> None:
    text = (
        "mokza moksha, liberation; release from worldly existence; "
        "cf. MBh. ; PadmaP. ; RV. ; steadfast vow"
    )

    display = cdsl.cdsl_text_to_iast_display(
        text,
        source_slp1="mokza",
        display_iast="mokṣa",
    )

    assert "mokṣa" in display
    assert "moksha" in display
    assert "liberation" in display
    assert "release from worldly existence" in display
    assert "cf. MBh. ; PadmaP. ; RV." in display
    assert "steadfast vow" in display


def test_cdsl_display_gloss_preserves_citation_segments() -> None:
    text = (
        "1. mokza m. moksha, liberation; release from worldly existence; cf. MBh. ; PadmaP. ; RV."
    )

    display = cdsl.cdsl_display_gloss(
        text,
        source_slp1="mokza",
        display_iast="mokṣa",
    )

    assert display == (
        "1. mokṣa m. moksha, liberation; release from worldly existence; cf. MBh. ; PadmaP. ; RV."
    )
    assert "MBh" in display
    assert "PadmaP" in display
    assert "RV" in display


def test_cdsl_claim_preserves_raw_gloss_but_adds_display_gloss() -> None:
    fetch_call = make_call(
        "fetch.cdsl",
        "fetch-cdsl-clean",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"lemma": "mokza", "dict": "mw"},
        endpoint="duckdb://cdsl/mw",
    )
    raw_gloss = (
        "1. mokza m. moksha, liberation; release from worldly existence; cf. MBh. ; PadmaP. ; RV."
    )
    rows = [
        {
            "key": "mokza",
            "key2": "mokza",
            "dict_id": "mw",
            "lnum": "200",
            "plain_text": raw_gloss,
            "body": "<H><s>mokza</s><lex>m.</lex></H>",
        }
    ]
    raw = RawResponseEffect(
        response_id="resp-cdsl-clean",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(rows),
    )

    extraction = cdsl.extract_xml(
        make_call(
            "extract.cdsl.xml",
            "extract-cdsl-clean",
            cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
            params={"source_call_id": fetch_call.call_id},
        ),
        raw,
    )
    derivation = cdsl.derive_sense(
        make_call(
            "derive.cdsl.sense",
            "derive-cdsl-clean",
            cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
            params={"source_call_id": "extract-cdsl-clean"},
        ),
        extraction,
    )
    claim = cdsl.claim_sense(
        make_call(
            "claim.cdsl.sense",
            "claim-cdsl-clean",
            cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
            params={"source_call_id": "derive-cdsl-clean"},
        ),
        derivation,
    )

    triples = claim_triples(claim)
    gloss = next(triple for triple in triples if triple["predicate"] == "gloss")
    assert gloss["object"] == raw_gloss
    assert gloss["metadata"]["display_gloss"] == (
        "1. mokṣa m. moksha, liberation; release from worldly existence; cf. MBh. ; PadmaP. ; RV."
    )
    assert gloss["metadata"]["source_segments"] == [
        {
            "index": 0,
            "raw_text": "1. mokza m. moksha, liberation",
            "display_text": "1. mokṣa m. moksha, liberation",
            "segment_type": "unclassified",
            "labels": [],
        },
        {
            "index": 1,
            "raw_text": "release from worldly existence",
            "display_text": "release from worldly existence",
            "segment_type": "unclassified",
            "labels": [],
        },
        {
            "index": 2,
            "raw_text": "cf. MBh.",
            "display_text": "cf. MBh.",
            "segment_type": "cross_reference",
            "labels": ["cross_reference", "source_reference"],
            "recognized_abbreviations": ["MBh"],
        },
        {
            "index": 3,
            "raw_text": "PadmaP.",
            "display_text": "PadmaP.",
            "segment_type": "source_reference",
            "labels": ["source_reference"],
            "recognized_abbreviations": ["PadmaP"],
        },
        {
            "index": 4,
            "raw_text": "RV.",
            "display_text": "RV.",
            "segment_type": "source_reference",
            "labels": ["source_reference"],
            "recognized_abbreviations": ["RV"],
        },
    ]
    assert gloss["metadata"]["source_notes"] == {
        "cross_reference_segments": ["cf. MBh."],
        "source_reference_segments": ["PadmaP.", "RV."],
        "recognized_abbreviations": ["MBh", "PadmaP", "RV"],
    }
    assert gloss["metadata"]["source_ref"] == "mw:200"


def test_cdsl_source_notes_do_not_reclassify_meaning_segments() -> None:
    fetch_call = make_call(
        "fetch.cdsl",
        "fetch-cdsl-dharma-notes",
        cast(ToolStage, ToolStage.TOOL_STAGE_FETCH),
        params={"lemma": "Darma", "dict": "mw"},
        endpoint="duckdb://cdsl/mw",
    )
    raw_gloss = "law, duty; see Mn. ; MBh. ; religious merit"
    rows = [
        {
            "key": "Darma",
            "key2": "Darma",
            "dict_id": "mw",
            "lnum": "201",
            "plain_text": raw_gloss,
            "body": "<H><s>Darma</s><lex>m.</lex></H>",
        }
    ]
    raw = RawResponseEffect(
        response_id="resp-cdsl-dharma-notes",
        tool=fetch_call.tool,
        call_id=fetch_call.call_id,
        endpoint=fetch_call.endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        body=orjson.dumps(rows),
    )
    extraction = cdsl.extract_xml(
        make_call(
            "extract.cdsl.xml",
            "extract-cdsl-dharma-notes",
            cast(ToolStage, ToolStage.TOOL_STAGE_EXTRACT),
            params={"source_call_id": fetch_call.call_id},
        ),
        raw,
    )
    derivation = cdsl.derive_sense(
        make_call(
            "derive.cdsl.sense",
            "derive-cdsl-dharma-notes",
            cast(ToolStage, ToolStage.TOOL_STAGE_DERIVE),
            params={"source_call_id": "extract-cdsl-dharma-notes"},
        ),
        extraction,
    )
    claim = cdsl.claim_sense(
        make_call(
            "claim.cdsl.sense",
            "claim-cdsl-dharma-notes",
            cast(ToolStage, ToolStage.TOOL_STAGE_CLAIM),
            params={"source_call_id": "derive-cdsl-dharma-notes"},
        ),
        derivation,
    )

    triples = claim_triples(claim)
    gloss = next(triple for triple in triples if triple["predicate"] == "gloss")

    assert gloss["object"] == raw_gloss
    assert gloss["metadata"]["display_gloss"] == raw_gloss
    assert gloss["metadata"]["source_segments"] == [
        {
            "index": 0,
            "raw_text": "law, duty",
            "display_text": "law, duty",
            "segment_type": "unclassified",
            "labels": [],
        },
        {
            "index": 1,
            "raw_text": "see Mn.",
            "display_text": "see Mn.",
            "segment_type": "cross_reference",
            "labels": ["cross_reference", "source_reference"],
            "recognized_abbreviations": ["Mn"],
        },
        {
            "index": 2,
            "raw_text": "MBh.",
            "display_text": "MBh.",
            "segment_type": "source_reference",
            "labels": ["source_reference"],
            "recognized_abbreviations": ["MBh"],
        },
        {
            "index": 3,
            "raw_text": "religious merit",
            "display_text": "religious merit",
            "segment_type": "unclassified",
            "labels": [],
        },
    ]
    assert gloss["metadata"]["source_notes"] == {
        "cross_reference_segments": ["see Mn."],
        "source_reference_segments": ["MBh."],
        "recognized_abbreviations": ["Mn", "MBh"],
    }


def test_cdsl_match_filter_prefers_slp1_key_for_iast_like_input() -> None:
    rows = [
        {
            "key": "DarmaH",
            "key2": "DarmaH",
            "key_normalized": "darmah",
            "key2_normalized": "darmah",
            "plain_text": "religion, law, duty",
        },
        {
            "key": "darma",
            "key2": "darma/",
            "key_normalized": "darma",
            "key2_normalized": "darma/",
            "plain_text": "a demolisher",
        },
        {
            "key": "Darma",
            "key2": "Da/rma",
            "key_normalized": "darma",
            "key2_normalized": "da/rma",
            "plain_text": "law, duty",
        },
    ]

    filtered = cdsl._filter_best_cdsl_matches(rows, "dharma")

    assert [entry["key"] for entry in filtered] == ["Darma"]


def test_cdsl_fetch_preserves_case_sensitive_slp1_ranking(tmp_path: Path) -> None:
    db_path = tmp_path / "cdsl_mw.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE entries (
                dict_id VARCHAR,
                key VARCHAR,
                key2 VARCHAR,
                key_normalized VARCHAR,
                key2_normalized VARCHAR,
                lnum VARCHAR,
                body VARCHAR,
                plain_text VARCHAR,
                data VARCHAR
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("mw", "darma", "darma/", "darma", "darma", "1", "", "a demolisher", ""),
                ("mw", "Darma", "Da/rma", "darma", "da/rma", "2", "", "law, duty", ""),
            ],
        )

    with patch("langnet.execution.handlers.cdsl.default_cdsl_path", return_value=db_path):
        response = cdsl.CdslFetchClient().execute(
            "cdsl-1",
            "duckdb",
            {"dict": "mw", "lemma": "Darma"},
        )

    rows = orjson.loads(response.body)
    assert [row["key"] for row in rows] == ["Darma"]


def test_cdsl_match_filter_preserves_lowercase_slp1_query() -> None:
    rows = [
        {
            "key": "DarmaH",
            "key2": "DarmaH",
            "key_normalized": "darmah",
            "key2_normalized": "darmah",
            "plain_text": "religion, law, duty",
        },
        {
            "key": "darma",
            "key2": "darma/",
            "key_normalized": "darma",
            "key2_normalized": "darma/",
            "plain_text": "a demolisher",
        },
        {
            "key": "Darma",
            "key2": "Da/rma",
            "key_normalized": "darma",
            "key2_normalized": "da/rma",
            "plain_text": "law, duty",
        },
    ]

    filtered = cdsl._filter_best_cdsl_matches(rows, "darma")

    assert len(filtered) == 1
    assert filtered[0]["key"] == "darma"


def test_cdsl_match_filter_prefers_slp1_visarga_variant_over_normalized_collision() -> None:
    rows = [
        {
            "key": "darma",
            "key2": "darma",
            "key_normalized": "darma",
            "key2_normalized": "darma",
            "plain_text": "a demolisher",
        },
        {
            "key": "DarmaH",
            "key2": "DarmaH",
            "key_normalized": "darmah",
            "key2_normalized": "darmah",
            "plain_text": "religion, law, duty",
        },
    ]

    filtered = cdsl._filter_best_cdsl_matches(rows, "dharma")

    assert [entry["key"] for entry in filtered] == ["DarmaH"]
