# French Entry Translation Cache

**Status:** cache schema/key helpers, demo cache writes, encounter cache-hit projection, and Gaffiot/DICO golden cache rows are implemented.  
**Scope:** lazy French → English translation for Gaffiot Latin entries first, then DICO Sanskrit entries.

## Current State

- `just translate-lex` samples rows from local DuckDB lexicon indexes and sends them to OpenRouter through `aisuite`.
- DICO reads from `data/build/lex_dico.duckdb`; Gaffiot reads from `data/build/lex_gaffiot.duckdb`.
- CDSL does not need translation for this path. It already provides Sanskrit dictionary material separately from the French DICO index.
- The current prompt and chunking behavior are tuned most heavily for Gaffiot: Latin citations are preserved while surrounding French explanation is translated, and entries are split on Gaffiot paragraph markers.
- DICO/Sanskrit mode exists and has Sanskrit-preservation hints, but should be treated as less mature until it has fixture-backed examples.
- `langnet.translation.cache` now provides the DuckDB `entry_translations` schema, cache-key helpers, and a small `TranslationCache` read/write wrapper. This is intentionally no-network infrastructure.
- `langnet.translation.projection` can project successful cache hits into derived English `has_sense`/`gloss` triples before semantic reduction.
- `langnet-cli encounter` now provides a first learner-facing textual path over claim-to-WSU reduction. It displays reduced source glosses and, with `--use-translation-cache`, treats cached translations as first-class English meaning buckets.
- `.justscripts/lex_translation_demo.py` can now write successful translations to `entry_translations` with `--write-cache` and can display deterministic cache keys with `--show-cache-key`.
- `langnet-cli encounter` can read cache hits with `--use-translation-cache --translation-cache-db <path>`. It does not call the network.
- `triples-dump` resolves exact Latin headwords through staged Gaffiot effects (`fetch.gaffiot` → `extract.gaffiot.json` → `derive.gaffiot.entries` → `claim.gaffiot.entries`) and emits French Gaffiot gloss triples.
- `langnet-cli databuild dico` can rebuild the DICO DuckDB index from local Sanskrit Heritage `DICO/*.html` files.
- `triples-dump` resolves Sanskrit headwords through staged DICO effects (`fetch.dico` → `extract.dico.json` → `derive.dico.entries` → `claim.dico.entries`) and emits French DICO gloss triples.
- Heritage `/skt/DICO/*.html#anchor` URL resolution remains as a fallback for cases where the planned headword misses the exact DICO anchor.
- Gaffiot and DICO lookup clients try multiple candidate forms from the planner so inflected Latin and encoded Sanskrit variants have a better chance of finding local entries.
- Gaffiot/DICO source triples remain source-language French evidence. Cached translations are emitted as derived evidence when requested.
- Translation population is intentionally networked and potentially expensive, so it must stay opt-in. Normal learner-facing lookup should prefer resolved cache hits and should not call the translation provider implicitly.
- `docs/OUTPUT_GUIDE.md` now includes an inspection walkthrough for source French triples and derived cache-hit English witnesses.

## Target Behavior

Translation should be lazy, cached, and evidence-bearing:

1. `triples-dump` or a dedicated lexicon witness loader reads source Gaffiot/DICO entries.
2. If translation is requested, it checks a local translation cache.
3. On a cache hit, it emits English gloss triples with translation evidence.
4. On a cache miss, it may call the translation provider only when explicitly allowed.
5. Reducer tests use fixtures or fake translators, never live API calls.

## Cache Identity

The cache key should include every input that changes output meaning:

- `source_lexicon`: `gaffiot` or `dico`
- `entry_id`
- `occurrence`
- `headword_norm`
- `source_text_hash`
- `source_lang`: `fr`
- `target_lang`: `en`
- `model`
- `prompt_hash`
- `hint_hash`

This avoids reusing stale translations when source text, prompt instructions, or model choices change.

## Proposed Table

```sql
CREATE TABLE IF NOT EXISTS entry_translations (
  translation_id TEXT PRIMARY KEY,
  source_lexicon TEXT NOT NULL,
  entry_id TEXT NOT NULL,
  occurrence INTEGER NOT NULL,
  headword_norm TEXT,
  source_text_hash TEXT NOT NULL,
  source_lang TEXT NOT NULL,
  target_lang TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  hint_hash TEXT NOT NULL,
  translated_text TEXT,
  status TEXT NOT NULL,
  error TEXT,
  duration_ms INTEGER,
  created_at DOUBLE NOT NULL,
  updated_at DOUBLE NOT NULL
);
```

`status` should be one of `ok`, `failed`, or `skipped`. Failed rows remain useful because they prevent silent repeated expensive calls during debugging.

## Triple Projection

Translated text should not replace source French text. It should be projected as derived evidence:

```text
lexeme:<lemma> has_sense sense:<source_lexicon>:<entry_id>:<occurrence>
sense:<...> gloss "<English translation>"
```

The `gloss` claim should carry translation metadata:

- `translation_id`
- `source_lexicon`
- `entry_id`
- `occurrence`
- `source_text_hash`
- `source_text_lang`
- `gloss_lang`
- `model`
- `prompt_hash`
- `hint_hash`

Semantic reduction should treat these as derived witness data. The reducer must be able to distinguish native English source glosses from model-translated glosses.

## CLI Boundary

Possible future commands:

```bash
langnet-cli lexicon-translate san dico agni --cache data/cache/langnet.duckdb
langnet-cli triples-dump lat lupus all --include-gaffiot --translate-fr-en --allow-translation-network
```

Network calls should require an explicit opt-in flag such as `--allow-translation-network`. Cache-only translation reads should be safe for routine inspection.

Current bridge command:

```bash
devenv shell -- bash -c 'python3 .justscripts/lex_translation_demo.py --mode latin --headword lupus --limit 1 --write-cache --show-cache-key'
devenv shell -- bash -c 'langnet-cli encounter lat lupus gaffiot --use-translation-cache --translation-cache-db data/cache/langnet.duckdb'
```

## Stabilization Steps

1. Add cache schema and key helpers without calling the network. **Done.**
2. Add fixture-backed Gaffiot/DICO tests for cache identity and cache hits. **Done.**
3. Wire the existing translation demo into cache writes. **Done.**
4. Add cache-hit display in `encounter`. **Done.**
5. Add cache-hit translated gloss projection for `encounter` reducer JSON. **Done.**
6. Add evidence-inspection walkthrough for cached translations in `encounter`. **Done.**
7. Add accepted-output examples that show cached translations in `encounter`.
8. Add a fake translator interface for no-network integration tests if the explicit miss path needs more coverage.
9. Add the explicit network miss path only behind an opt-in flag after cache-hit behavior is stable.
