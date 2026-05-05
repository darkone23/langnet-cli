from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import duckdb
import jsonschema
from click.testing import CliRunner
from filelock import FileLock
from query_spec import CanonicalCandidate, NormalizedQuery

from langnet.cli import (
    LanguageHint,
    NormalizeConfig,
    _encounter_bucket_sort_key,
    _encounter_compact_gloss,
    _encounter_component_candidates,
    _encounter_foster_display,
    _encounter_lemma_compare_keys,
    _encounter_morphology_fallback_terms,
    _encounter_morphology_rows,
    _encounter_preferred_lemmas_for_sorting,
    _encounter_preferred_lemmas_from_morphology,
    _get_query_value_for_plan,
    main,
)
from langnet.execution.effects import ClaimEffect, ProvenanceLink
from langnet.normalizer.core import NormalizationResult, _hash_query
from langnet.storage.normalization_index import ensure_schema as ensure_normalization_schema
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    TranslationRecord,
    build_translation_key,
    default_hints_for_language,
)

TRANSLATION_FIXTURE_PATH = Path("tests/fixtures/translation_cache_golden_rows.json")
ENCOUNTER_SCHEMA_PATH = Path("docs/schemas/encounter.v1.schema.json")
ENCOUNTER_ERROR_SCHEMA_PATH = Path("docs/schemas/encounter-error.v1.schema.json")
GAFFIOT_LUPUS_SOURCE_ORDER = 38776


def _claim_with_triples(
    *, tool: str, subject: str, triples: list[dict[str, object]]
) -> ClaimEffect:
    return ClaimEffect(
        claim_id=f"clm-{tool}",
        tool=f"claim.{tool}.fixture",
        call_id=f"call-{tool}",
        source_call_id=f"derive-{tool}",
        derivation_id=f"drv-{tool}",
        subject=subject,
        predicate="has_sense",
        value={"triples": triples},
        provenance_chain=[
            ProvenanceLink(
                stage="derive",
                tool=f"derive.{tool}.fixture",
                reference_id=f"drv-{tool}",
            )
        ],
        handler_version="test",
    )


def _translation_language(source_lexicon: str) -> str:
    return "lat" if source_lexicon == "gaffiot" else "san"


def _assert_matches_schema(payload: object, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_encounter_morphology_rows_from_interpretation_triples() -> None:
    claim = _claim_with_triples(
        tool="whitakers",
        subject="lex:armum#noun",
        triples=[
            {
                "subject": "form:arma",
                "predicate": "has_interpretation",
                "object": "interp:form:arma→lex:armum#noun",
                "metadata": {"evidence": {"source_tool": "whitaker"}},
            },
            {
                "subject": "interp:form:arma→lex:armum#noun",
                "predicate": "realizes_lexeme",
                "object": "lex:armum#noun",
                "metadata": {"evidence": {"source_tool": "whitaker"}},
            },
            {
                "subject": "interp:form:arma→lex:armum#noun",
                "predicate": "has_pos",
                "object": "noun",
                "metadata": {"evidence": {"source_tool": "whitaker"}},
            },
            {
                "subject": "interp:form:arma→lex:armum#noun",
                "predicate": "has_case",
                "object": "nominative",
                "metadata": {"evidence": {"source_tool": "whitaker"}},
            },
            {
                "subject": "interp:form:arma→lex:armum#noun",
                "predicate": "has_number",
                "object": "plural",
                "metadata": {"evidence": {"source_tool": "whitaker"}},
            },
            {
                "subject": "interp:form:arma→lex:armum#noun",
                "predicate": "has_gender",
                "object": "neuter",
                "metadata": {"evidence": {"source_tool": "whitaker"}},
            },
        ],
    )

    assert _encounter_morphology_rows([asdict(claim)]) == [
        {
            "source_tool": "whitaker",
            "form": "arma",
            "lemma": "armum",
            "analysis": "noun; nominative; plural; neuter",
        }
    ]


def test_encounter_morphology_rows_from_form_feature_triples() -> None:
    claim = _claim_with_triples(
        tool="diogenes",
        subject="lex:mhnis",
        triples=[
            {
                "subject": "form:mhnis",
                "predicate": "inflection_of",
                "object": "lex:mhnis",
                "metadata": {"evidence": {"source_tool": "diogenes"}},
            },
            {
                "subject": "form:mhnis",
                "predicate": "has_pos",
                "object": "noun",
                "metadata": {"evidence": {"source_tool": "diogenes"}},
            },
            {
                "subject": "form:mhnis",
                "predicate": "has_feature",
                "object": {"tags": ["fem", "sg"], "defs": ["wrath"]},
                "metadata": {"evidence": {"source_tool": "diogenes"}},
            },
        ],
    )

    assert _encounter_morphology_rows([asdict(claim)]) == [
        {
            "source_tool": "diogenes",
            "form": "mhnis",
            "lemma": "mhnis",
            "analysis": "noun; tags: fem, sg",
        }
    ]


def test_encounter_foster_display_renders_full_learner_labels() -> None:
    assert _encounter_foster_display("lat", "noun; nominative; plural; neuter") == (
        "Naming Function; Group; Neuter"
    )
    assert _encounter_foster_display("san", "m. sg. voc.") == ("Calling Function; Single; Male")
    assert _encounter_foster_display("san", "n. sg. acc. | n. sg. nom.") == (
        "Receiving Function; Single; Neuter / Naming Function; Single; Neuter"
    )


def test_encounter_compact_gloss_extracts_learner_summary_from_source_entry() -> None:
    assert (
        _encounter_compact_gloss(
            "ĭī, n. (princeps), 1 commencement : nec principium nec finem habere"
        )
        == "commencement"
    )
    assert _encounter_compact_gloss("God, the Deity, in general sense, both sg. and pl.") == (
        "God, the Deity, in general sense"
    )


def test_encounter_adds_local_latin_ae_morphology_when_source_parse_is_empty() -> None:
    reduction = SimpleNamespace(lexeme_anchors=["lex:troia"], buckets=[])

    assert _encounter_morphology_rows(
        [],
        language="lat",
        original="Troiae",
        reduction=reduction,
    ) == [
        {
            "source_tool": "local",
            "form": "Troiae",
            "lemma": "troia",
            "analysis": (
                "first-declension -ae form; genitive/dative singular or nominative/vocative plural"
            ),
        }
    ]


def test_encounter_adds_local_greek_epic_eos_morphology_when_source_parse_is_empty() -> None:
    reduction = SimpleNamespace(lexeme_anchors=["lex:axilleus"], buckets=[])

    assert _encounter_morphology_rows(
        [],
        language="grc",
        original="Ἀχιλῆος",
        reduction=reduction,
    ) == [
        {
            "source_tool": "local",
            "form": "Ἀχιλῆος",
            "lemma": "axilleus",
            "analysis": "epic genitive singular; -ῆος form of a -εύς noun",
        }
    ]


def test_get_query_value_for_plan_uses_passthrough_for_greek_script() -> None:
    query = _get_query_value_for_plan(
        "ἀρχῇ",
        LanguageHint.LANGUAGE_HINT_GRC,
        normalize=True,
        norm_cfg=NormalizeConfig(
            diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
            heritage_base="http://localhost:48080",
            db_path="/path/that/should/not/be/opened.duckdb",
            no_cache=False,
            output="pretty",
        ),
    )

    assert query.original == "ἀρχῇ"
    assert query.candidates[0].lemma == "ἀρχῇ"
    assert query.candidates[0].sources == ["manual"]


def test_get_query_value_for_plan_normalizes_greek_compatibility_symbol() -> None:
    normalized = NormalizedQuery(
        original="ὄμϐρος",
        language=LanguageHint.LANGUAGE_HINT_GRC,
        candidates=[
            CanonicalCandidate(
                lemma="ὄμβρος",
                sources=["diogenes_word_list"],
            )
        ],
    )
    service = SimpleNamespace(
        normalize=lambda _text, _lang_hint: SimpleNamespace(normalized=normalized)
    )

    with patch("langnet.cli._create_normalization_service", return_value=service):
        query = _get_query_value_for_plan(
            "ὄμϐρος",
            LanguageHint.LANGUAGE_HINT_GRC,
            normalize=True,
            norm_cfg=NormalizeConfig(
                diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
                heritage_base="http://localhost:48080",
                db_path="examples/debug/nonexistent/test-normalize.duckdb",
                no_cache=True,
                output="pretty",
            ),
        )

    assert query.candidates[0].lemma == "ὄμβρος"


def test_get_query_value_for_plan_normalizes_greek_epic_eos_form() -> None:
    normalized = NormalizedQuery(
        original="Ἀχιλῆος",
        language=LanguageHint.LANGUAGE_HINT_GRC,
        candidates=[
            CanonicalCandidate(
                lemma="ἀχιλλεύς",
                sources=["diogenes_word_list_epic_eus"],
            )
        ],
    )
    service = SimpleNamespace(
        normalize=lambda _text, _lang_hint: SimpleNamespace(normalized=normalized)
    )

    with patch("langnet.cli._create_normalization_service", return_value=service):
        query = _get_query_value_for_plan(
            "Ἀχιλῆος",
            LanguageHint.LANGUAGE_HINT_GRC,
            normalize=True,
            norm_cfg=NormalizeConfig(
                diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
                heritage_base="http://localhost:48080",
                db_path="examples/debug/nonexistent/test-normalize.duckdb",
                no_cache=True,
                output="pretty",
            ),
        )

    assert query.candidates[0].lemma == "ἀχιλλεύς"


def test_get_query_value_for_plan_does_not_hold_cache_lock_during_normalization() -> None:
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(db_path)) as conn:
            ensure_normalization_schema(conn)

        class LockCheckingService:
            def normalize(self, text: str, lang_hint: int) -> NormalizationResult:
                with FileLock(f"{db_path}.lock", timeout=0):
                    pass
                normalized = NormalizedQuery(
                    original=text,
                    language=lang_hint,
                    candidates=[CanonicalCandidate(lemma="hen", encodings={}, sources=["fixture"])],
                )
                return NormalizationResult(
                    query_hash=_hash_query(text, lang_hint),
                    normalized=normalized,
                )

        with patch("langnet.cli._create_normalization_service", return_value=LockCheckingService()):
            query = _get_query_value_for_plan(
                "hen",
                LanguageHint.LANGUAGE_HINT_GRC,
                normalize=True,
                norm_cfg=NormalizeConfig(
                    diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
                    heritage_base="http://localhost:48080",
                    db_path=str(db_path),
                    no_cache=False,
                    output="pretty",
                ),
            )

        assert query.candidates[0].lemma == "hen"


def test_lemma_compare_keys_include_pos_anchor_base() -> None:
    assert "armum" in _encounter_lemma_compare_keys("armum#noun")


def test_sanskrit_morphology_fallback_ignores_compound_component_lemmas() -> None:
    claim = _claim_with_triples(
        tool="heritage",
        subject="lex:dharmakṣetra",
        triples=[
            {
                "subject": "form:dharma",
                "predicate": "has_morphology",
                "object": {"lemma": "dharma", "form": "dharma", "analysis": "iic."},
                "metadata": {"evidence": {"source_tool": "heritage"}},
            },
            {
                "subject": "form:kṣetra",
                "predicate": "has_morphology",
                "object": {"lemma": "kṣetra", "form": "kṣetra", "analysis": "n. sg. loc."},
                "metadata": {"evidence": {"source_tool": "heritage"}},
            },
        ],
    )

    assert (
        _encounter_morphology_fallback_terms(
            [asdict(claim)],
            language="san",
            original="dharmakṣetre",
        )
        == []
    )


def test_encounter_sanskrit_component_candidates_follow_compound_solution() -> None:
    rows = [
        {
            "source_tool": "heritage",
            "form": "aṣṭan",
            "lemma": "aṣṭan",
            "analysis": "iic.",
            "solution_number": "1",
        },
        {
            "source_tool": "heritage",
            "form": "aṅga_1",
            "lemma": "aṅga_1",
            "analysis": "n. sg. voc.",
            "solution_number": "1",
        },
        {
            "source_tool": "heritage",
            "form": "aṣṭan",
            "lemma": "aṣṭan",
            "analysis": "* pl. nom.",
            "solution_number": "2",
        },
        {
            "source_tool": "heritage",
            "form": "aṅga_2",
            "lemma": "aṅga_2",
            "analysis": "ind.",
            "solution_number": "2",
        },
    ]

    assert _encounter_component_candidates(rows, language="san") == [
        {
            "surface": "aṣṭan",
            "lemma": "aṣṭan",
            "display": "aṣṭan",
            "role": "initial",
            "analysis": "iic.",
            "source_tool": "heritage",
            "lookup_terms": ["aṣṭan", "aṣṭa"],
        },
        {
            "surface": "aṅga_1",
            "lemma": "aṅga_1",
            "display": "aṅga",
            "role": "final",
            "analysis": "n. sg. voc.",
            "source_tool": "heritage",
            "lookup_terms": ["aṅga"],
        },
    ]


def test_encounter_latin_component_candidates_link_tackon_and_base() -> None:
    rows = [
        {
            "source_tool": "whitaker",
            "form": "que",
            "lemma": "que",
            "analysis": "tackon",
        },
        {
            "source_tool": "whitaker",
            "form": "virum",
            "lemma": "virum",
            "analysis": "noun; declension 2; nominative; singular; neuter; accusative",
        },
        {
            "source_tool": "whitaker",
            "form": "virum",
            "lemma": "vir",
            "analysis": "noun; declension 2; accusative; singular; masculine",
        },
    ]

    assert _encounter_component_candidates(rows, language="lat") == [
        {
            "surface": "virum",
            "lemma": "vir",
            "display": "vir",
            "role": "base",
            "analysis": "noun; declension 2; accusative; singular; masculine",
            "source_tool": "whitaker",
            "lookup_terms": ["vir"],
        },
        {
            "surface": "que",
            "lemma": "que",
            "display": "-que",
            "role": "tackon",
            "analysis": "tackon",
            "source_tool": "whitaker",
            "lookup_terms": ["que"],
        },
    ]


def _claim_from_translation_row(row: dict[str, object]) -> ClaimEffect:
    source_lexicon = str(row["source_lexicon"])
    headword = str(row["headword_norm"])
    source_ref = str(row["source_ref"])
    source_text = str(row["source_text"])
    sense_anchor = f"sense:lex:{headword}#{source_lexicon}-{row['entry_id']}"
    evidence: dict[str, object] = {
        "source_tool": source_lexicon,
        "source_ref": source_ref,
    }
    if source_lexicon == "gaffiot":
        evidence["variant_num"] = int(str(row["occurrence"]))
    return _claim_with_triples(
        tool=source_lexicon,
        subject=f"lex:{headword}",
        triples=[
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
        ],
    )


def _write_translation_cache_from_rows(
    *,
    cache_path: Path,
    rows: list[dict[str, object]],
    model: str,
) -> None:
    conn = duckdb.connect(str(cache_path))
    try:
        cache = TranslationCache(conn)
        for row in rows:
            source_lexicon = str(row["source_lexicon"])
            key = build_translation_key(
                source_lexicon=source_lexicon,
                entry_id=str(row["entry_id"]),
                occurrence=int(str(row["occurrence"])),
                headword_norm=str(row["headword_norm"]),
                source_text=str(row["source_text"]),
                model=model,
                prompt=BASE_SYSTEM,
                hint="\n".join(default_hints_for_language(_translation_language(source_lexicon))),
            )
            cache.upsert(
                TranslationRecord(
                    key=key,
                    translated_text=str(row["translated_text"]),
                    status="ok",
                    duration_ms=5,
                )
            )
    finally:
        conn.close()


def test_encounter_sanskrit_cdsl_snapshot() -> None:
    triples = [
        {
            "subject": "lex:Darma",
            "predicate": "has_sense",
            "object": "sense:lex:Darma#1",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:1"},
                "display_iast": "dharma",
                "display_slp1": "Darma",
                "source_encoding": "slp1",
            },
        },
        {
            "subject": "sense:lex:Darma#1",
            "predicate": "gloss",
            "object": "dharma; duty",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:1"},
                "display_iast": "dharma",
                "display_slp1": "Darma",
                "source_encoding": "slp1",
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="cdsl", subject="lex:Darma", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "dharma",
                "cdsl",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n"
        "============\n"
        "Forms: dharma\n"
        "Source keys: Darma\n"
        "\n"
        "Meanings\n"
        "1. dharma; duty\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "   refs: mw:1\n"
    )


def test_encounter_json_includes_ranking_explanations() -> None:
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#wolf",
            "metadata": {
                "evidence": {"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_38776"}
            },
        },
        {
            "subject": "sense:lex:lupus#wolf",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {
                "display_gloss": "wolf",
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_38776",
                },
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "gaffiot",
                "--output",
                "json",
                "--translation-mode",
                "off",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    payload = json.loads(cli_result.output)
    assert len(payload["ranking"]) == 1
    ranking = payload["ranking"][0]
    assert ranking["display_gloss"] == "wolf"
    assert ranking["has_bilingual_source"] is True
    assert ranking["source_order"] == GAFFIOT_LUPUS_SOURCE_ORDER
    assert "has DICO/Gaffiot bilingual source evidence" in ranking["reasons"]


def test_encounter_json_includes_public_contract_display_views() -> None:
    triples = [
        {
            "subject": "form:arma",
            "predicate": "has_interpretation",
            "object": "interp:form:arma→lex:armum#noun",
            "metadata": {"evidence": {"source_tool": "whitaker"}},
        },
        {
            "subject": "interp:form:arma→lex:armum#noun",
            "predicate": "realizes_lexeme",
            "object": "lex:armum#noun",
            "metadata": {"evidence": {"source_tool": "whitaker"}},
        },
        {
            "subject": "interp:form:arma→lex:armum#noun",
            "predicate": "has_pos",
            "object": "noun",
            "metadata": {"evidence": {"source_tool": "whitaker"}},
        },
        {
            "subject": "interp:form:arma→lex:armum#noun",
            "predicate": "has_case",
            "object": "nominative",
            "metadata": {"evidence": {"source_tool": "whitaker"}},
        },
        {
            "subject": "interp:form:arma→lex:armum#noun",
            "predicate": "has_number",
            "object": "plural",
            "metadata": {"evidence": {"source_tool": "whitaker"}},
        },
        {
            "subject": "interp:form:arma→lex:armum#noun",
            "predicate": "has_gender",
            "object": "neuter",
            "metadata": {"evidence": {"source_tool": "whitaker"}},
        },
        {
            "subject": "lex:arma",
            "predicate": "has_sense",
            "object": "sense:lex:arma#gaffiot",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_123",
                }
            },
        },
        {
            "subject": "sense:lex:arma#gaffiot",
            "predicate": "gloss",
            "object": "weapons; arms; cf. armum",
            "metadata": {
                "display_gloss": "weapons; arms",
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_123",
                    "raw_blob_ref": "tei_xml",
                    "source_entry": {
                        "dict": "gaffiot",
                        "entry_id": "gaffiot_123",
                        "headword_norm": "arma",
                        "source_ref": "gaffiot:gaffiot_123",
                        "source_text": "weapons; arms; cf. armum",
                    },
                    "source_segments": [
                        {
                            "display_text": "cf. armum",
                            "labels": ["cross_reference", "source_reference"],
                        }
                    ],
                },
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="latin", subject="lex:arma", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "arma",
                "all",
                "--output",
                "json",
                "--translation-mode",
                "off",
                "--max-gloss-chars",
                "20",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    payload = json.loads(cli_result.output)
    _assert_matches_schema(payload, ENCOUNTER_SCHEMA_PATH)
    assert payload["query"] == "arma"
    assert payload["schema_version"] == "langnet.encounter.v1"
    assert payload["request"] == {
        "language": "lat",
        "text": "arma",
        "tool_filter": "all",
        "normalize": True,
        "no_cache": False,
        "include_cltk": False,
        "translation_mode": "off",
    }
    assert payload["display"]["header"] == {"forms": ["arma"], "source_keys": []}
    assert payload["display"]["analysis"] == [
        {
            "form": "arma",
            "lemma": "armum",
            "analysis": "noun; nominative; plural; neuter",
            "source": "whitaker",
            "foster_display": "Naming Function; Group; Neuter",
            "display_text": (
                "arma -> armum: noun; nominative; plural; neuter "
                "[Foster: Naming Function; Group; Neuter] (whitaker)"
            ),
        }
    ]
    assert payload["display"]["meanings"][0]["bucket_id"] == payload["buckets"][0]["bucket_id"]
    assert payload["display"]["meanings"][0]["display_gloss"] == "weapons; arms"
    assert payload["display"]["meanings"][0]["evidence_gloss"] == ""
    assert payload["display"]["meanings"][0]["source_refs"] == ["gaffiot:gaffiot_123"]
    assert payload["display"]["meanings"][0]["source_detail_summary"] == {
        "cross_refs": ["cf. armum"],
        "source_refs": [],
        "examples": [],
        "text": "cross refs: cf. armum",
    }
    assert payload["display"]["meanings"][0]["entries"] == [
        {
            "witness_id": payload["buckets"][0]["witnesses"][0]["wsu_id"],
            "lexeme_anchor": "lex:arma",
            "sense_anchor": "sense:lex:arma#gaffiot",
            "claim_id": "clm-latin",
            "source_tool": "gaffiot",
            "source_ref": "gaffiot:gaffiot_123",
            "source_lang": "",
            "gloss_lang": "",
            "display_form": "arma",
            "source_key": "",
            "headword": "arma",
            "entry_id": "gaffiot_123",
            "dictionary": "gaffiot",
            "raw_blob_ref": "tei_xml",
            "source_encoding": "",
            "source_entry": {
                "dict": "gaffiot",
                "entry_id": "gaffiot_123",
                "headword_norm": "arma",
                "source_ref": "gaffiot:gaffiot_123",
                "source_text_chars": 24,
                "has_source_text": True,
            },
            "source_detail_summary": {
                "cross_refs": ["cf. armum"],
                "source_refs": [],
                "examples": [],
                "text": "cross refs: cf. armum",
            },
            "translation": {
                "available": False,
                "translation_id": "",
                "source_lexicon": "",
                "source_text_lang": "",
                "target_lang": "",
                "model": "",
                "source_text_hash": "",
                "derived_from_tool": "",
                "derived_from_sense": "",
            },
        }
    ]
    assert payload["display"]["options"] == {
        "max_gloss_chars": 20,
        "foster_labels": True,
        "source_details": True,
    }


def test_encounter_json_links_sanskrit_compound_components() -> None:
    surface_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="fixture",
                subject="lex:azwanga",
                triples=[
                    {
                        "subject": "form:aṣṭan",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "aṣṭan",
                            "form": "aṣṭan",
                            "analysis": "iic.",
                            "solution_number": "1",
                        },
                        "metadata": {"evidence": {"source_tool": "heritage"}},
                    },
                    {
                        "subject": "form:aṅga_1",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "aṅga_1",
                            "form": "aṅga_1",
                            "analysis": "n. sg. voc.",
                            "solution_number": "1",
                        },
                        "metadata": {"evidence": {"source_tool": "heritage"}},
                    },
                    {
                        "subject": "lex:azwanga",
                        "predicate": "has_sense",
                        "object": "sense:lex:azwanga#eight",
                        "metadata": {
                            "evidence": {"source_tool": "cdsl", "source_ref": "mw:20308.0"},
                            "display_iast": "aṣṭāṅga",
                            "display_slp1": "azwANga",
                        },
                    },
                    {
                        "subject": "sense:lex:azwanga#eight",
                        "predicate": "gloss",
                        "object": "consisting of eight parts or members",
                        "metadata": {
                            "evidence": {"source_tool": "cdsl", "source_ref": "mw:20308.0"},
                            "display_iast": "aṣṭāṅga",
                            "display_slp1": "azwANga",
                        },
                    },
                ],
            )
        ]
    )
    ashtan_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="dico",
                subject="lex:a.s.tan",
                triples=[
                    {
                        "subject": "lex:a.s.tan",
                        "predicate": "has_sense",
                        "object": "sense:lex:a.s.tan#eight",
                        "metadata": {
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:7.html#a.s.tan:0",
                                "source_entry": {
                                    "dict": "dico",
                                    "headword_norm": "a.s.tan",
                                    "headword_roma": "aṣṭan",
                                    "source_ref": "dico:7.html#a.s.tan:0",
                                },
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:a.s.tan#eight",
                        "predicate": "gloss",
                        "object": "the number eight",
                        "metadata": {
                            "display_gloss": "the number eight",
                            "source_lang": "fr",
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:7.html#a.s.tan:0",
                                "source_lang": "fr",
                                "source_entry": {
                                    "dict": "dico",
                                    "headword_norm": "a.s.tan",
                                    "headword_roma": "aṣṭan",
                                    "source_ref": "dico:7.html#a.s.tan:0",
                                },
                            },
                        },
                    },
                ],
            )
        ]
    )
    anga_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="dico",
                subject="lex:a.nga",
                triples=[
                    {
                        "subject": "lex:a.nga_2",
                        "predicate": "has_sense",
                        "object": "sense:lex:a.nga#particle",
                        "metadata": {
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:8.html#a.nga:2",
                                "source_entry": {
                                    "dict": "dico",
                                    "headword_norm": "a.nga",
                                    "headword_roma": "aṅga",
                                },
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:a.nga#particle",
                        "predicate": "gloss",
                        "object": "aṅga_2 part. emphatic particle",
                        "metadata": {
                            "display_gloss": "aṅga_2 part. emphatic particle",
                            "source_lang": "fr",
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:8.html#a.nga:2",
                                "source_lang": "fr",
                            },
                        },
                    },
                    {
                        "subject": "lex:a.nga_1",
                        "predicate": "has_sense",
                        "object": "sense:lex:a.nga#member",
                        "metadata": {
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:8.html#a.nga:1",
                                "source_entry": {
                                    "dict": "dico",
                                    "headword_norm": "a.nga",
                                    "headword_roma": "aṅga",
                                },
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:a.nga#member",
                        "predicate": "gloss",
                        "object": "member; limb; body division",
                        "metadata": {
                            "display_gloss": "member; limb; body division",
                            "source_lang": "fr",
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:8.html#a.nga:1",
                                "source_lang": "fr",
                            },
                        },
                    },
                ],
            )
        ]
    )

    with patch(
        "langnet.cli._execute_lookup_plan",
        side_effect=[surface_result, ashtan_result, anga_result],
    ):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "ashtanga",
                "all",
                "--output",
                "json",
                "--translation-mode",
                "off",
                "--max-buckets",
                "1",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    payload = json.loads(cli_result.output)
    _assert_matches_schema(payload, ENCOUNTER_SCHEMA_PATH)
    assert payload["display"]["components"] == payload["components"]
    assert payload["display"]["meanings"][0]["display_gloss"] == (
        "consisting of eight parts or members"
    )
    assert [(component["display"], component["role"]) for component in payload["components"]] == [
        ("aṣṭan", "initial"),
        ("aṅga", "final"),
    ]
    assert payload["components"][0]["lookup_terms"] == ["aṣṭan", "aṣṭa"]
    assert payload["components"][0]["evidence"]["status"] == "linked"
    assert payload["components"][0]["evidence"]["source"] == "component_lookup"
    assert payload["components"][0]["evidence"]["lookup_tool_filter"] == "dico"
    assert (
        payload["components"][0]["evidence"]["meanings"][0]["display_gloss"] == "the number eight"
    )
    assert payload["components"][1]["evidence"]["meanings"][0]["display_gloss"] == (
        "member; limb; body division"
    )


def test_encounter_translation_mode_auto_projects_component_lookup_claims() -> None:
    surface_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="fixture",
                subject="lex:azwanga",
                triples=[
                    {
                        "subject": "form:aṣṭan",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "aṣṭan",
                            "form": "aṣṭan",
                            "analysis": "iic.",
                            "solution_number": "1",
                        },
                        "metadata": {"evidence": {"source_tool": "heritage"}},
                    },
                    {
                        "subject": "form:aṅga_1",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "aṅga_1",
                            "form": "aṅga_1",
                            "analysis": "n. sg. voc.",
                            "solution_number": "1",
                        },
                        "metadata": {"evidence": {"source_tool": "heritage"}},
                    },
                    {
                        "subject": "lex:azwanga",
                        "predicate": "has_sense",
                        "object": "sense:lex:azwanga#whole",
                        "metadata": {"evidence": {"source_tool": "cdsl"}},
                    },
                    {
                        "subject": "sense:lex:azwanga#whole",
                        "predicate": "gloss",
                        "object": "consisting of eight parts or members",
                        "metadata": {"evidence": {"source_tool": "cdsl"}},
                    },
                ],
            )
        ]
    )
    ashtan_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="dico-ashtan",
                subject="lex:a.s.tan",
                triples=[
                    {
                        "subject": "lex:a.s.tan",
                        "predicate": "has_sense",
                        "object": "sense:lex:a.s.tan#eight",
                        "metadata": {
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:7.html#a.s.tan:0",
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:a.s.tan#eight",
                        "predicate": "gloss",
                        "object": "le nombre huit",
                        "metadata": {
                            "source_lang": "fr",
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:7.html#a.s.tan:0",
                                "source_lang": "fr",
                            },
                        },
                    },
                ],
            )
        ]
    )
    anga_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="dico-anga",
                subject="lex:a.nga",
                triples=[
                    {
                        "subject": "lex:a.nga",
                        "predicate": "has_sense",
                        "object": "sense:lex:a.nga#member",
                        "metadata": {
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:8.html#a.nga:1",
                            }
                        },
                    },
                    {
                        "subject": "sense:lex:a.nga#member",
                        "predicate": "gloss",
                        "object": "membre; partie du corps",
                        "metadata": {
                            "source_lang": "fr",
                            "evidence": {
                                "source_tool": "dico",
                                "source_ref": "dico:8.html#a.nga:1",
                                "source_lang": "fr",
                            },
                        },
                    },
                ],
            )
        ]
    )
    contexts: list[str] = []

    def fake_apply_translation_cache(**kwargs):
        context = kwargs["context"]
        contexts.append(context)
        claims = deepcopy(list(kwargs["claims"]))
        display_by_context = {
            "component:aṣṭan": "eight",
            "component:aṅga": "member; body part",
        }
        display = display_by_context.get(context)
        if display is None:
            return claims
        for claim in claims:
            value = claim.get("value")
            triples = value.get("triples") if isinstance(value, dict) else None
            if not isinstance(triples, list):
                continue
            for triple in triples:
                if triple.get("predicate") != "gloss":
                    continue
                metadata = triple.setdefault("metadata", {})
                metadata["display_gloss"] = display
                metadata["source_lang"] = "en"
                evidence = metadata.setdefault("evidence", {})
                evidence["source_lang"] = "en"
        return claims

    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translations.duckdb"
        with (
            patch(
                "langnet.cli._execute_lookup_plan",
                side_effect=[surface_result, ashtan_result, anga_result],
            ),
            patch(
                "langnet.cli._encounter_apply_translation_cache",
                side_effect=fake_apply_translation_cache,
            ),
        ):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "san",
                    "ashtanga",
                    "all",
                    "--output",
                    "json",
                    "--translation-mode",
                    "auto",
                    "--translation-cache-db",
                    str(cache_path),
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    payload = json.loads(cli_result.output)
    assert contexts == ["initial", "component:aṣṭan", "component:aṅga"]
    assert payload["components"][0]["evidence"]["meanings"][0]["display_gloss"] == "eight"
    assert payload["components"][1]["evidence"]["meanings"][0]["display_gloss"] == (
        "member; body part"
    )


def test_encounter_json_returns_structured_error_on_lookup_failure() -> None:
    with patch("langnet.cli._execute_lookup_plan", side_effect=RuntimeError("backend unavailable")):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "gaffiot",
                "--output",
                "json",
                "--translation-mode",
                "off",
            ],
        )

    assert cli_result.exit_code == 1
    payload = json.loads(cli_result.output)
    _assert_matches_schema(payload, ENCOUNTER_ERROR_SCHEMA_PATH)
    assert payload == {
        "schema_version": "langnet.encounter.error.v1",
        "ok": False,
        "request": {
            "language": "lat",
            "text": "lupus",
            "tool_filter": "gaffiot",
            "normalize": True,
            "no_cache": False,
            "include_cltk": False,
            "translation_mode": "off",
        },
        "error": {
            "code": "encounter_failed",
            "type": "RuntimeError",
            "message": "backend unavailable",
        },
    }


def test_encounter_prints_compact_learner_gloss_with_evidence_line() -> None:
    triples = [
        {
            "subject": "lex:principium",
            "predicate": "has_sense",
            "object": "sense:lex:principium#1",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_53107",
                }
            },
        },
        {
            "subject": "sense:lex:principium#1",
            "predicate": "gloss",
            "object": (
                "ĭī, n. (princeps), 1 commencement : nec principium nec finem habere "
                "Cic. CM 78, n'avoir ni commencement ni fin"
            ),
            "metadata": {
                "source_lang": "fr",
                "display_gloss": (
                    "ĭī, n. (princeps), 1 commencement : nec principium nec finem habere "
                    "Cic. CM 78, n'avoir ni commencement ni fin"
                ),
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_53107",
                },
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="gaffiot", subject="lex:principium", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "principium",
                "gaffiot",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert "1. commencement\n" in cli_result.output
    assert "   evidence: ĭī, n. (princeps), 1 commencement :" in cli_result.output


def test_encounter_prints_structured_cdsl_source_notes_below_refs() -> None:
    triples = [
        {
            "subject": "lex:Darma",
            "predicate": "has_sense",
            "object": "sense:lex:Darma#notes",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:201"},
                "display_iast": "dharma",
                "display_slp1": "Darma",
            },
        },
        {
            "subject": "sense:lex:Darma#notes",
            "predicate": "gloss",
            "object": "law, duty; see Mn. ; MBh. ; religious merit",
            "metadata": {
                "display_gloss": "law, duty; see Mn. ; MBh. ; religious merit",
                "learner_gloss": "law, duty",
                "source_ref": "mw:201",
                "display_iast": "dharma",
                "display_slp1": "Darma",
                "source_notes": {
                    "cross_reference_segments": ["see Mn."],
                    "source_reference_segments": ["MBh."],
                    "recognized_abbreviations": ["Mn", "MBh"],
                },
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:201"},
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="cdsl", subject="lex:Darma", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "dharma",
                "cdsl",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n"
        "============\n"
        "Forms: dharma\n"
        "Source keys: Darma\n"
        "\n"
        "Meanings\n"
        "1. law, duty\n"
        "   evidence: law, duty; see Mn. ; MBh. ; religious merit\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "   refs: mw:201\n"
        "   source notes: cross refs: see Mn.; source refs: MBh.\n"
    )


def test_encounter_summarizes_typed_source_segments_below_refs() -> None:
    triples = [
        {
            "subject": "lex:principium",
            "predicate": "has_sense",
            "object": "sense:lex:principium#segments",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_53107",
                }
            },
        },
        {
            "subject": "sense:lex:principium#segments",
            "predicate": "gloss",
            "object": (
                "ĭī, n. (princeps), 1 beginning || principio Cic. Off. 1, 11; cf. principium; Verg."
            ),
            "metadata": {
                "source_lang": "fr",
                "display_gloss": (
                    "ĭī, n. (princeps), 1 beginning || principio Cic. Off. 1, 11; "
                    "cf. principium; Verg."
                ),
                "learner_gloss": "beginning",
                "source_ref": "gaffiot:gaffiot_53107",
                "source_segments": [
                    {
                        "raw_text": "ĭī, n. (princeps), 1 beginning",
                        "display_text": "ĭī, n. (princeps), 1 beginning",
                        "segment_type": "definition_segment",
                        "labels": ["definition"],
                    },
                    {
                        "raw_text": "principio Cic. Off. 1, 11",
                        "display_text": "principio Cic. Off. 1, 11",
                        "segment_type": "example_segment",
                        "labels": ["example", "citation", "source_reference"],
                    },
                    {
                        "raw_text": "cf. principium",
                        "display_text": "cf. principium",
                        "segment_type": "cross_reference_segment",
                        "labels": ["cross_reference", "source_reference"],
                    },
                    {
                        "raw_text": "Verg.",
                        "display_text": "Verg.",
                        "segment_type": "source_reference_segment",
                        "labels": ["source_reference"],
                    },
                ],
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_53107",
                },
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="gaffiot", subject="lex:principium", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "principium",
                "gaffiot",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "90",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert "1. beginning\n" in cli_result.output
    assert "   refs: gaffiot:gaffiot_53107\n" in cli_result.output
    assert (
        "   source notes: cross refs: cf. principium; source refs: Verg.; "
        "examples: principio Cic. Off. 1, 11\n"
    ) in cli_result.output


def test_encounter_source_details_toggle_hides_typed_source_segment_summary() -> None:
    triples = [
        {
            "subject": "lex:principium",
            "predicate": "has_sense",
            "object": "sense:lex:principium#segments",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_53107",
                }
            },
        },
        {
            "subject": "sense:lex:principium#segments",
            "predicate": "gloss",
            "object": "beginning; cf. principium",
            "metadata": {
                "display_gloss": "beginning; cf. principium",
                "learner_gloss": "beginning",
                "source_ref": "gaffiot:gaffiot_53107",
                "source_segments": [
                    {
                        "raw_text": "cf. principium",
                        "display_text": "cf. principium",
                        "segment_type": "cross_reference_segment",
                        "labels": ["cross_reference", "source_reference"],
                    },
                ],
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_53107",
                },
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="gaffiot", subject="lex:principium", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "principium",
                "gaffiot",
                "--max-buckets",
                "1",
                "--no-source-details",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert "source notes:" not in cli_result.output


def test_encounter_sorts_cdsl_buckets_by_source_order_before_gloss_text() -> None:
    early = SimpleNamespace(
        display_gloss="z later alphabetically",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                evidence={"source_tool": "cdsl", "source_ref": "mw:45268.0"},
            )
        ],
    )
    late = SimpleNamespace(
        display_gloss="a earlier alphabetically",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                evidence={"source_tool": "cdsl", "source_ref": "mw:45277.0"},
            )
        ],
    )

    assert sorted([late, early], key=_encounter_bucket_sort_key) == [early, late]


def test_encounter_sorts_cdsl_mw_before_ap90() -> None:
    mw = SimpleNamespace(
        display_gloss="mw gloss",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                evidence={"source_tool": "cdsl", "source_ref": "mw:168320.0"},
            )
        ],
    )
    ap90 = SimpleNamespace(
        display_gloss="ap90 gloss",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                evidence={"source_tool": "cdsl", "source_ref": "ap90:23529.0"},
            )
        ],
    )

    assert sorted([ap90, mw], key=_encounter_bucket_sort_key) == [mw, ap90]


def test_encounter_promotes_direct_pronoun_gloss_over_metalinguistic_cdsl_line() -> None:
    metalinguistic = SimpleNamespace(
        display_gloss="also considered by native grammarians to be the base of the cases yuṣmān",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:yuzmad",
                evidence={
                    "source_tool": "cdsl",
                    "source_ref": "mw:172214.1",
                    "display_iast": "yuṣmad",
                    "display_gloss": (
                        "also considered by native grammarians to be the base of the cases yuṣmān"
                    ),
                },
            )
        ],
    )
    learner_pronoun = SimpleNamespace(
        display_gloss="yuṣmad The base of the second personal pronoun; Thou, you",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:yuzmad",
                evidence={
                    "source_tool": "cdsl",
                    "source_ref": "ap90:23854.0",
                    "display_iast": "yuṣmad",
                    "display_gloss": "yuṣmad The base of the second personal pronoun; Thou, you",
                },
            )
        ],
    )

    assert sorted(
        [metalinguistic, learner_pronoun],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, ["yuṣmad"]),
    ) == [learner_pronoun, metalinguistic]


def test_encounter_promotes_auspicious_particle_over_sanskrit_root_entry() -> None:
    root_entry = SimpleNamespace(
        display_gloss="śam_1 v. travailler, se fatiguer; s'apaiser; être calme",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:zam",
                evidence={
                    "source_tool": "dico",
                    "source_ref": "dico:63.html#zam#1:0",
                    "display_gloss": "śam_1 v. travailler, se fatiguer; s'apaiser; être calme",
                },
            )
        ],
    )
    particle_entry = SimpleNamespace(
        display_gloss="śam_2 part. bénédiction, bonheur; bien-être",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:zam",
                evidence={
                    "source_tool": "dico",
                    "source_ref": "dico:63.html#zam#2:0",
                    "display_gloss": "śam_2 part. bénédiction, bonheur; bien-être",
                },
            )
        ],
    )

    assert sorted([root_entry, particle_entry], key=_encounter_bucket_sort_key) == [
        particle_entry,
        root_entry,
    ]


def test_encounter_sorts_whitaker_buckets_by_source_order_before_gloss_text() -> None:
    early = SimpleNamespace(
        display_gloss="z later alphabetically",
        witnesses=[
            SimpleNamespace(
                source_tool="whitaker",
                evidence={"source_tool": "whitaker", "source_order": 0},
            )
        ],
    )
    late = SimpleNamespace(
        display_gloss="a earlier alphabetically",
        witnesses=[
            SimpleNamespace(
                source_tool="whitaker",
                evidence={"source_tool": "whitaker", "source_order": 1},
            )
        ],
    )

    assert sorted([late, early], key=_encounter_bucket_sort_key) == [early, late]


def test_encounter_sorts_gaffiot_buckets_by_source_order_before_gloss_text() -> None:
    early = SimpleNamespace(
        display_gloss="z sum, esse",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_64300"},
            )
        ],
    )
    late = SimpleNamespace(
        display_gloss="a adjacent entry",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_64301"},
            )
        ],
    )

    assert sorted([late, early], key=_encounter_bucket_sort_key) == [early, late]


def test_encounter_sorts_diogenes_sense_order_before_gloss_text() -> None:
    primary = SimpleNamespace(
        display_gloss="z beginning, origin",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={"source_tool": "diogenes", "source_ref": "diogenes:00:00"},
            )
        ],
    )
    subsidiary = SimpleNamespace(
        display_gloss="a first principle",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={"source_tool": "diogenes", "source_ref": "diogenes:00:00:01:00"},
            )
        ],
    )

    assert sorted([subsidiary, primary], key=_encounter_bucket_sort_key) == [
        primary,
        subsidiary,
    ]


def test_encounter_demotes_diogenes_cross_reference_heading_below_numbered_sense() -> None:
    heading = SimpleNamespace(
        display_gloss="I. computation, reckoning (cf. λέγω (B) II).",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={
                    "source_tool": "diogenes",
                    "source_ref": "diogenes:00:00",
                    "display_gloss": "I. computation, reckoning (cf. λέγω (B) II).",
                },
            )
        ],
    )
    numbered = SimpleNamespace(
        display_gloss="1. account of money handled",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={
                    "source_tool": "diogenes",
                    "source_ref": "diogenes:00:00:00",
                    "display_gloss": "1. account of money handled",
                },
            )
        ],
    )

    assert sorted([numbered, heading], key=_encounter_bucket_sort_key) == [numbered, heading]


def test_encounter_demotes_diogenes_headword_header_below_numbered_sense() -> None:
    header = SimpleNamespace(
        display_gloss="a headword and inflectional header",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={"source_tool": "diogenes", "source_ref": "diogenes:00"},
            )
        ],
    )
    primary = SimpleNamespace(
        display_gloss="z god, the deity",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={"source_tool": "diogenes", "source_ref": "diogenes:00:00"},
            )
        ],
    )

    assert sorted([header, primary], key=_encounter_bucket_sort_key) == [primary, header]


def test_encounter_preferred_lemma_sort_overrides_source_priority() -> None:
    surface_match = SimpleNamespace(
        display_gloss="surface dictionary material",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:tva",
                evidence={"source_tool": "dico"},
            )
        ],
    )
    morphology_match = SimpleNamespace(
        display_gloss="pronoun dictionary material",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:yuzmad",
                evidence={"source_tool": "cdsl", "display_iast": "yuṣmad"},
            )
        ],
    )

    assert sorted(
        [surface_match, morphology_match],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, ["yuṣmad"]),
    ) == [morphology_match, surface_match]


def test_encounter_reduction_lemma_order_can_promote_selected_homograph() -> None:
    canus = SimpleNamespace(
        display_gloss="white, gray",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                lexeme_anchor="lex:canus",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_10263"},
            )
        ],
    )
    cano = SimpleNamespace(
        display_gloss="sing of; celebrate",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                lexeme_anchor="lex:cano",
                evidence={"source_tool": "diogenes", "source_ref": "diogenes:00:00"},
            )
        ],
    )

    assert sorted(
        [canus, cano],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, ["cano", "canus"]),
    ) == [cano, canus]


def test_encounter_preferred_lemma_sort_preserves_analysis_order() -> None:
    first_analysis = SimpleNamespace(
        display_gloss="principium noun evidence",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                lexeme_anchor="lex:principium",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_53107"},
            )
        ],
    )
    second_analysis = SimpleNamespace(
        display_gloss="principio verb evidence",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                lexeme_anchor="lex:principio",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_53106"},
            )
        ],
    )
    morphology_rows = [
        {
            "source_tool": "whitaker",
            "form": "principio",
            "lemma": "principium",
            "analysis": "noun; dative; singular; neuter; ablative",
        },
        {
            "source_tool": "whitaker",
            "form": "principio",
            "lemma": "principio",
            "analysis": "verb; present; active; indicative",
        },
    ]

    preferred = _encounter_preferred_lemmas_from_morphology(morphology_rows)

    assert sorted(
        [second_analysis, first_analysis],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred),
    ) == [first_analysis, second_analysis]


def test_encounter_combined_preferred_lemmas_use_morphology_before_reduction_order() -> None:
    reduction = SimpleNamespace(
        lexeme_anchors=["lex:principio", "lex:principium"],
        buckets=[],
    )
    morphology_rows = [
        {
            "source_tool": "whitaker",
            "form": "principio",
            "lemma": "principio",
            "analysis": "verb; present; active; indicative",
        },
        {
            "source_tool": "whitaker",
            "form": "principio",
            "lemma": "principium",
            "analysis": "noun; dative; singular; neuter; ablative",
        },
    ]

    assert _encounter_preferred_lemmas_for_sorting(reduction, morphology_rows) == [
        "principium",
        "principio",
    ]


def test_encounter_preferred_lemma_rank_keeps_base_lemma_before_tagged_variant() -> None:
    principium = SimpleNamespace(
        display_gloss="commencement",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                lexeme_anchor="lex:principium",
                evidence={"source_tool": "gaffiot"},
            )
        ],
    )
    principio = SimpleNamespace(
        display_gloss="begin to speak",
        witnesses=[
            SimpleNamespace(
                source_tool="whitaker",
                lexeme_anchor="lex:principio#verb",
                evidence={"source_tool": "whitaker"},
            )
        ],
    )
    preferred = ["principium", "principio", "principio#verb", "principium#noun"]

    assert sorted(
        [principio, principium],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred),
    ) == [principium, principio]


def test_encounter_strong_learner_gloss_can_promote_common_verb_homograph() -> None:
    adjective = SimpleNamespace(
        display_gloss="white, gray",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                lexeme_anchor="lex:canus",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_10263"},
            )
        ],
    )
    verb = SimpleNamespace(
        display_gloss="sing of; celebrate",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                lexeme_anchor="lex:cano",
                evidence={
                    "source_tool": "diogenes",
                    "source_ref": "diogenes:00:00",
                    "display_gloss": "sing of; celebrate",
                },
            )
        ],
    )
    preferred = ["canus", "canum", "cano"]

    assert sorted(
        [adjective, verb],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred),
    ) == [verb, adjective]


def test_encounter_preferred_lemma_sort_demotes_tackon_before_content_word() -> None:
    tackon_bucket = SimpleNamespace(
        display_gloss="-que = and",
        witnesses=[
            SimpleNamespace(
                source_tool="whitaker",
                lexeme_anchor="lex:que#tackon",
                evidence={"source_tool": "whitaker"},
            )
        ],
    )
    content_bucket = SimpleNamespace(
        display_gloss="man; hero",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                lexeme_anchor="lex:vir",
                evidence={"source_tool": "gaffiot"},
            )
        ],
    )
    surface_homograph_bucket = SimpleNamespace(
        display_gloss="virus",
        witnesses=[
            SimpleNamespace(
                source_tool="whitaker",
                lexeme_anchor="lex:virum#noun",
                evidence={"source_tool": "whitaker"},
            )
        ],
    )
    morphology_rows = [
        {
            "source_tool": "whitaker",
            "form": "que",
            "lemma": "que",
            "analysis": "tackon",
        },
        {
            "source_tool": "whitaker",
            "form": "virum",
            "lemma": "virum",
            "analysis": "noun; declension 2; nominative; singular; neuter; accusative",
        },
        {
            "source_tool": "whitaker",
            "form": "virum",
            "lemma": "vir",
            "analysis": "noun; declension 2; accusative; singular; masculine",
        },
    ]

    preferred = _encounter_preferred_lemmas_from_morphology(morphology_rows)

    assert preferred == ["vir", "virum", "que"]
    assert sorted(
        [tackon_bucket, surface_homograph_bucket, content_bucket],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, preferred),
    ) == [content_bucket, surface_homograph_bucket, tackon_bucket]


def test_encounter_preferred_lemma_sort_matches_sanskrit_transliteration_variants() -> None:
    dico_bucket = SimpleNamespace(
        display_gloss="DICO Varuna material",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:varu.na",
                evidence={"source_tool": "dico"},
            )
        ],
    )
    cdsl_bucket = SimpleNamespace(
        display_gloss="CDSL Varuna material",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:varuRa",
                evidence={"source_tool": "cdsl", "display_iast": "varuṇa"},
            )
        ],
    )

    assert sorted(
        [cdsl_bucket, dico_bucket],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, ["varuṇa"]),
    ) == [cdsl_bucket, dico_bucket]


def test_encounter_sort_prefers_exact_source_headword_deva() -> None:
    near_bucket = SimpleNamespace(
        display_gloss="puraṇa [obj. pṝ ] m. océan.",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:pura.na",
                evidence={
                    "source_tool": "dico",
                    "source_entry": {"headword_deva": "पुरण", "headword_norm": "pura.na"},
                },
            )
        ],
    )
    exact_bucket = SimpleNamespace(
        display_gloss="purāṇa old; ancient tale",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:puraa.na",
                evidence={
                    "source_tool": "dico",
                    "source_entry": {"headword_deva": "पुराण", "headword_norm": "puraa.na"},
                },
            )
        ],
    )

    assert sorted(
        [near_bucket, exact_bucket],
        key=lambda bucket: _encounter_bucket_sort_key(bucket, ["पुराण"]),
    ) == [exact_bucket, near_bucket]


def test_encounter_sanskrit_heritage_analysis_snapshot() -> None:
    triples = [
        {
            "subject": "form:dharma",
            "predicate": "has_morphology",
            "object": {
                "lemma": "dharma",
                "form": "dharma",
                "analysis": "m. sg. voc.",
                "dictionary_url": "https://sanskrit.inria.fr/DICO/34.html#dharma",
            },
            "metadata": {
                "evidence": {"source_tool": "heritage", "raw_blob_ref": "raw_html"},
            },
        }
    ]
    result = SimpleNamespace(
        claims=[
            ClaimEffect(
                claim_id="clm-heritage",
                tool="claim.heritage.morph",
                call_id="call-heritage",
                source_call_id="derive-heritage",
                derivation_id="drv-heritage",
                subject="lex:dharma",
                predicate="has_morphology",
                value={"triples": triples},
                provenance_chain=[],
                handler_version="test",
            )
        ]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "dharma",
                "heritage",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n============\n\nAnalysis\n"
        "- dharma -> dharma: m. sg. voc. "
        "[Foster: Calling Function; Single; Male] (heritage)\n"
    )


def test_encounter_follows_sanskrit_morphology_lemma_when_surface_has_no_meanings() -> None:
    morphology_result = SimpleNamespace(
        claims=[
            ClaimEffect(
                claim_id="clm-heritage",
                tool="claim.heritage.morph",
                call_id="call-heritage",
                source_call_id="derive-heritage",
                derivation_id="drv-heritage",
                subject="lex:yuyutsava",
                predicate="has_morphology",
                value={
                    "triples": [
                        {
                            "subject": "form:yuyutsava",
                            "predicate": "has_morphology",
                            "object": {
                                "lemma": "yuyutsava",
                                "form": "yuyutsava",
                                "analysis": "?",
                            },
                            "metadata": {"evidence": {"source_tool": "heritage"}},
                        },
                        {
                            "subject": "form:yuyutsu",
                            "predicate": "has_morphology",
                            "object": {
                                "lemma": "yuyutsu",
                                "form": "yuyutsu",
                                "analysis": "m. pl. voc.",
                            },
                            "metadata": {"evidence": {"source_tool": "heritage"}},
                        },
                    ]
                },
                provenance_chain=[],
                handler_version="test",
            )
        ]
    )
    sense_triples = [
        {
            "subject": "lex:yuyutsu",
            "predicate": "has_sense",
            "object": "sense:lex:yuyutsu#1",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:yuyutsu"},
                "display_iast": "yuyutsu",
                "display_slp1": "yuyutsu",
            },
        },
        {
            "subject": "sense:lex:yuyutsu#1",
            "predicate": "gloss",
            "object": "desiring to fight",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:yuyutsu"},
                "display_iast": "yuyutsu",
                "display_slp1": "yuyutsu",
            },
        },
    ]
    lemma_result = SimpleNamespace(
        claims=[_claim_with_triples(tool="cdsl", subject="lex:yuyutsu", triples=sense_triples)]
    )

    with patch(
        "langnet.cli._execute_lookup_plan",
        side_effect=[morphology_result, lemma_result],
    ):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "yuyutsavaḥ",
                "all",
                "--no-cache",
                "--max-buckets",
                "1",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "yuyutsavaḥ [san]\n"
        "================\n"
        "Forms: yuyutsu\n"
        "Warning: No sense buckets for surface form; followed Sanskrit morphology lemma "
        "for meaning evidence.\n"
        "\n"
        "Analysis\n"
        "- yuyutsu -> yuyutsu: m. pl. voc. "
        "[Foster: Calling Function; Group; Male] (heritage)\n"
        "\n"
        "Meanings\n"
        "1. desiring to fight\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "   refs: mw:yuyutsu\n"
    ), cli_result.output


def test_encounter_enriches_sanskrit_surface_with_clear_morphology_lemma() -> None:
    surface_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="fixture",
                subject="lex:karma",
                triples=[
                    {
                        "subject": "form:karman",
                        "predicate": "has_morphology",
                        "object": {
                            "lemma": "karman",
                            "form": "karman",
                            "analysis": "n. sg. acc. | n. sg. nom.",
                        },
                        "metadata": {"evidence": {"source_tool": "heritage"}},
                    },
                    {
                        "subject": "lex:karma",
                        "predicate": "has_sense",
                        "object": "sense:lex:karma#compound",
                        "metadata": {"evidence": {"source_tool": "cdsl"}},
                    },
                    {
                        "subject": "sense:lex:karma#compound",
                        "predicate": "gloss",
                        "object": "karma (in comp. for karman above).",
                        "metadata": {"evidence": {"source_tool": "cdsl"}},
                    },
                ],
            )
        ]
    )
    lemma_result = SimpleNamespace(
        claims=[
            _claim_with_triples(
                tool="fixture",
                subject="lex:karman",
                triples=[
                    {
                        "subject": "lex:karman",
                        "predicate": "has_sense",
                        "object": "sense:lex:karman#action",
                        "metadata": {"evidence": {"source_tool": "cdsl"}},
                    },
                    {
                        "subject": "sense:lex:karman#action",
                        "predicate": "gloss",
                        "object": "act, action, duty, rite",
                        "metadata": {"evidence": {"source_tool": "cdsl"}},
                    },
                ],
            )
        ]
    )

    with patch("langnet.cli._execute_lookup_plan", side_effect=[surface_result, lemma_result]):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "karma",
                "all",
                "--translation-mode",
                "off",
                "--max-buckets",
                "2",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "karma [san]\n"
        "===========\n"
        "Forms: karman, karma\n"
        "Warning: Followed Sanskrit morphology lemma for additional meaning evidence.\n"
        "\n"
        "Analysis\n"
        "- karman -> karman: n. sg. acc. | n. sg. nom. "
        "[Foster: Receiving Function; Single; Neuter / Naming Function; Single; Neuter] "
        "(heritage)\n"
        "\n"
        "Meanings\n"
        "1. act, action, duty, rite\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "2. karma (in comp. for karman above).\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
    ), cli_result.output


def test_encounter_retries_uncached_when_cached_normalization_has_no_senses() -> None:
    stale_result = SimpleNamespace(
        claims=[
            ClaimEffect(
                claim_id="clm-heritage",
                tool="claim.heritage.morph",
                call_id="call-heritage",
                source_call_id="derive-heritage",
                derivation_id="drv-heritage",
                subject="lex:nirudha",
                predicate="has_morphology",
                value={
                    "triples": [
                        {
                            "subject": "form:nirudha",
                            "predicate": "has_morphology",
                            "object": {
                                "lemma": "nirudha",
                                "form": "nirudha",
                                "analysis": "?",
                            },
                            "metadata": {
                                "evidence": {"source_tool": "heritage"},
                            },
                        }
                    ]
                },
                provenance_chain=[],
                handler_version="test",
            )
        ]
    )
    recovered_triples = [
        {
            "subject": "lex:niruqa",
            "predicate": "has_sense",
            "object": "sense:lex:niruqa#purged",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:109472.0"},
                "display_iast": "nirūḍha",
                "display_slp1": "nirUQa",
            },
        },
        {
            "subject": "sense:lex:niruqa#purged",
            "predicate": "gloss",
            "object": "purged",
            "metadata": {
                "evidence": {"source_tool": "cdsl", "source_ref": "mw:109472.0"},
                "display_iast": "nirūḍha",
                "display_slp1": "nirUQa",
            },
        },
    ]
    recovered_result = SimpleNamespace(
        claims=[_claim_with_triples(tool="cdsl", subject="lex:niruqa", triples=recovered_triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", side_effect=[stale_result, recovered_result]):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "san",
                "nirudha",
                "--max-buckets",
                "1",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "nirudha [san]\n"
        "=============\n"
        "Forms: nirūḍha\n"
        "Source keys: nirUQa\n"
        "Warning: Cached normalization produced no sense buckets; retried with fresh "
        "normalization.\n"
        "\n"
        "Meanings\n"
        "1. purged\n"
        "   sources: cdsl; witnesses: 1; confidence: single-witness\n"
        "   refs: mw:109472.0\n"
    )


def test_encounter_latin_source_language_snapshot() -> None:
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#1",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:lupus",
                    "source_lang": "fr",
                }
            },
        },
        {
            "subject": "sense:lex:lupus#1",
            "predicate": "gloss",
            "object": "loup",
            "metadata": {
                "evidence": {
                    "source_tool": "gaffiot",
                    "source_ref": "gaffiot:lupus",
                    "source_lang": "fr",
                }
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "gaffiot",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. loup\n"
        "   sources: gaffiot; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:lupus\n"
        "   source language: fr\n"
    )


def test_encounter_latin_translation_cache_snapshot() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        key = build_translation_key(
            source_lexicon="gaffiot",
            entry_id="gaffiot_38776",
            occurrence=1,
            headword_norm="lupus",
            source_text="loup",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("lat")),
        )
        conn = duckdb.connect(str(cache_path))
        try:
            TranslationCache(conn).upsert(
                TranslationRecord(
                    key=key,
                    translated_text="wolf",
                    status="ok",
                    duration_ms=5,
                )
            )
        finally:
            conn.close()

        triples = [
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
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
        )

        with patch("langnet.cli._execute_lookup_plan", return_value=result):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "lat",
                    "lupus",
                    "gaffiot",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--max-buckets",
                    "2",
                    "--max-gloss-chars",
                    "80",
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. wolf\n"
        "   sources: translation; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:gaffiot_38776\n"
        "   translated from: gaffiot\n"
        "   source language: en\n"
        "2. loup\n"
        "   sources: gaffiot; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:gaffiot_38776\n"
        "   source language: fr\n"
    )


def test_encounter_translation_mode_off_ignores_default_cache_hits() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        key = build_translation_key(
            source_lexicon="gaffiot",
            entry_id="gaffiot_38776",
            occurrence=1,
            headword_norm="lupus",
            source_text="loup",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("lat")),
        )
        conn = duckdb.connect(str(cache_path))
        try:
            TranslationCache(conn).upsert(
                TranslationRecord(
                    key=key,
                    translated_text="wolf",
                    status="ok",
                    duration_ms=5,
                )
            )
        finally:
            conn.close()

        triples = [
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
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
        )

        with patch("langnet.cli._execute_lookup_plan", return_value=result):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "lat",
                    "lupus",
                    "gaffiot",
                    "--translation-mode",
                    "off",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--max-buckets",
                    "1",
                    "--max-gloss-chars",
                    "80",
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    assert "1. loup\n" in cli_result.output
    assert "wolf" not in cli_result.output
    assert "translated from:" not in cli_result.output


def test_translation_warm_populates_wordlist_cache() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        wordlist = Path(tmpdir) / "words.txt"
        wordlist.write_text("lupus\n", encoding="utf-8")
        triples = [
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
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
        )

        with (
            patch("langnet.cli._execute_lookup_plan", return_value=result),
            patch("langnet.cli._encounter_translation_callback", return_value=lambda _: "wolf"),
        ):
            cli_result = CliRunner().invoke(
                main,
                [
                    "translation-warm",
                    "lat",
                    str(wordlist),
                    "--tool-filter",
                    "gaffiot",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--output",
                    "json",
                ],
            )

        assert cli_result.exit_code == 0, cli_result.output
        payload = json.loads(cli_result.output)
        assert payload["summary"]["terms"] == 1
        assert payload["summary"]["before_missing"] == 1
        assert payload["summary"]["written"] == 1
        assert payload["summary"]["after_hits"] == 1

        key = build_translation_key(
            source_lexicon="gaffiot",
            entry_id="gaffiot_38776",
            occurrence=1,
            headword_norm="lupus",
            source_text="loup",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("lat")),
        )
        conn = duckdb.connect(str(cache_path), read_only=True)
        try:
            record = TranslationCache(conn, read_only=True).get(key)
        finally:
            conn.close()
        assert record is not None
        assert record.translated_text == "wolf"


def test_encounter_translation_mode_auto_populates_missing_cache() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        triples = [
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
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="gaffiot", subject="lex:lupus", triples=triples)]
        )

        with (
            patch("langnet.cli._execute_lookup_plan", return_value=result),
            patch(
                "langnet.cli._openrouter_translation_callback",
                return_value=lambda projection: "wolf",
            ),
        ):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "lat",
                    "lupus",
                    "gaffiot",
                    "--translation-mode",
                    "auto",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--max-buckets",
                    "1",
                    "--max-gloss-chars",
                    "80",
                ],
            )

        assert cli_result.exit_code == 0, cli_result.output
        assert "1. wolf\n" in cli_result.output
        assert "translated from: gaffiot\n" in cli_result.output

        key = build_translation_key(
            source_lexicon="gaffiot",
            entry_id="gaffiot_38776",
            occurrence=1,
            headword_norm="lupus",
            source_text="loup",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("lat")),
        )
        conn = duckdb.connect(str(cache_path), read_only=True)
        try:
            record = TranslationCache(conn, read_only=True).get(key)
        finally:
            conn.close()
        assert record is not None
        assert record.translated_text == "wolf"
        assert record.status == "ok"


def test_encounter_sanskrit_dico_translation_cache_snapshot() -> None:
    model = "test:model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        key = build_translation_key(
            source_lexicon="dico",
            entry_id="dharma",
            occurrence=0,
            headword_norm="dharma",
            source_text="loi, devoir, vertu",
            model=model,
            prompt=BASE_SYSTEM,
            hint="\n".join(default_hints_for_language("san")),
        )
        conn = duckdb.connect(str(cache_path))
        try:
            TranslationCache(conn).upsert(
                TranslationRecord(
                    key=key,
                    translated_text="law, duty, virtue",
                    status="ok",
                    duration_ms=5,
                )
            )
        finally:
            conn.close()

        triples = [
            {
                "subject": "lex:dharma",
                "predicate": "has_sense",
                "object": "sense:lex:dharma#dico",
                "metadata": {
                    "evidence": {
                        "source_tool": "dico",
                        "source_ref": "dico:34.html#dharma:0",
                    }
                },
            },
            {
                "subject": "sense:lex:dharma#dico",
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
        result = SimpleNamespace(
            claims=[_claim_with_triples(tool="dico", subject="lex:dharma", triples=triples)]
        )

        with patch("langnet.cli._execute_lookup_plan", return_value=result):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    "san",
                    "dharma",
                    "dico",
                    "--use-translation-cache",
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--max-buckets",
                    "2",
                    "--max-gloss-chars",
                    "80",
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "dharma [san]\n"
        "============\n"
        "Forms: dharma\n"
        "\n"
        "Meanings\n"
        "1. law, duty, virtue\n"
        "   sources: translation; witnesses: 1; confidence: single-witness\n"
        "   refs: dico:34.html#dharma:0\n"
        "   translated from: dico\n"
        "   source language: en\n"
        "2. loi, devoir, vertu\n"
        "   sources: dico; witnesses: 1; confidence: single-witness\n"
        "   refs: dico:34.html#dharma:0\n"
        "   source language: fr\n"
    )


def test_encounter_json_projects_all_translation_golden_rows() -> None:
    fixture = json.loads(TRANSLATION_FIXTURE_PATH.read_text())
    rows = list(fixture["rows"])
    model = str(fixture["model"])
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        _write_translation_cache_from_rows(cache_path=cache_path, rows=rows, model=model)

        for row in rows:
            source_lexicon = str(row["source_lexicon"])
            language = _translation_language(source_lexicon)
            result = SimpleNamespace(claims=[_claim_from_translation_row(row)])

            with patch("langnet.cli._execute_lookup_plan", return_value=result):
                cli_result = CliRunner().invoke(
                    main,
                    [
                        "encounter",
                        language,
                        str(row["headword_norm"]),
                        source_lexicon,
                        "--use-translation-cache",
                        "--translation-cache-db",
                        str(cache_path),
                        "--translation-model",
                        model,
                        "--output",
                        "json",
                    ],
                )

            assert cli_result.exit_code == 0, cli_result.output
            payload = json.loads(cli_result.output)
            _assert_matches_schema(payload, ENCOUNTER_SCHEMA_PATH)
            translated_buckets = [
                bucket
                for bucket in payload["buckets"]
                if bucket["display_gloss"] == row["translated_text"]
            ]
            assert len(translated_buckets) == 1
            translated_witness = translated_buckets[0]["witnesses"][0]
            assert translated_witness["source_tool"] == "translation"
            assert translated_witness["evidence"]["source_lexicon"] == source_lexicon
            assert translated_witness["evidence"]["source_ref"] == row["source_ref"]
            assert translated_witness["evidence"]["parsed_glosses"]
            assert payload["translation_cache"]["cache_available"] is True
            assert payload["translation_cache"]["before"] == {
                "total": 1,
                "hits": 1,
                "missing": 0,
                "errors": 0,
                "empty": 0,
            }
            assert payload["translation_cache"]["after"] == {
                "total": 1,
                "hits": 1,
                "missing": 0,
                "errors": 0,
                "empty": 0,
            }
            assert payload["translation_cache"]["written"] == 0


def test_encounter_json_reports_translation_cache_miss() -> None:
    fixture = json.loads(TRANSLATION_FIXTURE_PATH.read_text())
    row = fixture["rows"][0]
    model = str(fixture["model"])
    source_lexicon = str(row["source_lexicon"])
    language = _translation_language(source_lexicon)
    result = SimpleNamespace(claims=[_claim_from_translation_row(row)])
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "translation.duckdb"
        conn = duckdb.connect(str(cache_path))
        conn.close()

        with patch("langnet.cli._execute_lookup_plan", return_value=result):
            cli_result = CliRunner().invoke(
                main,
                [
                    "encounter",
                    language,
                    str(row["headword_norm"]),
                    source_lexicon,
                    "--translation-cache-db",
                    str(cache_path),
                    "--translation-model",
                    model,
                    "--output",
                    "json",
                ],
            )

    assert cli_result.exit_code == 0, cli_result.output
    payload = json.loads(cli_result.output)
    assert payload["translation_cache"]["cache_available"] is True
    assert payload["translation_cache"]["before"] == {
        "total": 1,
        "hits": 0,
        "missing": 1,
        "errors": 0,
        "empty": 0,
    }
    assert payload["translation_cache"]["after"] == {
        "total": 1,
        "hits": 0,
        "missing": 1,
        "errors": 0,
        "empty": 0,
    }
    assert payload["translation_cache"]["written"] == 0


def test_encounter_prefers_multi_witness_bucket_snapshot() -> None:
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#apple",
            "metadata": {"evidence": {"source_tool": "fixture", "source_ref": "fixture:apple"}},
        },
        {
            "subject": "sense:lex:lupus#apple",
            "predicate": "gloss",
            "object": "apple",
            "metadata": {"evidence": {"source_tool": "fixture", "source_ref": "fixture:apple"}},
        },
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#wolf-a",
            "metadata": {"evidence": {"source_tool": "whitaker", "source_ref": "whitaker:lupus"}},
        },
        {
            "subject": "sense:lex:lupus#wolf-a",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {"evidence": {"source_tool": "whitaker", "source_ref": "whitaker:lupus"}},
        },
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#wolf-b",
            "metadata": {"evidence": {"source_tool": "diogenes", "source_ref": "ls:6387"}},
        },
        {
            "subject": "sense:lex:lupus#wolf-b",
            "predicate": "gloss",
            "object": "wolf",
            "metadata": {"evidence": {"source_tool": "diogenes", "source_ref": "ls:6387"}},
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="latin", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "all",
                "--max-buckets",
                "2",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. wolf\n"
        "   sources: diogenes, whitaker; witnesses: 2; confidence: multi-witness\n"
        "   refs: whitaker:lupus, ls:6387\n"
        "2. apple\n"
        "   sources: fixture; witnesses: 1; confidence: single-witness\n"
        "   refs: fixture:apple\n"
    )


def test_encounter_prefers_bilingual_source_bucket_snapshot() -> None:
    triples = [
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#generic",
            "metadata": {"evidence": {"source_tool": "fixture", "source_ref": "fixture:generic"}},
        },
        {
            "subject": "sense:lex:lupus#generic",
            "predicate": "gloss",
            "object": "generic animal",
            "metadata": {"evidence": {"source_tool": "fixture", "source_ref": "fixture:generic"}},
        },
        {
            "subject": "lex:lupus",
            "predicate": "has_sense",
            "object": "sense:lex:lupus#gaffiot",
            "metadata": {
                "evidence": {"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_38776"}
            },
        },
        {
            "subject": "sense:lex:lupus#gaffiot",
            "predicate": "gloss",
            "object": "loup",
            "metadata": {
                "source_lang": "fr",
                "source_ref": "gaffiot:gaffiot_38776",
                "evidence": {"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_38776"},
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="latin", subject="lex:lupus", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "lat",
                "lupus",
                "all",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "lupus [lat]\n"
        "===========\n"
        "Forms: lupus\n"
        "\n"
        "Meanings\n"
        "1. loup\n"
        "   sources: gaffiot; witnesses: 1; confidence: single-witness\n"
        "   refs: gaffiot:gaffiot_38776\n"
        "   source language: fr\n"
        "\n"
        "(1 more bucket(s) hidden)\n"
    )


def test_encounter_greek_learner_output_snapshot() -> None:
    triples = [
        {
            "subject": "lex:λόγος",
            "predicate": "has_sense",
            "object": "sense:lex:λόγος#1",
            "metadata": {
                "evidence": {
                    "source_tool": "diogenes",
                    "source_ref": "lsj:logos",
                }
            },
        },
        {
            "subject": "sense:lex:λόγος#1",
            "predicate": "gloss",
            "object": "word; speech; account; reason",
            "metadata": {
                "evidence": {
                    "source_tool": "diogenes",
                    "source_ref": "lsj:logos",
                }
            },
        },
    ]
    result = SimpleNamespace(
        claims=[_claim_with_triples(tool="diogenes", subject="lex:λόγος", triples=triples)]
    )

    with patch("langnet.cli._execute_lookup_plan", return_value=result):
        cli_result = CliRunner().invoke(
            main,
            [
                "encounter",
                "grc",
                "λόγος",
                "diogenes",
                "--max-buckets",
                "1",
                "--max-gloss-chars",
                "80",
            ],
        )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.output == (
        "λόγος [grc]\n"
        "===========\n"
        "Forms: λόγος\n"
        "\n"
        "Meanings\n"
        "1. word; speech; account; reason\n"
        "   sources: diogenes; witnesses: 1; confidence: single-witness\n"
        "   refs: lsj:logos\n"
    )
