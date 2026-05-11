# Getting Started

`langnet-cli` is a local CLI for classical-language lookup and morphology. The reliable interface today is the command line.

## Environment

```bash
# Enter the project environment
devenv shell

# Or run one command through just
just cli lookup lat lupus --output pretty
```

Most project recipes enter the environment through local wrappers, so from the repo root this is usually enough:

```bash
just cli --help
just lint-all
just test-fast
```

Routine recipes run through local wrapper scripts and should be audited
sequentially. Keep Diogenes, Heritage, and other live services running in your
process-compose session; LangNet recipes are clients/readiness probes rather
than the service supervisor.

## External Services

Live lookup depends on local tools that are not bundled with the repo.

| Tool | Languages | Requirement |
| --- | --- | --- |
| Diogenes | Latin, Greek | server at `localhost:8888` |
| Whitaker's Words | Latin | binary at `~/.local/bin/whitakers-words` |
| Sanskrit Heritage Platform | Sanskrit | server at `localhost:48080` |
| CDSL DuckDB data | Sanskrit | built with `just cli-databuild ...` when needed |
| CLTK data | Latin, Greek utilities | uses `CLTK_DATA` when set; otherwise prefers writable `~/cltk_data`, then `data/cache/cltk_data` |

If a service is unavailable, `lookup` should return a per-tool error rather than hiding the failure.

## Core Commands

```bash
just cli lookup lat lupus --output pretty
just cli lookup grc λόγος --output pretty
just cli lookup san agni --output pretty

just cli encounter san dharma all --no-cache --max-buckets 3
just cli encounter san agni heritage --no-cache

just cli parse whitakers lat amarem --format json
just cli parse diogenes lat lupus --format pretty

just cli normalize san agni
just cli plan lat lupus
just cli plan-exec lat lupus
just triples-dump lat lupus whitakers

just cli encounter lat arma gaffiot
just cli encounter san dharma dico

just cli word-of-day san --output json
just cli recommend-words lat --count 3

just cli reader-eval --limit 3 --translation-mode cache
```

## Command Reference

| Command | Purpose |
| --- | --- |
| `lookup` | Backend-keyed word lookup for users and debugging. |
| `parse` | Direct parser/debug entrypoint for one backend. |
| `normalize` | Show canonical query normalization. |
| `plan` | Build the tool-plan DAG without executing it. |
| `plan-exec` | Run normalize → plan → fetch/extract/derive/claim. |
| `triples-dump` | Print claim triples and evidence for inspection. |
| `encounter` | Current learner-facing MVP: reduced meaning buckets plus source-backed analysis. |
| `word-of-day` | Recommend learner words with terse glosses, learner notes, and verified encounter summaries when available. |
| `recommend-words` | Alias-style recommendation command for requesting several learner word cards on demand. |
| `reader-eval` | Run reader-oriented fixture checks against live encounter reductions. |
| `translation-warm` | Explicitly warm DICO/Gaffiot translation cache rows from a word list. |
| `databuild` | Build local data/indexes. |
| `index` | Inspect or manage storage indexes/caches. |

Run `just cli COMMAND --help` for options.

## DICO/Gaffiot Translations

DICO and Gaffiot entries are French source evidence. English translations are
derived evidence stored in the local translation cache.

```bash
# Read exact cache hits only; no network call.
just cli encounter lat cano gaffiot
just cli encounter san karman dico

# Explicitly populate missing rows through OpenRouter, then display them.
just cli encounter lat cano gaffiot --translation-mode auto
just cli encounter san karman dico --translation-mode auto

# Warm a word list ahead of learner lookup.
just cli translation-warm lat examples/debug/latin_words.txt --tool-filter gaffiot
```

`--translation-mode auto` requires `OPENAI_API_KEY` only when a cache miss must
be translated. Routine learner lookup should stay cache-backed and network-free.

## Validation

```bash
just lint-all
just test-fast
just validate-stabilization
```

Use targeted tests during development:

```bash
just test tests.test_whitakers_triples
just test tests.test_cdsl_triples
```

## Common Problems

- **No backend data**: confirm Diogenes, Heritage, and Whitaker are installed/running.
- **Sanskrit meanings vs analysis**: Heritage is the preferred Sanskrit analysis/morphology source; CDSL and DICO supply dictionary/source glosses. Use `encounter san <word> all` for the composed view.
- **CLTK unavailable**: install required CLTK model data and ensure `CLTK_DATA` points to a writable directory.
- **Stale server behavior**: restart long-running processes after code changes; Python modules are cached in running servers.
- **Need provenance**: use `plan-exec` or `triples-dump`, not only `lookup --output pretty`.
- **Long source entries**: compact display lines are summaries. Use `--output json` to inspect `source_text`, `source_text_chars`, `evidence_length_note`, and per-entry metadata.
