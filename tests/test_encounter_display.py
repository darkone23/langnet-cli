from __future__ import annotations

from types import SimpleNamespace

from langnet.encounter_display import (
    build_analysis_views,
    build_display_payload,
    build_header_view,
    build_meaning_view,
    foster_display_for_analysis,
    summarize_source_details,
)


def test_build_header_view_prefers_display_forms_and_separates_source_keys() -> None:
    reduction = SimpleNamespace(
        lexeme_anchors=["lex:Darma"],
        buckets=[
            SimpleNamespace(
                witnesses=[
                    SimpleNamespace(
                        lexeme_anchor="lex:Darma",
                        evidence={"display_iast": "dharma", "display_slp1": "Darma"},
                    ),
                    SimpleNamespace(
                        lexeme_anchor="lex:Darma",
                        evidence={"display_iast": "dharma", "display_slp1": "Darma"},
                    ),
                ]
            )
        ],
    )

    view = build_header_view(reduction)

    assert view.forms == ("dharma",)
    assert view.source_keys == ("Darma",)


def test_build_display_payload_includes_json_ready_views() -> None:
    bucket = SimpleNamespace(
        bucket_id="bucket:law",
        display_gloss="loi; devoir",
        confidence_label="single-witness",
        witnesses=[
            SimpleNamespace(
                lexeme_anchor="lex:dharma",
                source_tool="translation",
                evidence={
                    "source_tool": "translation",
                    "display_iast": "dharma",
                    "display_slp1": "Darma",
                    "source_ref": "dico:34.html#dharma:0",
                    "source_lang": "en",
                    "source_lexicon": "dico",
                    "translation_id": "tr-1",
                    "model": "test-model",
                    "source_text_lang": "fr",
                    "target_lang": "en",
                    "derived_from_tool": "dico",
                    "derived_from_sense": "sense:lex:dharma#dico",
                    "source_entry": {
                        "dict": "dico",
                        "entry_id": "dharma",
                        "headword_norm": "dharma",
                        "source_text": "loi; devoir; cf. dharma",
                    },
                    "source_segments": [
                        {
                            "display_text": "cf. dharma",
                            "labels": ["cross_reference", "source_reference"],
                        }
                    ],
                },
            )
        ],
    )
    reduction = SimpleNamespace(lexeme_anchors=["lex:dharma"], buckets=[bucket])
    rows = [
        {
            "source_tool": "heritage",
            "form": "dharmam",
            "lemma": "dharma",
            "analysis": "m. sg. acc.",
        }
    ]

    payload = build_display_payload(
        reduction,
        rows,
        language="san",
        max_gloss_chars=20,
        include_foster=True,
        include_source_details=True,
        bucket_gloss=lambda _: "loi; devoir; cf. dharma",
        bucket_learner_gloss=lambda _: "law; duty",
    )

    assert payload["header"] == {"forms": ["dharma"], "source_keys": ["Darma"]}
    assert payload["analysis"] == [
        {
            "form": "dharmam",
            "lemma": "dharma",
            "analysis": "m. sg. acc.",
            "source": "heritage",
            "foster_display": "Receiving Function; Single; Male",
            "display_text": (
                "dharmam -> dharma: m. sg. acc. "
                "[Foster: Receiving Function; Single; Male] (heritage)"
            ),
        }
    ]
    assert payload["meanings"][0]["bucket_id"] == "bucket:law"  # type: ignore[index]
    assert payload["meanings"][0]["display_gloss"] == "law; duty"  # type: ignore[index]
    assert payload["meanings"][0]["evidence_gloss"] == "loi; devoir; cf. dh…"  # type: ignore[index]
    assert payload["meanings"][0]["source_text"] == "translation"  # type: ignore[index]
    assert payload["meanings"][0]["translation_sources"] == ["dico"]  # type: ignore[index]
    assert payload["meanings"][0]["source_detail_summary"]["cross_refs"] == [  # type: ignore[index]
        "cf. dharma"
    ]
    assert payload["meanings"][0]["entries"] == [  # type: ignore[index]
        {
            "witness_id": "",
            "lexeme_anchor": "lex:dharma",
            "sense_anchor": "",
            "claim_id": "",
            "source_tool": "translation",
            "source_ref": "dico:34.html#dharma:0",
            "source_lang": "en",
            "gloss_lang": "en",
            "display_form": "dharma",
            "source_key": "Darma",
            "headword": "dharma",
            "entry_id": "dharma",
            "dictionary": "dico",
            "raw_blob_ref": "",
            "source_encoding": "",
            "source_entry": {
                "dict": "dico",
                "entry_id": "dharma",
                "headword_norm": "dharma",
                "source_text_chars": 23,
                "has_source_text": True,
            },
            "source_detail_summary": {
                "cross_refs": ["cf. dharma"],
                "source_refs": [],
                "examples": [],
                "text": "cross refs: cf. dharma",
            },
            "translation": {
                "available": True,
                "translation_id": "tr-1",
                "source_lexicon": "dico",
                "source_text_lang": "fr",
                "target_lang": "en",
                "model": "test-model",
                "source_text_hash": "",
                "derived_from_tool": "dico",
                "derived_from_sense": "sense:lex:dharma#dico",
            },
        }
    ]


def test_build_header_view_falls_back_to_reduction_anchors() -> None:
    reduction = SimpleNamespace(lexeme_anchors=["lex:principium"], buckets=[])

    view = build_header_view(reduction)

    assert view.forms == ("principium",)
    assert view.source_keys == ()


def test_foster_display_for_analysis_renders_full_learner_labels() -> None:
    assert foster_display_for_analysis("lat", "noun; nominative; plural; neuter") == (
        "Naming Function; Group; Neuter"
    )
    assert foster_display_for_analysis("san", "m. sg. voc.") == ("Calling Function; Single; Male")
    assert foster_display_for_analysis("san", "n. sg. acc. | n. sg. nom.") == (
        "Receiving Function; Single; Neuter / Naming Function; Single; Neuter"
    )


def test_build_analysis_views_formats_optional_foster_labels() -> None:
    rows = [
        {
            "source_tool": "heritage",
            "form": "agnim",
            "lemma": "agni",
            "analysis": "m. sg. acc.",
        }
    ]

    with_foster = build_analysis_views(rows, language="san", include_foster=True)
    without_foster = build_analysis_views(rows, language="san", include_foster=False)

    assert with_foster[0].display_text == (
        "agnim -> agni: m. sg. acc. [Foster: Receiving Function; Single; Male] (heritage)"
    )
    assert without_foster[0].display_text == "agnim -> agni: m. sg. acc. (heritage)"


def test_summarize_source_details_merges_notes_and_typed_segments() -> None:
    summary = summarize_source_details(
        [
            {
                "source_notes": {
                    "cross_reference_segments": ["see Mn."],
                    "source_reference_segments": ["MBh."],
                },
                "source_segments": [
                    {
                        "display_text": "principio Cic. Off. 1, 11",
                        "labels": ["example", "citation", "source_reference"],
                    },
                    {
                        "display_text": "cf. principium",
                        "labels": ["cross_reference", "source_reference"],
                    },
                    {
                        "display_text": "Verg.",
                        "labels": ["source_reference"],
                    },
                ],
            }
        ]
    )

    assert summary.cross_refs == ("see Mn.", "cf. principium")
    assert summary.source_refs == ("MBh.", "Verg.")
    assert summary.examples == ("principio Cic. Off. 1, 11",)
    assert summary.format() == (
        "cross refs: see Mn., cf. principium; source refs: MBh., Verg.; "
        "examples: principio Cic. Off. 1, 11"
    )


def test_summarize_source_details_dedupes_across_witnesses() -> None:
    summary = summarize_source_details(
        [
            {
                "source_notes": {
                    "cross_reference_segments": ["see Mn."],
                    "source_reference_segments": ["MBh."],
                }
            },
            {
                "source_segments": [
                    {
                        "raw_text": "see Mn.",
                        "labels": ["cross_reference", "source_reference"],
                    },
                    {
                        "raw_text": "MBh.",
                        "labels": ["source_reference"],
                    },
                ]
            },
        ]
    )

    assert summary.cross_refs == ("see Mn.",)
    assert summary.source_refs == ("MBh.",)


def test_build_meaning_view_keeps_evidence_line_and_metadata() -> None:
    bucket = SimpleNamespace(
        confidence_label="single-witness",
        witnesses=[
            SimpleNamespace(
                source_tool="translation",
                evidence={
                    "source_tool": "translation",
                    "source_ref": "gaffiot:gaffiot_53107",
                    "source_lang": "fr",
                    "source_lexicon": "gaffiot",
                    "translation_id": "tr-1",
                    "source_segments": [
                        {
                            "display_text": "cf. principium",
                            "labels": ["cross_reference", "source_reference"],
                        }
                    ],
                },
            )
        ],
    )

    view = build_meaning_view(
        bucket,
        learner_gloss="beginning",
        evidence_gloss="ĭī, n. (princeps), 1 beginning; cf. principium",
        max_gloss_chars=30,
    )

    assert view.display_gloss == "beginning"
    assert view.evidence_gloss.startswith("ĭī, n. (princeps), 1 begin")
    assert view.evidence_gloss.endswith("…")
    assert view.evidence_length_note == "evidence shown: 30/46 chars"
    assert view.length_note == ""
    assert view.source_text == "translation"
    assert view.witness_count == 1
    assert view.confidence_label == "single-witness"
    assert view.source_refs == ("gaffiot:gaffiot_53107",)
    assert view.source_detail_summary.cross_refs == ("cf. principium",)
    assert view.translation_sources == ("gaffiot",)
    assert view.source_langs == ("fr",)


def test_build_meaning_view_can_suppress_source_details() -> None:
    bucket = SimpleNamespace(
        confidence_label="single-witness",
        witnesses=[
            SimpleNamespace(
                source_tool="gaffiot",
                evidence={
                    "source_segments": [
                        {
                            "display_text": "cf. principium",
                            "labels": ["cross_reference", "source_reference"],
                        }
                    ]
                },
            )
        ],
    )

    view = build_meaning_view(
        bucket,
        learner_gloss="beginning",
        evidence_gloss="beginning; cf. principium",
        max_gloss_chars=80,
        include_source_details=False,
    )

    assert view.source_detail_summary.format() == ""
