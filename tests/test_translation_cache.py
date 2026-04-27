from __future__ import annotations

import duckdb

from langnet.translation import TranslationCache, TranslationRecord, build_translation_key

TRANSLATION_DURATION_MS = 12


def test_translation_cache_key_changes_with_prompt_material() -> None:
    first = build_translation_key(
        source_lexicon="dico",
        entry_id="dharma",
        occurrence=0,
        headword_norm="dharma",
        source_text="loi, devoir",
        model="test:model",
        prompt="translate",
        hint="preserve Sanskrit",
    )
    second = build_translation_key(
        source_lexicon="dico",
        entry_id="dharma",
        occurrence=0,
        headword_norm="dharma",
        source_text="loi, devoir",
        model="test:model",
        prompt="translate",
        hint="preserve Sanskrit IAST",
    )

    assert first.translation_id != second.translation_id


def test_translation_cache_round_trips_ok_record() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn)
    key = build_translation_key(
        source_lexicon="gaffiot",
        entry_id="gaffiot_38776",
        occurrence=1,
        headword_norm="lupus",
        source_text="loup",
        model="test:model",
        prompt="translate",
        hint="keep Latin",
    )

    translation_id = cache.upsert(
        TranslationRecord(
            key=key,
            translated_text="wolf",
            status="ok",
            duration_ms=TRANSLATION_DURATION_MS,
        )
    )
    loaded = cache.get(key)

    assert translation_id == key.translation_id
    assert loaded is not None
    assert loaded.translated_text == "wolf"
    assert loaded.status == "ok"
    assert loaded.duration_ms == TRANSLATION_DURATION_MS


def test_read_only_translation_cache_without_table_is_a_miss() -> None:
    conn = duckdb.connect(database=":memory:")
    cache = TranslationCache(conn, read_only=True)
    key = build_translation_key(
        source_lexicon="gaffiot",
        entry_id="gaffiot_38776",
        occurrence=1,
        headword_norm="lupus",
        source_text="loup",
        model="test:model",
        prompt="translate",
        hint="keep Latin",
    )

    assert cache.get(key) is None
