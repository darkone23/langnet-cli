from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import duckdb
from click.testing import CliRunner
from query_spec import CanonicalCandidate, NormalizedQuery

from langnet.cli import (
    LanguageHint,
    NormalizeConfig,
    _encounter_bucket_sort_key,
    _encounter_compact_gloss,
    _encounter_foster_display,
    _encounter_lemma_compare_keys,
    _encounter_morphology_fallback_terms,
    _encounter_morphology_rows,
    _encounter_preferred_lemmas_from_morphology,
    _get_query_value_for_plan,
    main,
)
from langnet.execution.effects import ClaimEffect, ProvenanceLink
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    TranslationRecord,
    build_translation_key,
    default_hints_for_language,
)

TRANSLATION_FIXTURE_PATH = Path("tests/fixtures/translation_cache_golden_rows.json")


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
    ) == [dico_bucket, cdsl_bucket]


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
