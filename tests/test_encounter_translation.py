from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NoReturn, cast

import duckdb
import jsonschema
from click.testing import CliRunner
from filelock import FileLock

from langnet.cli import _PathTranslationCache, main
from langnet.encounter_translation import (
    add_translation_counts,
    apply_translation_cache,
    empty_translation_counts,
    encounter_translation_diagnostics,
    merge_translation_counts,
    resolve_translation_mode,
)
from langnet.translation import (
    BASE_SYSTEM,
    TranslationCache,
    TranslationRecord,
    build_translation_key,
    default_hints_for_language,
)

TRANSLATION_CACHE_SCHEMA_PATH = Path("docs/schemas/translation-cache.v1.schema.json")


def _assert_matches_translation_cache_schema(payload: object) -> None:
    schema = json.loads(TRANSLATION_CACHE_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)


def _dico_claim(source_text: str = "loi; devoir") -> dict[str, object]:
    return {
        "claim_id": "clm-dico",
        "tool": "claim.dico.fixture",
        "call_id": "call-dico",
        "source_call_id": "derive-dico",
        "derivation_id": "drv-dico",
        "subject": "lex:dharma",
        "predicate": "has_sense",
        "value": {
            "triples": [
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
                    "object": source_text,
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


def _translation_key(*, source_text: str, model: str):
    return build_translation_key(
        source_lexicon="dico",
        entry_id="dharma",
        occurrence=0,
        headword_norm="dharma",
        source_text=source_text,
        model=model,
        prompt=BASE_SYSTEM,
        hint="\n".join(default_hints_for_language("san")),
    )


def _fail_translate(_projection: object) -> NoReturn:
    raise AssertionError("translation callback should not be called")


def test_resolve_translation_mode_preserves_legacy_aliases() -> None:
    assert resolve_translation_mode(False, "do-it-all") == "auto"
    assert resolve_translation_mode(True, "off") == "cache"
    assert resolve_translation_mode(False, "off") == "off"
    assert resolve_translation_mode(False, "populate") == "populate"


def test_translation_count_helpers_accumulate_statuses() -> None:
    counts = empty_translation_counts()

    merge_translation_counts(counts, {"total": 2, "hits": 1, "missing": 1})
    add_translation_counts(counts, {"total": 3, "hits": 2}, prefix="before_")
    add_translation_counts(counts, {"total": 1}, prefix="before_")

    assert counts == {
        "total": 2,
        "hits": 1,
        "missing": 1,
        "errors": 0,
        "empty": 0,
        "before_total": 4,
        "before_hits": 2,
    }


def test_apply_translation_cache_projects_cached_hit_and_records_diagnostics() -> None:
    source_text = "loi; devoir"
    translated_text = "law; duty"
    model = "test-model"
    claim = _dico_claim(source_text)
    with duckdb.connect(database=":memory:") as conn:
        cache = TranslationCache(conn)
        cache.upsert(
            TranslationRecord(
                key=_translation_key(source_text=source_text, model=model),
                translated_text=translated_text,
                status="ok",
                duration_ms=5,
            )
        )
        diagnostics = encounter_translation_diagnostics(
            mode="cache",
            cache_path=Path("translations.duckdb"),
            model=model,
            populate=False,
        )

        projected = apply_translation_cache(
            claims=[claim],
            language="san",
            model=model,
            cache=cache,
            populate=False,
            translate=_fail_translate,
            diagnostics=diagnostics,
            context="unit",
        )

    assert diagnostics["before"] == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}
    assert diagnostics["after"] == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}
    assert diagnostics["written"] == 0
    assert diagnostics["batches"] == [
        {
            "context": "unit",
            "before": {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0},
            "written": 0,
            "after": {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0},
        }
    ]
    triples = projected[0]["value"]["triples"]  # type: ignore[index]
    assert any(triple["object"] == translated_text for triple in triples)


def test_apply_translation_cache_populates_missing_projection() -> None:
    source_text = "loi; devoir"
    translated_text = "law; duty"
    model = "test-model"
    claim = _dico_claim(source_text)
    with duckdb.connect(database=":memory:") as conn:
        cache = TranslationCache(conn)
        diagnostics = encounter_translation_diagnostics(
            mode="auto",
            cache_path=Path("translations.duckdb"),
            model=model,
            populate=True,
        )

        projected = apply_translation_cache(
            claims=[claim],
            language="san",
            model=model,
            cache=cache,
            populate=True,
            translate=lambda _projection: translated_text,
            diagnostics=diagnostics,
            context="unit",
        )
        record = cache.get(_translation_key(source_text=source_text, model=model))

    assert diagnostics["before"] == {"total": 1, "hits": 0, "missing": 1, "errors": 0, "empty": 0}
    assert diagnostics["after"] == {"total": 1, "hits": 1, "missing": 0, "errors": 0, "empty": 0}
    assert diagnostics["written"] == 1
    assert record is not None
    assert record.translated_text == translated_text
    triples = projected[0]["value"]["triples"]  # type: ignore[index]
    assert any(triple["object"] == translated_text for triple in triples)


def test_translation_cache_cli_status_and_clear_removes_translation_rows() -> None:
    source_text = "loi; devoir"
    model = "test-model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            cache.upsert(
                TranslationRecord(
                    key=_translation_key(source_text=source_text, model=model),
                    translated_text="law; duty",
                    status="ok",
                    duration_ms=5,
                )
            )

        runner = CliRunner()
        status = runner.invoke(
            main,
            [
                "translation-cache",
                "status",
                "--translation-cache-db",
                str(cache_path),
                "--output",
                "json",
            ],
        )
        assert status.exit_code == 0, status.output
        status_payload = json.loads(status.output)
        _assert_matches_translation_cache_schema(status_payload)
        assert status_payload["schema_version"] == "langnet.translation_cache.v1"
        assert status_payload["row_count"] == 1
        assert status_payload["status_counts"] == {"ok": 1}

        cleared = runner.invoke(
            main,
            [
                "translation-cache",
                "clear",
                "--translation-cache-db",
                str(cache_path),
                "--yes",
                "--output",
                "json",
            ],
        )
        assert cleared.exit_code == 0, cleared.output
        clear_payload = json.loads(cleared.output)
        _assert_matches_translation_cache_schema(clear_payload)
        assert clear_payload["schema_version"] == "langnet.translation_cache.v1"
        assert clear_payload["deleted"] == 1
        assert clear_payload["before"]["row_count"] == 1
        assert clear_payload["after"]["row_count"] == 0


def test_translation_cache_cli_clear_filters_error_rows_by_source_and_headword() -> None:
    model = "test-model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            cache.upsert(
                TranslationRecord(
                    key=build_translation_key(
                        source_lexicon="bailly",
                        entry_id="bailly-p1450-c1-0024",
                        occurrence=0,
                        headword_norm="logos",
                        source_text="raison, d'où",
                        model=model,
                        prompt=BASE_SYSTEM,
                        hint="\n".join(default_hints_for_language("grc")),
                    ),
                    translated_text=None,
                    status="error",
                    error="Bailly translation block 01 appears untranslated",
                    duration_ms=5,
                )
            )
            cache.upsert(
                TranslationRecord(
                    key=build_translation_key(
                        source_lexicon="bailly",
                        entry_id="bailly-p090-c1-0004",
                        occurrence=0,
                        headword_norm="agelaios",
                        source_text="qui forme un troupeau",
                        model=model,
                        prompt=BASE_SYSTEM,
                        hint="\n".join(default_hints_for_language("grc")),
                    ),
                    translated_text="which forms a herd",
                    status="ok",
                    duration_ms=5,
                )
            )

        runner = CliRunner()
        cleared = runner.invoke(
            main,
            [
                "translation-cache",
                "clear",
                "--translation-cache-db",
                str(cache_path),
                "--source-lexicon",
                "bailly",
                "--status",
                "error",
                "--headword",
                "logos",
                "--yes",
                "--output",
                "json",
            ],
        )

        assert cleared.exit_code == 0, cleared.output
        clear_payload = json.loads(cleared.output)
        _assert_matches_translation_cache_schema(clear_payload)
        assert clear_payload["deleted"] == 1
        assert clear_payload["source_lexicon"] == "bailly"
        assert clear_payload["status"] == "error"
        assert clear_payload["headword"] == "logos"
        assert clear_payload["after"]["row_count"] == 1
        assert clear_payload["after"]["status_counts"] == {"ok": 1}


def test_translation_cache_cli_clear_removes_bad_ok_row_by_translation_id() -> None:
    source_text = "alors, il y a"
    model = "test-model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            key = build_translation_key(
                source_lexicon="dico",
                entry_id="asti",
                occurrence=0,
                headword_norm="asti",
                source_text=source_text,
                model=model,
                prompt=BASE_SYSTEM,
                hint="\n".join(default_hints_for_language("san")),
            )
            cache.upsert(
                TranslationRecord(
                    key=key,
                    translated_text="asti",
                    status="ok",
                    duration_ms=5,
                )
            )

        runner = CliRunner()
        cleared = runner.invoke(
            main,
            [
                "translation-cache",
                "clear",
                "--translation-cache-db",
                str(cache_path),
                "--translation-id",
                key.translation_id,
                "--yes",
                "--output",
                "json",
            ],
        )

        assert cleared.exit_code == 0, cleared.output
        clear_payload = json.loads(cleared.output)
        _assert_matches_translation_cache_schema(clear_payload)
        assert clear_payload["deleted"] == 1
        assert clear_payload["translation_id"] == key.translation_id
        assert clear_payload["after"]["row_count"] == 0


def test_translation_cache_cli_clear_removes_compatible_projection_rows() -> None:
    source_text = "alors, il y a"
    model = "test-model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            bad_key = build_translation_key(
                source_lexicon="dico",
                entry_id="asti",
                occurrence=0,
                headword_norm="asti",
                source_text=source_text,
                model=model,
                prompt=BASE_SYSTEM,
                hint="\n".join(default_hints_for_language("san")),
            )
            keep_key = build_translation_key(
                source_lexicon="dico",
                entry_id="astitva",
                occurrence=0,
                headword_norm="astitva",
                source_text="existence ; réalité",
                model=model,
                prompt=BASE_SYSTEM,
                hint="\n".join(default_hints_for_language("san")),
            )
            cache.upsert(
                TranslationRecord(
                    key=bad_key,
                    translated_text="asti",
                    status="ok",
                    duration_ms=5,
                )
            )
            cache.upsert(
                TranslationRecord(
                    key=keep_key,
                    translated_text="existence; reality",
                    status="ok",
                    duration_ms=5,
                )
            )

        runner = CliRunner()
        cleared = runner.invoke(
            main,
            [
                "translation-cache",
                "clear",
                "--translation-cache-db",
                str(cache_path),
                "--source-lexicon",
                "dico",
                "--entry-id",
                "asti",
                "--occurrence",
                "0",
                "--source-text-hash",
                bad_key.source_text_hash,
                "--yes",
                "--output",
                "json",
            ],
        )

        assert cleared.exit_code == 0, cleared.output
        clear_payload = json.loads(cleared.output)
        _assert_matches_translation_cache_schema(clear_payload)
        assert clear_payload["deleted"] == 1
        assert clear_payload["entry_id"] == "asti"
        assert clear_payload["source_text_hash"] == bad_key.source_text_hash
        assert clear_payload["after"]["row_count"] == 1


def test_translation_cache_cli_clear_caps_user_rejection_generation() -> None:
    source_text = "alors, il y a"
    model = "test-model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            key = build_translation_key(
                source_lexicon="dico",
                entry_id="asti",
                occurrence=0,
                headword_norm="asti",
                source_text=source_text,
                model=model,
                prompt=BASE_SYSTEM,
                hint="\n".join(default_hints_for_language("san")),
            )
            cache.upsert(
                TranslationRecord(
                    key=key,
                    translated_text="asti",
                    status="ok",
                    duration_ms=5,
                )
            )

        clear_args = [
            "translation-cache",
            "clear",
            "--translation-cache-db",
            str(cache_path),
            "--source-lexicon",
            "dico",
            "--entry-id",
            "asti",
            "--occurrence",
            "0",
            "--source-text-hash",
            key.source_text_hash,
            "--retry-reason",
            "user_rejected",
            "--max-retries",
            "1",
            "--yes",
            "--output",
            "json",
        ]
        runner = CliRunner()
        first = runner.invoke(main, clear_args)
        assert first.exit_code == 0, first.output
        first_payload = json.loads(first.output)
        assert first_payload["deleted"] == 1
        assert first_payload["retry_generation"] == 1
        assert first_payload["limit_reached"] is False

        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            cache.upsert(
                TranslationRecord(
                    key=key,
                    translated_text="asti again",
                    status="ok",
                    duration_ms=5,
                )
            )

        second = runner.invoke(main, clear_args)
        assert second.exit_code == 0, second.output
        second_payload = json.loads(second.output)
        assert second_payload["deleted"] == 0
        assert second_payload["retry_generation"] == 1
        assert second_payload["limit_reached"] is True
        assert second_payload["after"]["row_count"] == 1


def test_path_translation_cache_does_not_hold_lock_during_model_call() -> None:
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        cache = _PathTranslationCache(cache_path, read_only=False)

        def translate(_projection: object) -> str:
            with FileLock(f"{cache_path}.lock", timeout=0):
                pass
            return "law; duty"

        projected = apply_translation_cache(
            claims=[_dico_claim()],
            language="san",
            model="test-model",
            cache=cache,  # type: ignore[arg-type]
            populate=True,
            translate=translate,
            diagnostics=encounter_translation_diagnostics(
                mode="auto",
                cache_path=cache_path,
                model="test-model",
                populate=True,
            ),
            context="test",
        )

        first_claim = cast(dict[str, object], projected[0])
        first_value = cast(dict[str, object], first_claim["value"])
        assert first_value["triples"]
        with duckdb.connect(str(cache_path), read_only=True) as conn:
            row = conn.execute("SELECT translated_text FROM entry_translations").fetchone()
        assert row == ("law; duty",)


def test_path_translation_cache_reads_without_waiting_for_writer_file_lock() -> None:
    source_text = "loi; devoir"
    model = "test-model"
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        with duckdb.connect(str(cache_path)) as conn:
            cache = TranslationCache(conn)
            cache.upsert(
                TranslationRecord(
                    key=_translation_key(source_text=source_text, model=model),
                    translated_text="law; duty",
                    status="ok",
                    duration_ms=5,
                )
            )

        cache = _PathTranslationCache(cache_path, read_only=True)
        key = _translation_key(source_text=source_text, model=model)
        with FileLock(f"{cache_path}.lock", timeout=0):
            record = cast(TranslationRecord | None, cache.get(key))

    assert record is not None
    assert record.translated_text == "law; duty"


def test_path_translation_cache_read_lock_failure_is_cache_miss(monkeypatch) -> None:
    with TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "langnet.duckdb"
        cache_path.touch()
        cache = _PathTranslationCache(cache_path, read_only=True)

        def fail_connect(*_args, **_kwargs):
            raise duckdb.IOException("database is locked")

        monkeypatch.setattr("langnet.cli.connect_duckdb", fail_connect)

        assert cache.get(_translation_key(source_text="loi; devoir", model="test-model")) is None
