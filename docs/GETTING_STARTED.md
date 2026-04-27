# Getting Started

`langnet-cli` is a local CLI for classical-language lookup and morphology. The reliable interface today is the command line.

## Environment

```bash
# Enter the project environment
devenv shell

# Or run one command through just
just cli lookup lat lupus --output pretty
```

Most project recipes already enter `devenv shell`, so from the repo root this is usually enough:

```bash
just cli --help
just lint-all
just test-fast
```

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

devenv shell -- bash -c 'langnet-cli encounter san dharma all --no-cache --max-buckets 3'
devenv shell -- bash -c 'langnet-cli encounter san agni heritage --no-cache'

just cli parse whitakers lat amarem --format json
just cli parse diogenes lat lupus --format pretty

just cli normalize san agni
just cli plan lat lupus
just cli plan-exec lat lupus
just triples-dump lat lupus whitakers
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
| `databuild` | Build local data/indexes. |
| `index` | Inspect or manage storage indexes/caches. |

Run `just cli COMMAND --help` for options.

## Validation

```bash
just lint-all
just test-fast
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
