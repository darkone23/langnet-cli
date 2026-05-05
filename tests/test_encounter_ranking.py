from __future__ import annotations

from types import SimpleNamespace

from langnet.encounter_ranking import (
    bucket_ranking_explanation,
    bucket_sort_key,
    cdsl_dictionary_order,
    cdsl_source_order,
    diogenes_source_order,
    gaffiot_source_order,
    generic_source_order,
    lemma_compare_keys,
    preferred_lemma_rank,
    preferred_lemmas_for_sorting,
    preferred_lemmas_from_morphology,
)

CDSL_SOURCE_ORDER = 45268
GAFFIOT_SOURCE_ORDER = 64300
WHITAKER_SOURCE_ORDER = 3


def test_lemma_compare_keys_include_pos_anchor_base() -> None:
    assert "armum" in lemma_compare_keys("armum#noun")


def test_lemma_compare_keys_match_sanskrit_slp1_vocalic_r_and_visarga() -> None:
    assert lemma_compare_keys("pravṛtti") & lemma_compare_keys("pravftti")
    assert lemma_compare_keys("pravṛtti") & lemma_compare_keys("pravṛttiḥ")
    assert lemma_compare_keys("niyama") & lemma_compare_keys("niyamaḥ")
    assert lemma_compare_keys("niyama") & lemma_compare_keys("niyamah")


def test_preferred_lemmas_from_morphology_demotes_tackon_rows() -> None:
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
            "analysis": "noun; nominative; singular; neuter; accusative",
        },
        {
            "source_tool": "whitaker",
            "form": "virum",
            "lemma": "vir",
            "analysis": "noun; accusative; singular; masculine",
        },
    ]

    assert preferred_lemmas_from_morphology(morphology_rows) == ["vir", "virum", "que"]


def test_preferred_lemmas_for_sorting_uses_morphology_before_reduction_order() -> None:
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

    assert preferred_lemmas_for_sorting(reduction, morphology_rows) == [
        "principium",
        "principio",
    ]


def test_preferred_lemma_rank_matches_sanskrit_transliteration_variants() -> None:
    bucket = SimpleNamespace(
        display_gloss="CDSL Varuna material",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:varuRa",
                evidence={"source_tool": "cdsl", "display_iast": "varuṇa"},
            )
        ],
    )

    assert preferred_lemma_rank(bucket, ["varuṇa"]) == 0


def test_source_order_helpers_extract_source_specific_ordering() -> None:
    cdsl = SimpleNamespace(
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                evidence={"source_tool": "cdsl", "source_ref": "mw:45268.0"},
            )
        ]
    )
    ap90 = SimpleNamespace(
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                evidence={"source_tool": "cdsl", "source_ref": "ap90:23529.0"},
            )
        ]
    )
    gaffiot = SimpleNamespace(
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                evidence={"source_tool": "gaffiot", "source_ref": "gaffiot:gaffiot_64300"},
            )
        ]
    )
    whitaker = SimpleNamespace(
        witnesses=[
            SimpleNamespace(
                source_tool="whitaker",
                evidence={"source_tool": "whitaker", "source_order": "3"},
            )
        ]
    )
    diogenes = SimpleNamespace(
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                evidence={"source_tool": "diogenes", "source_ref": "diogenes:00:00:01:00"},
            )
        ]
    )

    assert cdsl_source_order(cdsl) == CDSL_SOURCE_ORDER
    assert cdsl_dictionary_order(cdsl) == 0
    assert cdsl_dictionary_order(ap90) == 1
    assert gaffiot_source_order(gaffiot) == GAFFIOT_SOURCE_ORDER
    assert generic_source_order(whitaker, "whitaker") == WHITAKER_SOURCE_ORDER
    assert diogenes_source_order(diogenes) == (0, 0, 1, 0)


def test_bucket_sort_key_combines_source_order_and_quality_policy() -> None:
    heading = SimpleNamespace(
        display_gloss="I. computation, reckoning (cf. λέγω (B) II).",
        witnesses=[
            SimpleNamespace(
                source_tool="diogenes",
                lexeme_anchor="lex:logos",
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
                lexeme_anchor="lex:logos",
                evidence={
                    "source_tool": "diogenes",
                    "source_ref": "diogenes:00:00:00",
                    "display_gloss": "1. account of money handled",
                },
            )
        ],
    )

    assert sorted([numbered, heading], key=bucket_sort_key) == [numbered, heading]


def test_bucket_sort_key_prefers_source_english_over_untranslated_dico() -> None:
    dico = SimpleNamespace(
        display_gloss="niyama discipline morale",
        witnesses=[
            SimpleNamespace(
                source_tool="dico",
                lexeme_anchor="lex:niyama",
                evidence={
                    "source_tool": "dico",
                    "source_lang": "fr",
                    "source_entry": {"headword_norm": "niyama"},
                },
            )
        ],
    )
    cdsl = SimpleNamespace(
        display_gloss="restraint of the mind",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:niyama",
                evidence={
                    "source_tool": "cdsl",
                    "display_iast": "niyama",
                    "source_ref": "mw:109142.0",
                },
            )
        ],
    )

    assert sorted([dico, cdsl], key=lambda bucket: bucket_sort_key(bucket, ["niyama"])) == [
        cdsl,
        dico,
    ]


def test_bucket_sort_key_demotes_bare_cross_reference_senses() -> None:
    cross_ref = SimpleNamespace(
        display_gloss="1. iṣa mfn. seeking (see gav-iṣa ).",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:iza",
                evidence={
                    "source_tool": "cdsl",
                    "display_iast": "iṣa",
                    "source_ref": "mw:29541.0",
                },
            )
        ],
    )
    definition = SimpleNamespace(
        display_gloss="2. iṣa mfn. possessing sap and strength",
        witnesses=[
            SimpleNamespace(
                source_tool="cdsl",
                lexeme_anchor="lex:iza",
                evidence={
                    "source_tool": "cdsl",
                    "display_iast": "iṣa",
                    "source_ref": "mw:29598.0",
                },
            )
        ],
    )

    assert sorted(
        [cross_ref, definition],
        key=lambda bucket: bucket_sort_key(bucket, ["iṣa"]),
    ) == [definition, cross_ref]


def test_bucket_ranking_explanation_reports_sort_factors_and_reasons() -> None:
    bucket = SimpleNamespace(
        bucket_id="bucket-wolf",
        display_gloss="wolf",
        witnesses=[
            SimpleNamespace(
                source_tool="translation",
                lexeme_anchor="lex:lupus",
                evidence={
                    "source_tool": "translation",
                    "source_lang": "en",
                    "source_lexicon": "gaffiot",
                    "source_ref": "gaffiot:gaffiot_38776",
                },
            )
        ],
    )

    explanation = bucket_ranking_explanation(bucket, ["lupus"])

    assert explanation.bucket_id == "bucket-wolf"
    assert explanation.display_gloss == "wolf"
    assert explanation.preferred_lemma_rank == 0
    assert explanation.has_english_translation is True
    assert "matches preferred morphology/reduction lemma" in explanation.reasons
    assert "has English translation evidence" in explanation.reasons
    assert "sources: translation" in explanation.reasons
