# DICO/Gaffiot Translation Cache

**Status:** implemented for cache hits and explicit cache-miss population.  
**Scope:** French source entries from Gaffiot and DICO, projected as
cache-backed English derived evidence.

## Current Behavior

DICO and Gaffiot source entries remain French source evidence. English
translations are separate derived witnesses.

`encounter` supports:

```bash
# Cache-only read. No network call.
langnet-cli encounter lat lupus gaffiot --translation-mode cache
langnet-cli encounter san dharma dico --translation-mode cache

# Explicit cache-miss population through OpenRouter, then display.
langnet-cli encounter lat cano gaffiot --translation-mode auto
langnet-cli encounter san karman dico --translation-mode auto
```

`--use-translation-cache` remains supported as an older spelling for cache-only
display.

`--translation-mode auto` requires `OPENAI_API_KEY` only when a missing
translation must be populated. Fully cached lookups do not require the key.

## Data Flow

```text
DICO/Gaffiot source triples
  -> build exact translation cache key
  -> read entry_translations
  -> optionally populate missing rows
  -> project English has_sense/gloss triples
  -> reduce into encounter buckets
```

The projected English witness carries `source_tool: translation` and evidence
fields that point back to the original DICO/Gaffiot source reference.

## Cache Identity

The cache key includes every input that can change translation meaning:

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

This prevents stale translations from being reused when source text, prompt
instructions, or model choices change.

## Table

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

Current statuses include `ok`, `error`, and `empty`.

## Evidence Policy

Translated text must not replace source French text. It is projected as derived
evidence with metadata such as:

- `translation_id`
- `source_lexicon`
- `source_ref`
- `source_text_hash`
- `source_text_lang`
- `gloss_lang`
- `model`
- `prompt_hash`
- `hint_hash`
- `derived_from_tool`
- `derived_from_sense`

The reducer can use translated witnesses for display and grouping, but the
source French witness remains inspectable.

## Observed Quality

Manual checks show useful source-faithful translation quality:

- Gaffiot `arma`: weapons/arms senses surface clearly.
- Gaffiot `cano`: "to sing" appears in the translated entry.
- Gaffiot `vir`: "man" appears correctly when the query reaches `vir`.
- DICO `dharma`: law, duty, virtue, proper nature.
- DICO `agni`: fire plus Vedic/mythological detail with Sanskrit names intact.
- DICO `yoga`: means, union, concentration, spiritual discipline.
- DICO `karman`: act, action, rite, duty, accumulated merits/faults.

Limitations:

- live population can be slow for long entries;
- output is full dictionary-entry prose, not compact learner glosses;
- wrong headword routing still produces wrong translated evidence, e.g.
  `virumque` can route to `virus`.

## Next Steps

1. Add compact learner gloss derivation from translated DICO/Gaffiot witnesses.
2. Add batch cache warming for word lists and passage vocabulary.
3. Add cache hit/miss diagnostics in JSON/debug output.
4. Add timeout/chunking policy for long source entries.
5. Keep default `encounter` network-free; live translation remains explicit.
