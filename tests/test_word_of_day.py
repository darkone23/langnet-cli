from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import jsonschema
from click.testing import CliRunner

from langnet.cli import (
    _word_of_day_apply_finalized_cards,
    _word_of_day_finalizer_system_prompt,
    _word_of_day_llm_call,
    _word_of_day_parse_finalized_cards,
    _word_of_day_parse_synthesized_candidates,
    _word_of_day_probe_translation_mode,
    _word_of_day_system_prompt,
    main,
)
from langnet.reduction.models import ReductionResult, SenseBucket, WitnessSenseUnit
from langnet.word_of_day import (
    WordCandidate,
    WordOfDayOptions,
    build_word_of_day_item,
    generate_word_of_day_payload,
)

RECOMMEND_WORDS_COUNT = 2
SUBPROCESS_TIMEOUT_TEST_MAX_SECONDS = 2
WORD_OF_DAY_SCHEMA_PATH = Path("docs/schemas/word_of_day.v1.schema.json")


def _assert_matches_word_of_day_schema(payload: object) -> None:
    schema = json.loads(WORD_OF_DAY_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def _slow_word_of_day_llm_direct(**_kwargs) -> dict[str, list[WordCandidate]]:
    time.sleep(5)
    return {}


def _fake_reduction(
    language: str,
    query: str,
    *,
    display_gloss: str = "one; a single one",
) -> ReductionResult:
    witness = WitnessSenseUnit(
        wsu_id=f"wsu:{language}:{query}",
        lexeme_anchor=f"lex:{query}",
        sense_anchor=f"sense:lex:{query}#1",
        gloss=display_gloss,
        normalized_gloss=display_gloss,
        source_tool="fixture",
        claim_id="claim-fixture",
        source_triple_subject=f"lex:{query}",
        evidence={
            "source_tool": "fixture",
            "source_ref": "fixture:1",
            "source_entry": {
                "source_ref": "fixture:1",
                "term": query,
                "source_text": display_gloss,
            },
        },
    )
    return ReductionResult(
        query=query,
        language=language,
        lexeme_anchors=[f"lex:{query}"],
        buckets=[
            SenseBucket(
                bucket_id=f"bucket:{language}:{query}",
                normalized_gloss=display_gloss,
                display_gloss=display_gloss,
                witnesses=[witness],
                confidence_label="single-witness",
            )
        ],
    )


def _options(seed: str = "stable") -> WordOfDayOptions:
    return WordOfDayOptions(
        count=1,
        level="beginner",
        dictionary="all",
        reader_lang="en",
        translation_mode="cache",
        max_source_chars=80,
        include_ambiguous=False,
        require_clean_primary=False,
        timeout_ms=0,
        seed=seed,
    )


def test_word_recommendations_seeded_output_is_reproducible() -> None:
    first = generate_word_of_day_payload(
        languages=["lat", "grc"],
        options=_options(),
        probe_encounter=_fake_reduction,
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
        exclude_terms=[],
    )
    second = generate_word_of_day_payload(
        languages=["lat", "grc"],
        options=_options(),
        probe_encounter=_fake_reduction,
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
        exclude_terms=[],
    )

    assert first["generator"] == second["generator"]
    assert first["request"] == second["request"]
    assert first["items"] == second["items"]


def test_word_of_day_cli_returns_structured_json() -> None:
    runner = CliRunner()
    with patch("langnet.cli._word_of_day_probe_reduction") as probe:
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "all",
                "--seed",
                "smoke",
                "--output",
                "json",
                "--candidate-source",
                "curated",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["schema_version"] == "langnet.word_of_day.v1"
    assert payload["request"]["languages"] == ["san", "grc", "lat"]
    assert {item["language"] for item in payload["items"]} == {"san", "grc", "lat"}
    for item in payload["items"]:
        assert item["query"]
        assert item["display"]
        assert item["canonical_name"]
        assert item["canonical"]["name"] == item["canonical_name"]
        assert item["summary"]
        assert item["learner_note"]
        assert item["recommended_request"]["backend"] == "cli"
        assert item["source_basis"]


def test_recommend_words_alias_uses_same_json_contract() -> None:
    runner = CliRunner()
    with patch("langnet.cli._word_of_day_probe_reduction") as probe:
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "recommend-words",
                "lat",
                "--seed",
                "smoke",
                "--count",
                str(RECOMMEND_WORDS_COUNT),
                "--output",
                "json",
                "--candidate-source",
                "curated",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["request"]["languages"] == ["lat"]
    assert len(payload["items"]) == RECOMMEND_WORDS_COUNT


def test_word_of_day_probe_translation_mode_never_populates() -> None:
    assert _word_of_day_probe_translation_mode("off") == "off"
    assert _word_of_day_probe_translation_mode("cache") == "cache"
    assert _word_of_day_probe_translation_mode("auto") == "cache"
    assert _word_of_day_probe_translation_mode("populate") == "cache"
    assert _word_of_day_probe_translation_mode("do-it-all") == "cache"


def test_word_of_day_auto_translation_mode_uses_cache_probe_with_warning() -> None:
    runner = CliRunner()
    with patch("langnet.cli._word_of_day_probe_reduction") as probe:
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--candidate-source",
                "curated",
                "--translation-mode",
                "auto",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["request"]["translation_mode"] == "auto"
    assert "skipped translation population" in payload["warnings"][0]["message"]
    assert probe.call_args.kwargs["translation_mode"] == "cache"


def test_word_of_day_fresh_avoids_recent_keys_when_possible() -> None:
    runner = CliRunner()
    seen: list[str] = []
    with patch("langnet.cli._word_of_day_probe_reduction") as probe:
        probe.side_effect = lambda **kwargs: (
            seen.append(kwargs["text"]) or _fake_reduction(kwargs["language"], kwargs["text"])
        )
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--seed",
                "stable",
                "--fresh",
                "--avoid",
                "lat:nox,lat:lupus,lat:arma,lat:amo",
                "--output",
                "json",
                "--candidate-source",
                "curated",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    item = payload["items"][0]
    assert item["key"] == "lat:rex"
    assert item["novelty"]["is_repeat"] is False
    assert payload["exhaustion"]["fresh_satisfied"] is True
    assert seen == ["rex"]


def test_word_of_day_marks_repeat_when_fresh_exhausted() -> None:
    runner = CliRunner()
    with patch("langnet.cli._word_of_day_probe_reduction") as probe:
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--seed",
                "stable",
                "--fresh",
                "--avoid",
                "lat:nox,lat:lupus,lat:arma,lat:amo,lat:rex",
                "--output",
                "json",
                "--candidate-source",
                "curated",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["items"][0]["novelty"]["is_repeat"] is True
    assert payload["exhaustion"]["fresh_satisfied"] is False


def test_word_of_day_can_use_llm_synthesized_candidates() -> None:
    runner = CliRunner()
    with (
        patch("langnet.cli._word_of_day_synthesize_candidates") as synthesize,
        patch("langnet.cli._word_of_day_finalize_payload_with_llm") as finalize,
        patch("langnet.cli._word_of_day_probe_reduction") as probe,
    ):
        synthesize.return_value = {
            "lat": [WordCandidate("lat", "mare", summary_hint="single word")]
        }
        finalize.side_effect = lambda payload, **_kwargs: payload
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--candidate-source",
                "llm",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["generator"]["candidate_source"] == "llm"
    assert payload["items"][0]["query"] == "mare"
    assert payload["items"][0]["summary"] == "single word"
    finalize.assert_called_once()


def test_word_of_day_auto_falls_back_when_llm_synthesis_times_out() -> None:
    runner = CliRunner()
    with (
        patch("langnet.cli._word_of_day_synthesize_candidates") as synthesize,
        patch("langnet.cli._word_of_day_probe_reduction") as probe,
    ):
        synthesize.side_effect = TimeoutError("synthetic timeout")
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--candidate-source",
                "auto",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["generator"]["candidate_source"] == "curated"
    assert "fell back to curated pools" in payload["warnings"][0]["message"]


def test_word_of_day_llm_source_fails_loudly_when_synthesis_times_out() -> None:
    runner = CliRunner()
    with patch("langnet.cli._word_of_day_synthesize_candidates") as synthesize:
        synthesize.side_effect = TimeoutError("synthetic timeout")
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--candidate-source",
                "llm",
                "--output",
                "json",
            ],
        )

    assert result.exit_code != 0
    assert "TimeoutError: synthetic timeout" in result.output


def test_word_of_day_auto_falls_back_when_llm_returns_no_candidates() -> None:
    runner = CliRunner()
    with (
        patch("langnet.cli._word_of_day_synthesize_candidates") as synthesize,
        patch("langnet.cli._word_of_day_probe_reduction") as probe,
    ):
        synthesize.return_value = {}
        probe.side_effect = lambda **kwargs: _fake_reduction(kwargs["language"], kwargs["text"])
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--candidate-source",
                "auto",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    _assert_matches_word_of_day_schema(payload)
    assert payload["generator"]["candidate_source"] == "curated"
    assert "returned no candidates for lat" in payload["warnings"][0]["message"]


def test_word_of_day_llm_source_fails_when_llm_returns_no_candidates() -> None:
    runner = CliRunner()
    with patch("langnet.cli._word_of_day_synthesize_candidates") as synthesize:
        synthesize.return_value = {}
        result = runner.invoke(
            main,
            [
                "word-of-day",
                "lat",
                "--candidate-source",
                "llm",
                "--output",
                "json",
            ],
        )

    assert result.exit_code != 0
    assert "returned no candidates for lat" in result.output


def test_word_of_day_llm_call_enforces_subprocess_deadline() -> None:
    started = time.monotonic()
    with patch(
        "langnet.cli._word_of_day_synthesize_candidates_direct",
        side_effect=_slow_word_of_day_llm_direct,
    ):
        try:
            _word_of_day_llm_call(
                "synthesize",
                {
                    "languages": ["lat"],
                    "count": 1,
                    "level": "beginner",
                    "avoid_terms": [],
                    "nonce": None,
                    "rotation_key": None,
                    "model": "openai:example",
                    "timeout_seconds": 0.1,
                },
                timeout_seconds=0.1,
            )
        except TimeoutError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("expected LLM subprocess timeout")

    assert time.monotonic() - started < SUBPROCESS_TIMEOUT_TEST_MAX_SECONDS


def test_word_of_day_finalizer_updates_verified_card_text() -> None:
    payload = {
        "items": [
            {
                "key": "grc:logos",
                "summary": "account of money handled",
                "learner_note": "old note",
                "mnemonic": "",
                "ui": {"short_gloss": "account of money handled"},
            }
        ]
    }
    updates = _word_of_day_parse_finalized_cards(
        json.dumps(
            {
                "items": [
                    {
                        "key": "grc:logos",
                        "summary": "word; account; reason; rational principle in speech",
                        "learner_note": (
                            "Good for learners because it joins ordinary speech with "
                            "abstract reasoning."
                        ),
                        "mnemonic": "A sober note about speech and account.",
                    }
                ]
            }
        )
    )

    _word_of_day_apply_finalized_cards(payload, updates)

    item = payload["items"][0]
    assert item["summary"] == "word; account; reason; rational principle in sp…"
    assert item["learner_note"] == (
        "Good for learners because it joins ordinary speech with abstract reasoning."
    )
    assert item["mnemonic"] == "A sober note about speech and account."
    assert isinstance(item["ui"], dict)
    assert item["ui"]["short_gloss"] == "word"


def test_word_of_day_prompt_requests_scholarly_humanist_tone() -> None:
    prompt = _word_of_day_system_prompt().lower()

    assert "scholarly-humanist" in prompt
    assert "philological" in prompt
    assert "learned seriousness" in prompt
    assert "mild eccentricity" in prompt
    assert "real philology" in prompt
    assert "morphology" in prompt
    assert "semantic range" in prompt
    assert "historically defensible" in prompt
    assert "random novelty" in prompt


def test_word_of_day_finalizer_prompt_distinguishes_summary_from_learner_note() -> None:
    prompt = _word_of_day_finalizer_system_prompt().lower()

    assert "summary" in prompt
    assert "learner_note" in prompt
    assert "why this is a good word for learners" in prompt
    assert "must not be a longer definition" in prompt


def test_word_of_day_parser_filters_unsuitable_llm_mnemonics() -> None:
    payload = {
        "items": [
            {
                "language": "san",
                "query": "jala",
                "summary": "water",
                "difficulty": "beginner",
                "mnemonic": "A random pop-culture joke mnemonic.",
            },
            {
                "language": "lat",
                "query": "aqua",
                "summary": "water",
                "difficulty": "beginner",
                "mnemonic": "This sounds like a modern brand pun.",
            },
            {
                "language": "grc",
                "query": "logos",
                "summary": "word; account; reason",
                "difficulty": "beginner",
                "mnemonic": "A central term for speech, reckoning, and rational account.",
            },
        ]
    }

    pools = _word_of_day_parse_synthesized_candidates(
        json.dumps(payload), languages=["san", "lat", "grc"]
    )

    assert set(pools) == {"grc"}
    assert pools["grc"][0].query == "logos"


def test_word_of_day_uses_llm_summary_only_when_supported_by_source() -> None:
    reduction = _fake_reduction("lat", "virtus")
    item = build_word_of_day_item(
        candidate=WordCandidate(
            "lat",
            "virtus",
            summary_hint="manliness, courage, comprehensive moral excellence",
        ),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: "strength; power",
    )

    assert item is not None
    assert item["summary"] == "strength; power"


def test_word_of_day_keeps_supported_llm_summary_hint() -> None:
    reduction = _fake_reduction("grc", "arete")
    item = build_word_of_day_item(
        candidate=WordCandidate(
            "grc",
            "arete",
            summary_hint="single unity",
        ),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is not None
    assert item["summary"] == "single unity"


def test_word_of_day_projects_sanskrit_devanagari_canonical_name() -> None:
    reduction = _fake_reduction("san", "dharma")
    source_entry = reduction.buckets[0].witnesses[0].evidence["source_entry"]
    source_entry["headword_deva"] = "धर्म"
    source_entry["headword_roma"] = "dharma"

    item = build_word_of_day_item(
        candidate=WordCandidate("san", "dharma"),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is not None
    assert item["canonical_name"] == "धर्म"
    assert item["canonical"] == {
        "name": "धर्म",
        "script": "Devanagari",
        "source": "source_entry.headword_deva",
        "transliteration": "dharma",
        "source_key": "dharma",
        "lexeme": "dharma",
    }


def test_word_of_day_projects_greek_unicode_canonical_name() -> None:
    reduction = _fake_reduction("grc", "logos")
    reduction.buckets[0].witnesses[0].evidence["source_entry"]["term"] = "λόγος"

    item = build_word_of_day_item(
        candidate=WordCandidate("grc", "logos"),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is not None
    assert item["canonical_name"] == "λόγος"
    assert item["canonical"]["script"] == "Greek"
    assert item["canonical"]["source"] == "source_entry.term"
    assert item["canonical"]["transliteration"] == "logos"


def test_word_of_day_strips_greek_example_tail_from_summary() -> None:
    reduction = _fake_reduction(
        "grc",
        "homo",
        display_gloss="one and the same, common, joint, οὐ γὰρ πάντων ἦεν ὁ. θρόος Il. 4.437",
    )
    item = build_word_of_day_item(
        candidate=WordCandidate("grc", "homo"),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is not None
    assert item["summary"] == "one and the same, common, joint"


def test_word_of_day_strips_dangling_cross_reference_tail_from_summary() -> None:
    reduction = _fake_reduction(
        "grc",
        "polis",
        display_gloss="one's city or country, etc., cf. πόλιν· τὴν χώραν, Hsch.",
    )
    item = build_word_of_day_item(
        candidate=WordCandidate("grc", "polis"),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is not None
    assert item["summary"] == "one's city or country"


def test_word_of_day_rejects_reference_fragment_summary() -> None:
    reduction = _fake_reduction(
        "grc",
        "kapnos",
        display_gloss="cod. Urb., v.l. κάπνεος)",
    )
    item = build_word_of_day_item(
        candidate=WordCandidate("grc", "kapnos"),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is None


def test_word_of_day_rejects_grammar_fragment_summary() -> None:
    reduction = _fake_reduction(
        "grc",
        "agathos",
        display_gloss="c. gen., εἴ τι οἶδα πυρετοῦ ἀ. good for it, Id. Mem. 3.8.3",
    )
    item = build_word_of_day_item(
        candidate=WordCandidate("grc", "agathos"),
        reduction=reduction,
        options=_options(),
        bucket_gloss=lambda bucket: bucket.display_gloss,
        bucket_learner_gloss=lambda bucket: bucket.display_gloss,
    )

    assert item is None
