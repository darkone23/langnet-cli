from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import duckdb

from langnet.reduction import reduce_claims
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    TranslationRecord,
    build_translation_key,
    default_hints_for_language,
    project_cached_translations,
)

TRANSLATION_DURATION_MS = 7
ORIGINAL_TRIPLE_COUNT = 2
FIXTURE_PATH = Path("tests/fixtures/translation_cache_golden_rows.json")


def _gaffiot_claim() -> Mapping[str, Any]:
    return {
        "claim_id": "claim-gaffiot-lupus",
        "tool": "claim.gaffiot",
        "value": {
            "triples": [
                {
                    "subject": "lex:lupus",
                    "predicate": "has_sense",
                    "object": "sense:lex:lupus#gaffiot-loup",
                    "metadata": {
                        "evidence": {
                            "source_tool": "gaffiot",
                            "source_ref": "gaffiot:gaffiot_38776",
                            "variant_num": 1,
                        }
                    },
                },
                {
                    "subject": "sense:lex:lupus#gaffiot-loup",
                    "predicate": "gloss",
                    "object": "loup",
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": "gaffiot:gaffiot_38776",
                        "evidence": {
                            "source_tool": "gaffiot",
                            "source_ref": "gaffiot:gaffiot_38776",
                            "variant_num": 1,
                        },
                    },
                },
            ]
        },
    }


def _dico_claim() -> Mapping[str, Any]:
    return {
        "claim_id": "claim-dico-dharma",
        "tool": "claim.dico",
        "value": {
            "triples": [
                {
                    "subject": "lex:dharma",
                    "predicate": "has_sense",
                    "object": "sense:lex:dharma#dico-dharma",
                    "metadata": {
                        "evidence": {
                            "source_tool": "dico",
                            "source_ref": "dico:34.html#dharma:0",
                        }
                    },
                },
                {
                    "subject": "sense:lex:dharma#dico-dharma",
                    "predicate": "gloss",
                    "object": "loi, devoir, vertu",
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": "dico:34.html#dharma:0",
                        "evidence": {
                            "source_tool": "dico",
                            "source_ref": "dico:34.html#dharma:0",
                        },
                    },
                },
            ]
        },
    }


def _load_golden_fixture() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(FIXTURE_PATH.read_text()))


def _key_from_fixture_row(row: Mapping[str, Any], model: str, language: str):
    return build_translation_key(
        source_lexicon=str(row["source_lexicon"]),
        entry_id=str(row["entry_id"]),
        occurrence=int(row["occurrence"]),
        headword_norm=str(row["headword_norm"]),
        source_text=str(row["source_text"]),
        model=model,
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language(language)),
    )


def _claim_from_fixture_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    source_lexicon = str(row["source_lexicon"])
    headword = str(row["headword_norm"])
    source_ref = str(row["source_ref"])
    source_text = str(row["source_text"])
    sense_anchor = f"sense:lex:{headword}#{source_lexicon}-{row['entry_id']}"
    evidence: dict[str, Any] = {
        "source_tool": source_lexicon,
        "source_ref": source_ref,
    }
    if source_lexicon == "gaffiot":
        evidence["variant_num"] = int(row["occurrence"])
    return {
        "claim_id": f"claim-{source_lexicon}-{row['entry_id']}",
        "tool": f"claim.{source_lexicon}",
        "value": {
            "triples": [
                {
                    "subject": f"lex:{headword}",
                    "predicate": "has_sense",
                    "object": sense_anchor,
                    "metadata": {"evidence": dict(evidence)},
                },
                {
                    "subject": sense_anchor,
                    "predicate": "gloss",
                    "object": source_text,
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": source_ref,
                        "evidence": dict(evidence),
                    },
                },
            ]
        },
    }


def test_cached_gaffiot_translation_projects_as_english_gloss() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    key = build_translation_key(
        source_lexicon="gaffiot",
        entry_id="gaffiot_38776",
        occurrence=1,
        headword_norm="lupus",
        source_text="loup",
        model="test:model",
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("lat")),
    )
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text="wolf",
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )

    projected = project_cached_translations(
        claims=[_gaffiot_claim()],
        language="lat",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])

    english_glosses = [
        triple
        for triple in triples
        if triple.get("predicate") == "gloss" and triple.get("object") == "wolf"
    ]
    assert len(english_glosses) == 1
    metadata = english_glosses[0]["metadata"]
    assert metadata["source_lang"] == "en"
    assert metadata["translation_id"] == key.translation_id
    assert metadata["evidence"]["source_tool"] == "translation"
    assert metadata["evidence"]["source_text_lang"] == "fr"
    assert metadata["evidence"]["gloss_lang"] == "en"
    assert metadata["evidence"]["target_lang"] == "en"
    assert metadata["evidence"]["derived_from_tool"] == "gaffiot"
    assert metadata["evidence"]["derived_from_sense"] == "sense:lex:lupus#gaffiot-loup"
    assert metadata["display_gloss"] == "wolf"
    assert metadata["parsed_glosses"] == ["wolf"]
    assert metadata["translated_segments"] == [
        {
            "index": 0,
            "raw_text": "wolf",
            "display_text": "wolf",
            "segment_type": "translated_gloss_segment",
            "labels": ["translation", "parsed_gloss"],
        }
    ]

    reduction = reduce_claims(query="lupus", language="lat", claims=projected)
    assert "wolf" in {bucket.display_gloss for bucket in reduction.buckets}


def test_projection_leaves_claims_unchanged_without_cache_hit() -> None:
    conn = duckdb.connect(database=":memory:")
    projected = project_cached_translations(
        claims=[_gaffiot_claim()],
        language="lat",
        model="test:model",
        cache=TranslationCache(conn),
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])

    assert len(triples) == ORIGINAL_TRIPLE_COUNT
    assert all(triple.get("object") != "wolf" for triple in triples)


def test_golden_translation_rows_project_gaffiot_and_dico_cache_hits() -> None:
    fixture = _load_golden_fixture()
    rows = cast(list[dict[str, Any]], fixture["rows"])
    model = str(fixture["model"])
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)

    for row in rows:
        language = "lat" if row["source_lexicon"] == "gaffiot" else "san"
        key = _key_from_fixture_row(row, model, language)
        cache.upsert(
            TranslationRecord(
                key=key,
                translated_text=str(row["translated_text"]),
                status="ok",
                duration_ms=TRANSLATION_DURATION_MS,
            )
        )

    latin_projected = project_cached_translations(
        claims=[_gaffiot_claim()],
        language="lat",
        model=model,
        cache=cache,
    )
    sanskrit_projected = project_cached_translations(
        claims=[_dico_claim()],
        language="san",
        model=model,
        cache=cache,
    )

    latin_value = cast(Mapping[str, Any], latin_projected[0]["value"])
    latin_triples = cast(list[dict[str, Any]], latin_value["triples"])
    sanskrit_value = cast(Mapping[str, Any], sanskrit_projected[0]["value"])
    sanskrit_triples = cast(list[dict[str, Any]], sanskrit_value["triples"])

    assert any(triple.get("object") == "wolf" for triple in latin_triples)
    assert any(triple.get("object") == "law, duty, virtue" for triple in sanskrit_triples)
    dharma_translation = next(
        triple for triple in sanskrit_triples if triple.get("object") == "law, duty, virtue"
    )
    assert dharma_translation["metadata"]["parsed_glosses"] == ["law", "duty", "virtue"]

    for row in rows:
        language = "lat" if row["source_lexicon"] == "gaffiot" else "san"
        projected = project_cached_translations(
            claims=[_claim_from_fixture_row(row)],
            language=language,
            model=model,
            cache=cache,
        )
        value = cast(Mapping[str, Any], projected[0]["value"])
        triples = cast(list[dict[str, Any]], value["triples"])
        translated = [
            triple for triple in triples if triple.get("object") == row["translated_text"]
        ]
        assert len(translated) == 1
        assert translated[0]["metadata"]["parsed_glosses"]


def test_golden_translation_row_does_not_project_for_stale_source_text() -> None:
    fixture = _load_golden_fixture()
    rows = cast(list[dict[str, Any]], fixture["rows"])
    model = str(fixture["model"])
    gaffiot_row = rows[0]
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    stale_key = build_translation_key(
        source_lexicon=str(gaffiot_row["source_lexicon"]),
        entry_id=str(gaffiot_row["entry_id"]),
        occurrence=int(gaffiot_row["occurrence"]),
        headword_norm=str(gaffiot_row["headword_norm"]),
        source_text="loup gris",
        model=model,
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("lat")),
    )
    cache.upsert(
        TranslationRecord(
            key=stale_key,
            translated_text=str(gaffiot_row["translated_text"]),
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )

    projected = project_cached_translations(
        claims=[_gaffiot_claim()],
        language="lat",
        model=model,
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])

    assert len(triples) == ORIGINAL_TRIPLE_COUNT
    assert all(triple.get("object") != "wolf" for triple in triples)
