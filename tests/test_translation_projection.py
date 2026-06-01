from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import duckdb

from langnet.cli import _openrouter_translation_callback, _translation_model_candidates
from langnet.reduction import reduce_claims
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    TranslationRecord,
    build_translation_key,
    default_hints_for_language,
    populate_missing_translations,
    project_cached_translations,
    translation_cache_status_counts,
)
from langnet.translation.structured import structured_translation_user_content

TRANSLATION_DURATION_MS = 7
ORIGINAL_TRIPLE_COUNT = 2
EXPECTED_RETRY_CALL_COUNT = 2
EXPECTED_DICO_SEGMENT_BATCH_LIMIT = 900
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


def _bailly_claim() -> Mapping[str, Any]:
    return {
        "claim_id": "claim-bailly-agelaios",
        "tool": "claim.bailly.entries",
        "value": {
            "triples": [
                {
                    "subject": "lex:agelaios",
                    "predicate": "has_sense",
                    "object": "sense:lex:agelaios#bailly-troupeau",
                    "metadata": {
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                        }
                    },
                },
                {
                    "subject": "sense:lex:agelaios#bailly-troupeau",
                    "predicate": "gloss",
                    "object": "qui forme un troupeau",
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": "bailly:bailly-p090-c1-0004",
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                        },
                    },
                },
            ]
        },
    }


def _bailly_structured_claim() -> Mapping[str, Any]:
    source_blocks = [
        {
            "path": "00",
            "parent_path": None,
            "level": 0,
            "marker": "head",
            "kind": "head",
            "text": "ἀγελαῖος",
            "source_ref": "bailly:bailly-p090-c1-0004:00",
        },
        {
            "path": "01",
            "parent_path": None,
            "level": 1,
            "marker": "I",
            "kind": "sense",
            "text": "qui forme un troupeau",
            "source_ref": "bailly:bailly-p090-c1-0004:01",
            "layout": {"column": 1, "top": 200},
        },
        {
            "path": "01:00",
            "parent_path": "01",
            "level": 2,
            "marker": "fig.",
            "kind": "sense",
            "text": "fig. ἀγέλη réuni, Eschl. Pers. 460; Xén. An.; NT. Matth. 4",
            "source_ref": "bailly:bailly-p090-c1-0004:01:00",
            "layout": {"column": 1, "top": 220},
        },
    ]
    source_segments = [
        {
            "index": 0,
            "raw_text": "qui forme un troupeau",
            "display_text": "qui forme un troupeau",
            "segment_type": "definition_segment",
            "labels": ["definition"],
            "source_ref": "bailly:bailly-p090-c1-0004:01",
            "source_path": "01",
            "source_marker": "I",
            "source_level": 1,
        },
        {
            "index": 1,
            "raw_text": "fig. ἀγέλη réuni, Eschl. Pers. 460; Xén. An.; NT. Matth. 4",
            "display_text": "fig. ἀγέλη réuni, Eschl. Pers. 460; Xén. An.; NT. Matth. 4",
            "segment_type": "definition_segment",
            "labels": ["definition"],
            "source_ref": "bailly:bailly-p090-c1-0004:01:00",
            "source_path": "01:00",
            "source_marker": "fig.",
            "source_level": 2,
            "parent_path": "01",
        },
    ]
    return {
        "claim_id": "claim-bailly-agelaios",
        "tool": "claim.bailly.entries",
        "value": {
            "triples": [
                {
                    "subject": "lex:agelaios",
                    "predicate": "has_sense",
                    "object": "sense:lex:agelaios#bailly-troupeau",
                    "metadata": {
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                        }
                    },
                },
                {
                    "subject": "sense:lex:agelaios#bailly-troupeau",
                    "predicate": "gloss",
                    "object": (
                        "qui forme un troupeau fig. ἀγέλη réuni, Eschl. Pers. 460; "
                        "Xén. An.; NT. Matth. 4"
                    ),
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": "bailly:bailly-p090-c1-0004",
                        "source_blocks": source_blocks,
                        "source_segments": source_segments,
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                            "source_lang": "fr",
                        },
                    },
                },
            ]
        },
    }


def _large_bailly_structured_claim(block_count: int = 6) -> Mapping[str, Any]:
    claim = cast(dict[str, Any], _bailly_structured_claim())
    gloss = cast(dict[str, Any], claim["value"])["triples"][1]
    source_blocks = [
        {
            "path": "00",
            "level": 0,
            "marker": "head",
            "kind": "head",
            "text": "λόγος",
            "source_ref": "bailly:bailly-p1450-c1-0024:00",
        }
    ]
    source_segments = []
    source_text_parts = []
    for index in range(block_count):
        path = f"01:{index:02d}"
        text = f"bloc français {index}, λόγος, Hdt. {index}, 1 ||"
        source_blocks.append(
            {
                "path": path,
                "parent_path": "01",
                "level": 2,
                "marker": str(index + 1),
                "kind": "sense",
                "text": text,
                "source_ref": f"bailly:bailly-p1450-c1-0024:{path}",
            }
        )
        source_segments.append(
            {
                "index": index,
                "raw_text": text,
                "display_text": text,
                "segment_type": "definition_segment",
                "labels": ["definition"],
                "source_ref": f"bailly:bailly-p1450-c1-0024:{path}",
                "source_path": path,
                "source_marker": str(index + 1),
                "source_level": 2,
                "parent_path": "01",
            }
        )
        source_text_parts.append(text)

    gloss["object"] = " ".join(source_text_parts)
    gloss["metadata"]["source_ref"] = "bailly:bailly-p1450-c1-0024"
    gloss["metadata"]["source_blocks"] = source_blocks
    gloss["metadata"]["source_segments"] = source_segments
    gloss["metadata"]["evidence"]["source_ref"] = "bailly:bailly-p1450-c1-0024"
    return claim


def _bailly_large_translation_key(claim: Mapping[str, Any]):
    gloss = cast(Mapping[str, Any], cast(Mapping[str, Any], claim["value"])["triples"][1])
    return build_translation_key(
        source_lexicon="bailly",
        entry_id="bailly-p1450-c1-0024",
        occurrence=0,
        headword_norm="agelaios",
        source_text=str(gloss["object"]),
        model="test:model",
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("grc")),
    )


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


def test_translation_prompts_do_not_allow_headword_only_collapse() -> None:
    prompt_text = "\n".join(
        [
            BASE_SYSTEM,
            *default_hints_for_language("san"),
            *default_hints_for_language("lat"),
        ]
    )

    assert "only the source term" not in prompt_text
    assert "Never collapse" in prompt_text
    assert "If any French definition, label, or explanation is present" in prompt_text
    assert "Return only the translated dictionary entry text" in prompt_text
    assert "no Markdown" in prompt_text
    assert "no JSON" in prompt_text


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


def test_cached_bailly_translation_projects_as_english_gloss() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    key = build_translation_key(
        source_lexicon="bailly",
        entry_id="bailly-p090-c1-0004",
        occurrence=0,
        headword_norm="agelaios",
        source_text="qui forme un troupeau",
        model="test:model",
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("grc")),
    )
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text="forming a herd",
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )

    projected = project_cached_translations(
        claims=[_bailly_claim()],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])

    english_glosses = [
        triple
        for triple in triples
        if triple.get("predicate") == "gloss" and triple.get("object") == "forming a herd"
    ]
    assert len(english_glosses) == 1
    metadata = english_glosses[0]["metadata"]
    assert metadata["source_lang"] == "en"
    assert metadata["evidence"]["source_tool"] == "translation"
    assert metadata["evidence"]["derived_from_tool"] == "bailly"
    assert metadata["evidence"]["source_text_lang"] == "fr"
    assert metadata["evidence"]["gloss_lang"] == "en"
    assert metadata["evidence"]["target_lang"] == "en"


def test_bailly_translation_projection_carries_source_block_hierarchy() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    source_blocks = [
        {
            "path": "01",
            "parent_path": None,
            "level": 1,
            "marker": "I",
            "kind": "sense",
            "text": "qui forme un troupeau",
            "source_ref": "bailly:bailly-p090-c1-0004:01",
        }
    ]
    source_segments = [
        {
            "index": 0,
            "raw_text": "qui forme un troupeau",
            "display_text": "qui forme un troupeau",
            "segment_type": "definition_segment",
            "labels": ["definition"],
            "source_ref": "bailly:bailly-p090-c1-0004:01",
            "source_path": "01",
        }
    ]
    claim = {
        "claim_id": "claim-bailly-agelaios",
        "tool": "claim.bailly.entries",
        "value": {
            "triples": [
                {
                    "subject": "lex:agelaios",
                    "predicate": "has_sense",
                    "object": "sense:lex:agelaios#bailly-troupeau",
                    "metadata": {"evidence": {"source_tool": "bailly"}},
                },
                {
                    "subject": "sense:lex:agelaios#bailly-troupeau",
                    "predicate": "gloss",
                    "object": "qui forme un troupeau",
                    "metadata": {
                        "source_lang": "fr",
                        "source_ref": "bailly:bailly-p090-c1-0004",
                        "source_blocks": source_blocks,
                        "source_segments": source_segments,
                        "evidence": {
                            "source_tool": "bailly",
                            "source_ref": "bailly:bailly-p090-c1-0004",
                            "source_lang": "fr",
                        },
                    },
                },
            ]
        },
    }
    key = build_translation_key(
        source_lexicon="bailly",
        entry_id="bailly-p090-c1-0004",
        occurrence=0,
        headword_norm="agelaios",
        source_text="qui forme un troupeau",
        model="test:model",
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("grc")),
    )
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text="which forms a herd",
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )

    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss" and triple.get("object") == "which forms a herd"
    )

    evidence = translated["metadata"]["evidence"]
    assert evidence["source_blocks"] == source_blocks
    assert evidence["source_segments"] == source_segments


def test_bailly_translation_population_requires_matching_block_paths() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    try:
        populate_missing_translations(
            claims=[claim],
            language="grc",
            model="test:model",
            cache=cache,
            translate=lambda _projection: (
                '{"schema_version":"langnet.translation.blocks.v1",'
                '"blocks":[{"path":"99","text":"which forms a herd"}]}'
            ),
        )
    except ValueError as exc:
        assert "Bailly translation block paths changed" in str(exc)
    else:
        raise AssertionError("expected Bailly structured translation validation to fail")
    assert translation_cache_status_counts(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    ) == {"total": 1, "hits": 0, "missing": 0, "errors": 1, "empty": 0}


def test_dico_translation_population_preserves_headword_only_model_output() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "dico",
            "entry_id": "vibhakti",
            "occurrence": 0,
            "headword_norm": "vibhakti",
            "source_ref": "dico:60.html#vibhakti:0",
            "source_text": (
                "vibhakti [act. vibhaj ] f. séparation, distinction ; classification | "
                "gram. désinence, flexion nominale ou verbale"
            ),
        }
    )
    written = populate_missing_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
        translate=lambda _projection: "vibhakti",
    )
    projected = project_cached_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == "vibhakti"


def test_dico_translation_preserves_model_output_without_phrase_repair() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    source_text = (
        "mīmāṃsā [act. dés. man ] f. désir de connaissance ; investigation, examen | "
        "interprétation, exégèse ; casuistique | phil. np. de la doctrine philosophique "
        "Mīmāṃsā ; cf. pūrvamīmāṃsā , uttaramīmāṃsā . "
        "mīmāṃsānukramaṇī [ anukramaṇī ] f. lit. np. de la Mīmāṃsānukramaṇī , "
        "œuvre de Maṇḍana Miśra . "
        "mīmāṃsānyāya [ nyāya ] iic. phil. dialectique de l'exégèse du rituel védique. "
        "mīmāṃsānyāyaprakāśa [ prakāśa ] m. lit. np. de l'exégèse védique "
        "Mīmāṃsānyāyaprakāśa d' Āpadeva ; on l'appelle aussi l' Āpadevī . "
        "mīmāṃsāsūtra [ sūtra ] n. pl. lit. np. du Mīmāṃsāsūtra , "
        "recueil d'aphorismes condensant la doctrine pūrvamīmāṃsā ; "
        "il est postérieur au 4 e siècle ant., mais attribué à Jaimini ; "
        "mīmāṃsāsūtrabhāṣya [ bhāṣya ] n. lit. np. du Mīmāṃsāsūtrabhāṣya , "
        "commentaire du Mīmāṃsāsūtra dû à Śabarasvāmī ; il fut commenté par Kumārila ."
    )
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "dico",
            "entry_id": "miimaa.msaa",
            "occurrence": 0,
            "headword_norm": "miimaa.msaa",
            "source_ref": "dico:45.html#miimaa.msaa:0",
            "source_text": source_text,
        }
    )

    written = populate_missing_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
        translate=lambda _projection: source_text,
    )
    projected = project_cached_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == source_text
    assert "translation_review" not in translated["metadata"]
    assert translation_cache_status_counts(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
    ) == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}


def test_gaffiot_translation_population_preserves_first_model_output() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "gaffiot",
            "entry_id": "gaffiot_22739",
            "occurrence": 2,
            "headword_norm": "edo",
            "source_ref": "gaffiot:gaffiot_22739",
            "source_text": "dĭdī, dĭtum, ĕre, tr., faire sortir : animam Cic. Sest. 83",
        }
    )
    written = populate_missing_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
        translate=lambda _projection: "faire sortir",
    )
    projected = project_cached_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == "faire sortir"


def test_gaffiot_translation_population_preserves_common_kept_french_phrase() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "gaffiot",
            "entry_id": "gaffiot_22739",
            "occurrence": 2,
            "headword_norm": "edo",
            "source_ref": "gaffiot:gaffiot_22739",
            "source_text": "dĭdī, dĭtum, ĕre, tr., faire sortir",
        }
    )

    written = populate_missing_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
        translate=lambda _projection: "faire sortir",
    )
    projected = project_cached_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == "faire sortir"


def test_gaffiot_translation_population_preserves_model_text_without_phrase_repair() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    source_text = (
        "impf. subj. ederem ou ēssem, tr., manger : Cic. Nat. 2, 7 ; "
        "dîner en payant chacun son écot || multi modi salis simul edendi sunt "
        "Cic. Læl. 67, il faut manger force boisseaux de sel ensemble "
        "[pour être de vieux amis]; pugnos edet Pl. Amph. 309, "
        "il tâtera de mes poings [il sera rossé] || [fig.] ronger, consumer : "
        "Virg. G. 1, 151 ; si quid est animum Hor. Ep. 1, 2, 39, "
        "si quelque souci te ronge l'âme || edi sermonem tuum Pl. Aul. 537, "
        "j'ai dévoré tes paroles."
    )
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "gaffiot",
            "entry_id": "gaffiot_22739",
            "occurrence": 2,
            "headword_norm": "edo",
            "source_ref": "gaffiot:gaffiot_22739",
            "source_text": source_text,
        }
    )

    written = populate_missing_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
        translate=lambda _projection: source_text,
    )
    projected = project_cached_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == source_text


def test_gaffiot_translation_population_preserves_ok_cache_without_heuristic_review() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    model = "test:model"
    row = {
        "source_lexicon": "gaffiot",
        "entry_id": "gaffiot_22738",
        "occurrence": 1,
        "headword_norm": "edo",
        "source_ref": "gaffiot:gaffiot_22738",
        "source_text": "manger : dîner en payant chacun son écot",
    }
    claim = _claim_from_fixture_row(row)
    key = _key_from_fixture_row(row, model, "lat")
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text="manger : dîner en payant chacun son écot",
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )

    before = translation_cache_status_counts(
        claims=[claim],
        language="lat",
        model=model,
        cache=cache,
    )
    written = populate_missing_translations(
        claims=[claim],
        language="lat",
        model=model,
        cache=cache,
        translate=lambda _projection: "to eat: to dine with each person paying their share",
    )
    after = translation_cache_status_counts(
        claims=[claim],
        language="lat",
        model=model,
        cache=cache,
    )
    projected = project_cached_translations(
        claims=[claim],
        language="lat",
        model=model,
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])

    assert before == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}
    assert written == 0
    assert after == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )
    assert translated["object"] == "manger : dîner en payant chacun son écot"
    assert "translation_review" not in translated["metadata"]


def test_dico_translation_does_not_attach_heuristic_review() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    model = "test:model"
    row = {
        "source_lexicon": "dico",
        "entry_id": "dharma",
        "occurrence": 0,
        "headword_norm": "dharma",
        "source_ref": "dico:34.html#dharma:0",
        "source_text": "loi, devoir",
    }
    claim = _claim_from_fixture_row(row)
    key = _key_from_fixture_row(row, model, "san")
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text="non-intrinsic designations; ṣaḍdarśana; dharma",
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )

    projected = project_cached_translations(
        claims=[claim],
        language="san",
        model=model,
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert "translation_review" not in translated["metadata"]


def test_dico_translation_population_batches_long_source_segments() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "dico",
            "entry_id": "vibhakti",
            "occurrence": 0,
            "headword_norm": "vibhakti",
            "source_ref": "dico:60.html#vibhakti:0",
            "source_text": (
                "vibhakti [act. vibhaj ] f. séparation, distinction ; classification | "
                "gram. désinence, flexion nominale ou verbale ; on distingue le cas où "
                "la flexion est gouvernée par le rôle [ kāraka ] verbal du cas où elle "
                "gouvernée par la co-occurrence d'un autre mot [ upapada ]. "
                "avibhaktikanirdeśaḥ gram. utilisation de mots non fléchis. "
                "vibhaktipratirūpaka [ pratirūpaka ] a. m. n. gram. de même forme "
                "qu'un mot fléchi ; se dit notamment d'indéclinables [ avyaya_2 ] "
                "comme asti ."
            ),
        }
    )
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    gloss["metadata"]["source_segments"] = [
        {
            "index": 0,
            "raw_text": "vibhakti [act. vibhaj ] f. séparation, distinction",
        },
        {
            "index": 1,
            "raw_text": "classification | gram. désinence, flexion nominale ou verbale",
        },
        {
            "index": 2,
            "raw_text": (
                "on distingue le cas où la flexion est gouvernée par le rôle [ kāraka ] "
                "verbal du cas où elle gouvernée par la co-occurrence d'un autre mot "
                "[ upapada ]."
            ),
        },
        {
            "index": 3,
            "raw_text": "avibhaktikanirdeśaḥ gram. utilisation de mots non fléchis.",
        },
        {
            "index": 4,
            "raw_text": (
                "vibhaktipratirūpaka [ pratirūpaka ] a. m. n. gram. de même forme "
                "qu'un mot fléchi ; se dit notamment d'indéclinables [ avyaya_2 ] "
                "comme asti ."
            ),
        },
    ]
    seen_source_texts: list[str] = []

    def translate(projection: object) -> str:
        source_text = str(getattr(projection, "source_text"))
        seen_source_texts.append(source_text)
        translations: list[str] = []
        if "séparation" in source_text:
            translations.append(
                "vibhakti [act. vibhaj ] f. separation, distinction\n"
                "classification | gram. desinence, nominal or verbal inflection"
            )
        if "on distingue" in source_text:
            translations.append(
                "we distinguish the case where the inflection is governed by the verbal "
                "role [ kāraka ] from the case where it is governed by the co-occurrence "
                "of another word [ upapada ]."
            )
        if "avibhaktikanirdeśaḥ" in source_text:
            translations.append(
                "avibhaktikanirdeśaḥ gram. use of uninflected words.\n"
                "vibhaktipratirūpaka [ pratirūpaka ] a. m. n. gram. of the same form "
                "as an inflected word; said notably of indeclinables [ avyaya_2 ] such as asti ."
            )
        return "\n".join(translations)

    written = populate_missing_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
        translate=translate,
    )
    projected = project_cached_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert len(seen_source_texts) == 1
    assert all(len(text) < EXPECTED_DICO_SEGMENT_BATCH_LIMIT for text in seen_source_texts)
    assert "nominal or verbal inflection" in translated["object"]
    assert "use of uninflected words" in translated["object"]
    assert "indeclinables [ avyaya_2 ]" in translated["object"]


def test_gaffiot_segmented_translation_passes_through_latin_citation_batches() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    source_text = (
        "Cic. Nat. 2, 7 ; Ter. Eun. 540 ; Pl. Amph. 309. "
        "manger : dîner en payant chacun son écot ; "
        "il faut manger force boisseaux de sel ensemble [pour être de vieux amis]. "
        "Pl., Ov. ; ēssētur ; Varro L. 5, 106 ; Hor. Epo. 3, 3 ; S. 2, 8, 90. "
        "Cic. Læl. 67 ; Virg. G. 1, 151 ; En. 5, 683 ; Hor. Ep. 1, 2, 39 ; "
        "edi sermonem tuum Pl. Aul. 537 ; subj. arch. edim, īs, it, etc."
    )
    claim = _claim_from_fixture_row(
        {
            "source_lexicon": "gaffiot",
            "entry_id": "gaffiot_22738",
            "occurrence": 1,
            "headword_norm": "edo",
            "source_ref": "gaffiot:gaffiot_22738",
            "source_text": source_text,
        }
    )
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    gloss["metadata"]["source_segments"] = [
        {"index": 0, "raw_text": "Cic. Nat. 2, 7"},
        {"index": 1, "raw_text": "Ter. Eun. 540"},
        {"index": 2, "raw_text": "Pl. Amph. 309"},
        {"index": 3, "raw_text": "manger : dîner en payant chacun son écot"},
        {
            "index": 4,
            "raw_text": (
                "il faut manger force boisseaux de sel ensemble [pour être de vieux amis]"
            ),
        },
        {"index": 5, "raw_text": "Pl., Ov."},
        {"index": 6, "raw_text": "ēssētur"},
        {"index": 7, "raw_text": "Varro L. 5, 106"},
        {"index": 8, "raw_text": "Hor. Epo. 3, 3"},
        {"index": 9, "raw_text": "S. 2, 8, 90."},
    ]
    seen_source_texts: list[str] = []

    def translate(projection: object) -> str:
        source = str(getattr(projection, "source_text"))
        seen_source_texts.append(source)
        translated = source
        translated = translated.replace(
            "manger : dîner en payant chacun son écot",
            "to eat: to dine with each person paying their share",
        )
        translated = translated.replace(
            "il faut manger force boisseaux de sel ensemble [pour être de vieux amis]",
            "one must eat many bushels of salt together [to be old friends]",
        )
        return translated

    written = populate_missing_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
        translate=translate,
    )
    projected = project_cached_translations(
        claims=[claim],
        language="lat",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert len(seen_source_texts) >= 1
    assert any("dîner" in source for source in seen_source_texts)
    assert any("Hor. Epo. 3, 3" in source for source in seen_source_texts)
    assert "Cic. Nat. 2, 7" in translated["object"]
    assert "each person paying their share" in translated["object"]
    assert "ēssētur" in translated["object"]


def test_dico_translation_population_preserves_headword_only_response() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _dico_claim()

    written = populate_missing_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
        translate=lambda _projection: "dharma",
    )
    projected = project_cached_translations(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == "dharma"
    assert "translation_review" not in translated["metadata"]
    assert translation_cache_status_counts(
        claims=[claim],
        language="san",
        model="test:model",
        cache=cache,
    ) == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}


def test_bailly_structured_translation_repairs_single_echoed_path_typo_by_position() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _large_bailly_structured_claim(block_count=3)

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"schema_version":"langnet.translation.blocks.v1",'
            '"blocks":['
            '{"path":"01:00","text":"translated 00"},'
            '{"path":"01: ","text":"translated 01"},'
            '{"path":"01:02","text":"translated 02"}'
            "]}"
        ),
    )
    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert [block["path"] for block in translated["metadata"]["evidence"]["translated_blocks"]] == [
        f"01:{index:02d}" for index in range(3)
    ]


def test_bailly_structured_translation_request_contains_source_block_paths() -> None:
    seen_payload: dict[str, Any] = {}

    def translate(projection: object) -> str:
        seen_payload.update(json.loads(structured_translation_user_content(projection)))
        return (
            '{"schema_version":"langnet.translation.blocks.v1",'
            '"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}"
        )

    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    populate_missing_translations(
        claims=[_bailly_structured_claim()],
        language="grc",
        model="test:model",
        cache=cache,
        translate=translate,
    )

    assert seen_payload["schema_version"] == "langnet.translation.blocks.request.v1"
    assert seen_payload["source_lexicon"] == "bailly"
    assert [block["path"] for block in seen_payload["blocks"]] == ["01", "01:00"]
    assert seen_payload["blocks"][0]["text"] == "qui forme un troupeau"


def test_bailly_translation_population_batches_large_structured_entries() -> None:
    request_paths: list[list[str]] = []

    def translate(projection: object) -> str:
        request = json.loads(structured_translation_user_content(projection))
        paths = [str(block["path"]) for block in request["blocks"]]
        request_paths.append(paths)
        blocks = [{"path": path, "text": f"translated {path}, λόγος, Hdt. 1 ||"} for path in paths]
        return json.dumps(
            {
                "schema_version": "langnet.translation.blocks.v1",
                "blocks": blocks,
            }
        )

    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _large_bailly_structured_claim(block_count=25)
    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=translate,
    )

    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )
    evidence = translated["metadata"]["evidence"]

    assert written == 1
    assert len(request_paths) > 1
    assert [path for batch in request_paths for path in batch] == [
        f"01:{index:02d}" for index in range(25)
    ]
    assert [block["path"] for block in evidence["translated_blocks"]] == [
        f"01:{index:02d}" for index in range(25)
    ]
    assert translated["object"].startswith("translated 01:00")
    assert "translated 01:24" in translated["object"]


def test_bailly_structured_translation_accepts_fenced_json_response() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            "```json\n"
            '{"schema_version":"langnet.translation.blocks.v1",'
            '"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}\n"
            "```"
        ),
    )

    assert written == 1


def test_bailly_structured_translation_accepts_plain_text_for_single_block() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    source_blocks = cast(list[dict[str, Any]], gloss["metadata"]["source_blocks"])
    source_blocks[:] = [source_blocks[0], source_blocks[1]]
    source_blocks[1]["text"] = "défini- tion, Plat. Phædr. 245 e ||"

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: "definition, Plat. Phædr. 245 e ||",
    )
    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == "definition, Plat. Phædr. 245 e ||"


def test_bailly_structured_translation_accepts_block_json_without_schema_version() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}"
        ),
    )

    assert written == 1


def test_bailly_structured_translation_retries_invalid_batch_response() -> None:
    responses = iter(
        [
            "translated prose instead of json",
            (
                '{"blocks":['
                '{"path":"01","text":"which forms a herd"},'
                '{"path":"01:00","text":"figuratively, gathered together"}'
                "]}"
            ),
        ]
    )
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: next(responses),
    )

    assert written == 1


def test_bailly_structured_translation_retries_provider_exception() -> None:
    calls = 0

    def translate(_projection: object) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("Expecting value: line 603 column 1")
        return (
            '{"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}"
        )

    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=translate,
    )

    assert written == 1
    assert calls == EXPECTED_RETRY_CALL_COUNT


def test_bailly_cached_translation_error_annotates_source_evidence() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _large_bailly_structured_claim(block_count=3)
    key = _bailly_large_translation_key(claim)
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text=None,
            status="error",
            error="Bailly translation response is not JSON",
            duration_ms=17,
        )
    )

    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )

    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    source_gloss = next(triple for triple in triples if triple.get("predicate") == "gloss")
    source_evidence = source_gloss["metadata"]["evidence"]
    translated_glosses = [
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    ]

    assert translated_glosses == []
    assert source_evidence["translation_state"] == {
        "available": False,
        "status": "error",
        "translation_id": key.translation_id,
        "source_lexicon": "bailly",
        "source_text_lang": "fr",
        "target_lang": "en",
        "model": "test:model",
        "source_text_hash": key.source_text_hash,
        "derived_from_tool": "bailly",
        "derived_from_sense": "sense:lex:agelaios#bailly-troupeau",
        "error": "Bailly translation response is not JSON",
        "raw_blob_ref": "entry_translations",
    }


def test_bailly_populate_retries_cached_translation_error() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()
    key = build_translation_key(
        source_lexicon="bailly",
        entry_id="bailly-p090-c1-0004",
        occurrence=0,
        headword_norm="agelaios",
        source_text=(
            "qui forme un troupeau fig. ἀγέλη réuni, Eschl. Pers. 460; Xén. An.; NT. Matth. 4"
        ),
        model="test:model",
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("grc")),
    )
    cache.upsert(
        TranslationRecord(
            key=key,
            translated_text=None,
            status="error",
            error="Bailly translation response is not JSON",
            duration_ms=17,
        )
    )

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}"
        ),
    )
    record = cache.get(key)

    assert written == 1
    assert record is not None
    assert record.status == "ok"
    assert record.error is None
    assert record.translated_text is not None


def test_bailly_structured_translation_allows_unchanged_source_fragments_for_review() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    source_blocks = cast(list[dict[str, Any]], gloss["metadata"]["source_blocks"])
    source_blocks[1]["text"] = "raison, d’où :"
    source_blocks[2]["text"] = "faculté de raisonner, raison"

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"blocks":['
            '{"path":"01","text":"raison, d’où :"},'
            '{"path":"01:00","text":"faculté de raisonner, raison"}'
            "]}"
        ),
    )
    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"] == "raison, d’où :\nfaculté de raisonner, raison"


def test_bailly_structured_translation_allows_expected_unchanged_ngrams() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    source_blocks = cast(list[dict[str, Any]], gloss["metadata"]["source_blocks"])
    source_blocks[1]["text"] = "d’où au plur. tra- ditions historiques"

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"blocks":['
            '{"path":"01","text":"whence in plur. tra- ditions historiques"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}"
        ),
    )
    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"].startswith("whence in plur. tra- ditions historiques")


def test_bailly_structured_translation_does_not_rewrite_semantic_content() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    source_blocks = cast(list[dict[str, Any]], gloss["metadata"]["source_blocks"])
    source_blocks[1]["text"] = "parole :"
    source_blocks[2]["text"] = "fig. ἀγέλη réuni"

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"blocks":['
            '{"path":"01","text":"parole :"},'
            '{"path":"01:00","text":"figuratively, ἀγέλη gathered"}'
            "]}"
        ),
    )
    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    assert written == 1
    assert translated["object"].startswith("parole :")


def test_bailly_structured_translation_accepts_valid_cognate_block() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()
    gloss = cast(dict[str, Any], cast(dict[str, Any], claim["value"])["triples"][1])
    source_blocks = cast(list[dict[str, Any]], gloss["metadata"]["source_blocks"])
    source_blocks[1]["text"] = "argument, Xén. Cyr. 1, 5, 3, etc. ||"
    source_blocks[2]["text"] = "fig. ἀγέλη réuni"

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"blocks":['
            '{"path":"01","text":"argument, Xén. Cyr. 1, 5, 3, etc. ||"},'
            '{"path":"01:00","text":"figuratively, ἀγέλη gathered"}'
            "]}"
        ),
    )

    assert written == 1


def test_openrouter_callback_sends_bailly_blocks_as_structured_json() -> None:
    captured: dict[str, Any] = {}

    class FakeCompletions:
        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
            response_format: Mapping[str, str] | None = None,
            temperature: int | None = None,
        ) -> object:
            captured["model"] = model
            captured["messages"] = messages
            captured["response_format"] = response_format
            captured["temperature"] = temperature
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"schema_version":"langnet.translation.blocks.v1",'
                                '"blocks":[{"path":"01","text":"which forms a herd"}]}'
                            )
                        )
                    )
                ]
            )

    class FakeClient:
        def __init__(self, _config: Mapping[str, str]) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_aisuite = SimpleNamespace(Client=FakeClient)
    projection = SimpleNamespace(
        source=SimpleNamespace(
            source_lexicon="bailly",
            entry_id="bailly-p090-c1-0004",
            source_ref="bailly:bailly-p090-c1-0004",
        ),
        hint="Bailly hint",
        source_text="qui forme un troupeau",
        source_blocks=[
            {
                "path": "01",
                "kind": "sense",
                "text": "qui forme un troupeau",
                "source_ref": "bailly:bailly-p090-c1-0004:01",
            }
        ],
    )

    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False),
        patch.dict(sys.modules, {"aisuite": fake_aisuite}),
    ):
        translated = _openrouter_translation_callback("test:model")(projection)

    user_payload = json.loads(captured["messages"][-1]["content"])
    assert translated.startswith('{"schema_version":"langnet.translation.blocks.v1"')
    assert captured["model"] == "test:model"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["temperature"] == 0
    assert user_payload["schema_version"] == "langnet.translation.blocks.request.v1"
    assert user_payload["blocks"] == [{"path": "01", "text": "qui forme un troupeau"}]


def test_openrouter_callback_falls_back_to_alternate_translation_model() -> None:
    captured_models: list[str] = []

    class FakeCompletions:
        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
            response_format: Mapping[str, str] | None = None,
            temperature: int | None = None,
        ) -> object:
            captured_models.append(model)
            if model == "test:primary":
                raise RuntimeError("bad upstream provider")
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                '{"schema_version":"langnet.translation.blocks.v1",'
                                '"blocks":[{"path":"01","text":"which forms a herd"}]}'
                            )
                        )
                    )
                ]
            )

    class FakeClient:
        def __init__(self, _config: Mapping[str, str]) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_aisuite = SimpleNamespace(Client=FakeClient)
    projection = SimpleNamespace(
        source=SimpleNamespace(
            source_lexicon="bailly",
            entry_id="bailly-p090-c1-0004",
            source_ref="bailly:bailly-p090-c1-0004",
        ),
        hint="Bailly hint",
        source_text="qui forme un troupeau",
        source_blocks=[
            {
                "path": "01",
                "kind": "sense",
                "text": "qui forme un troupeau",
                "source_ref": "bailly:bailly-p090-c1-0004:01",
            }
        ],
    )

    with (
        patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "LANGNET_TRANSLATION_FALLBACK_MODELS": "test:fallback",
            },
            clear=False,
        ),
        patch.dict(sys.modules, {"aisuite": fake_aisuite}),
    ):
        translated = _openrouter_translation_callback("test:primary")(projection)

    assert captured_models == ["test:primary", "test:fallback"]
    assert translated.startswith('{"schema_version":"langnet.translation.blocks.v1"')


def test_translation_model_candidates_default_to_deepseek_after_gemini_primary() -> None:
    with patch.dict(os.environ, {}, clear=True):
        candidates = _translation_model_candidates("openai:google/gemini-2.5-flash")

    assert candidates == [
        "openai:google/gemini-2.5-flash",
        "openai:deepseek/deepseek-v4-flash",
    ]


def test_openrouter_callback_treats_empty_provider_response_as_retryable() -> None:
    captured_models: list[str] = []

    class FakeCompletions:
        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
            response_format: Mapping[str, str] | None = None,
            temperature: int | None = None,
        ) -> object:
            captured_models.append(model)
            content = "" if model == "test:primary" else "wolf"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class FakeClient:
        def __init__(self, _config: Mapping[str, str]) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_aisuite = SimpleNamespace(Client=FakeClient)
    projection = SimpleNamespace(
        source=SimpleNamespace(source_lexicon="gaffiot"),
        hint="Gaffiot hint",
        source_text="loup",
        source_blocks=[],
    )

    with (
        patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "LANGNET_TRANSLATION_FALLBACK_MODELS": "test:fallback",
            },
            clear=False,
        ),
        patch.dict(sys.modules, {"aisuite": fake_aisuite}),
    ):
        translated = _openrouter_translation_callback("test:primary")(projection)

    assert captured_models == ["test:primary", "test:fallback"]
    assert translated == "wolf"


def test_openrouter_callback_falls_back_when_token_rate_is_too_slow() -> None:
    captured_models: list[str] = []

    class FakeCompletions:
        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
            response_format: Mapping[str, str] | None = None,
            temperature: int | None = None,
        ) -> object:
            captured_models.append(model)
            usage = SimpleNamespace(completion_tokens=40)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="wolf"))],
                usage=usage,
            )

    class FakeClient:
        def __init__(self, _config: Mapping[str, str]) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_aisuite = SimpleNamespace(Client=FakeClient)
    projection = SimpleNamespace(
        source=SimpleNamespace(source_lexicon="gaffiot"),
        hint="Gaffiot hint",
        source_text="loup",
        source_blocks=[],
    )

    with (
        patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "LANGNET_TRANSLATION_FALLBACK_MODELS": "test:fallback",
                "LANGNET_TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND": "5",
                "LANGNET_TRANSLATION_MIN_RATE_TOKENS": "24",
                "LANGNET_TRANSLATION_MIN_RATE_SECONDS": "1",
            },
            clear=False,
        ),
        patch.dict(sys.modules, {"aisuite": fake_aisuite}),
        patch("langnet.cli.time.perf_counter", side_effect=[0.0, 20.0, 20.0, 21.0]),
    ):
        translated = _openrouter_translation_callback("test:primary")(projection)

    assert captured_models == ["test:primary", "test:fallback"]
    assert translated == "wolf"


def test_openrouter_callback_rate_budget_estimates_compact_json_tokens() -> None:
    captured_models: list[str] = []
    compact_json = (
        '{"schema_version":"langnet.translation.blocks.v1",'
        '"blocks":[{"path":"01","text":"reason, speech, account, reckoning, '
        "argument, explanation, principle, relation, proportion, formula, "
        'doctrine, report, narrative, statement, discourse"}]}'
    )

    class FakeCompletions:
        def create(
            self,
            *,
            model: str,
            messages: list[dict[str, str]],
            response_format: Mapping[str, str] | None = None,
            temperature: int | None = None,
        ) -> object:
            captured_models.append(model)
            content = compact_json if model == "test:primary" else "wolf"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class FakeClient:
        def __init__(self, _config: Mapping[str, str]) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_aisuite = SimpleNamespace(Client=FakeClient)
    projection = SimpleNamespace(
        source=SimpleNamespace(source_lexicon="gaffiot"),
        hint="Gaffiot hint",
        source_text="loup",
        source_blocks=[],
    )

    with (
        patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "LANGNET_TRANSLATION_FALLBACK_MODELS": "test:fallback",
                "LANGNET_TRANSLATION_MIN_OUTPUT_TOKENS_PER_SECOND": "8",
                "LANGNET_TRANSLATION_MIN_RATE_TOKENS": "24",
                "LANGNET_TRANSLATION_MIN_RATE_SECONDS": "1",
            },
            clear=False,
        ),
        patch.dict(sys.modules, {"aisuite": fake_aisuite}),
        patch("langnet.cli.time.perf_counter", side_effect=[0.0, 30.0, 30.0, 31.0]),
    ):
        translated = _openrouter_translation_callback("test:primary")(projection)

    assert captured_models == ["test:primary", "test:fallback"]
    assert translated == "wolf"


def test_bailly_structured_translation_projects_parallel_english_hierarchy() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    written = populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"schema_version":"langnet.translation.blocks.v1",'
            '"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, gathered together"}'
            "]}"
        ),
    )

    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )
    evidence = translated["metadata"]["evidence"]

    assert written == 1
    assert translated["object"] == "which forms a herd\nfiguratively, gathered together"
    assert [block["path"] for block in evidence["translated_blocks"]] == ["01", "01:00"]
    assert [block.get("parent_path") for block in evidence["translated_blocks"]] == [None, "01"]
    assert [block["level"] for block in evidence["translated_blocks"]] == [1, 2]
    assert [block["marker"] for block in evidence["translated_blocks"]] == ["I", "fig."]
    assert evidence["translated_blocks"][0]["source_ref"] == "bailly:bailly-p090-c1-0004:01"
    assert evidence["translated_blocks"][0]["text"] == "which forms a herd"
    assert evidence["translated_segments"][0]["source_path"] == "01"
    assert evidence["translated_segments"][1]["parent_path"] == "01"
    assert evidence["translated_segments"][1]["display_text"] == "figuratively, gathered together"

    reduction = reduce_claims(query="agelaios", language="grc", claims=projected)
    reduced_witness = next(
        witness
        for bucket in reduction.buckets
        for witness in bucket.witnesses
        if witness.evidence.get("translation_id")
    )
    assert [block["path"] for block in reduced_witness.evidence["translated_blocks"]] == [
        "01",
        "01:00",
    ]


def test_bailly_structured_translation_restores_source_greek_tokens() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    claim = _bailly_structured_claim()

    populate_missing_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
        translate=lambda _projection: (
            '{"schema_version":"langnet.translation.blocks.v1",'
            '"blocks":['
            '{"path":"01","text":"which forms a herd"},'
            '{"path":"01:00","text":"figuratively, ἀγέλη gathered, '
            'Aeschl. Pers. 460; Xen. An.; NT. Matt. 4"}'
            "]}"
        ),
    )

    projected = project_cached_translations(
        claims=[claim],
        language="grc",
        model="test:model",
        cache=cache,
    )
    value = cast(Mapping[str, Any], projected[0]["value"])
    triples = cast(list[dict[str, Any]], value["triples"])
    translated = next(
        triple
        for triple in triples
        if triple.get("predicate") == "gloss"
        and triple.get("metadata", {}).get("source_lang") == "en"
    )

    blocks = translated["metadata"]["evidence"]["translated_blocks"]
    assert blocks[1]["text"] == (
        "figuratively, ἀγέλη gathered, Eschl. Pers. 460; Xén. An.; NT. Matth. 4"
    )


def test_greek_translation_hints_are_bailly_specific_and_citation_averse() -> None:
    hint = "\n".join(default_hints_for_language("grc")).lower()

    assert "bailly" in hint
    assert "general english glosses" in hint
    assert "translate every french explanation" in hint
    assert "bibliographic citations" in hint
    assert "preserve original casing" in hint
    assert "preserve original punctuation" in hint
    assert "french common nouns" in hint
    assert "preserve layout" in hint
    assert "meticulous" in hint
    assert "source-faithful" in hint
    assert "source blocks" in hint
    assert "preserve every requested block path" in hint
    assert "do not merge or drop numbered senses" in hint
    assert "particul. => in particular" in hint
    assert "p. suite => by extension" in hint
    assert "en gén. => in general" in hint
    assert "citation" in hint
    assert "french" in hint
    assert "sanskrit" not in hint
    assert "pierre" not in hint
    assert "stone" not in hint


def test_latin_translation_hints_are_gaffiot_specific_and_source_faithful() -> None:
    hint = "\n".join(default_hints_for_language("lat")).lower()

    assert "gaffiot" in hint
    assert "preserve layout" in hint
    assert "translate every french explanation" in hint
    assert "bibliographic citations" in hint
    assert "preserve original casing" in hint
    assert "preserve original punctuation" in hint
    assert "french common nouns" in hint
    assert "use only meanings present in the source entry" in hint
    assert "meticulous" in hint
    assert "source-faithful" in hint
    assert "inflectional headers" in hint
    assert "principal parts" in hint
    assert "example translations" in hint


def test_sanskrit_translation_hints_are_dico_specific_and_source_faithful() -> None:
    hint = "\n".join(default_hints_for_language("san")).lower()

    assert "dico" in hint
    assert "preserve layout" in hint
    assert "translate every french explanation" in hint
    assert "use only meanings present in the source entry" in hint
    assert "preserve original casing" in hint
    assert "preserve original punctuation" in hint
    assert "french common nouns" in hint
    assert "meticulous" in hint
    assert "source-faithful" in hint
    assert "sanskrit tokens" in hint
    assert "derived compounds" in hint
    assert "do not summarize, omit, reorder, or split" in hint


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
