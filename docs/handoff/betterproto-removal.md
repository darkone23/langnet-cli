# Handoff: Remove betterproto2/pydantic from langnet-cli

## Why
- CLI startup is slowed by `betterproto2` → `pydantic` imports (plus typing_extensions/typing_inspection). Even with cache hits, `langnet-cli normalize …` spends ~0.5–0.6s in import overhead.
- We want pydantic-free generated types; simple dataclasses + cattrs/orjson (or plain protobuf) are sufficient for our use and would cut import cost.

## Current State
- Runtime no longer imports `betterproto2`/pydantic. We replaced the `query_spec` and `heritage_spec` imports with lightweight dataclass implementations in `src/query_spec.py` and `src/heritage_spec.py` (orjson serialization, enum helper).
- Storage + planner now rely on the new dataclasses (`from_json`/`to_json` implemented with sorted keys) so plan hashes and cache rows are deterministic without the generated code.
- Tests now import the local modules directly; vendor `langnet-spec` is still present for schema reference/codegen but not required at runtime.

## Target Direction (proposed)
- Keep runtime on the lightweight dataclasses for now; if we still want protobuf parity, add a pydantic-free generator path in `vendor/langnet-spec` (standard `--python_out` is fine) for cross-language artifacts.
- Remove `betterproto2` references from the vendor tooling/README if we no longer intend to generate those bindings.

## Suggested Migration Steps
1) Optional: add `generate-python-protobuf` in `vendor/langnet-spec/justfile` for consumers who still want protobuf artifacts (standard `protoc --python_out`).
2) If we decide to keep only the local dataclasses, trim `vendor/langnet-spec/README.md`/justfile to drop `betterproto2` mention and remove its deps from `vendor/langnet-spec/pyproject.toml` / `uv.lock`.
3) If protobuf bindings are still desired, add a small adapter in `src/query_spec.py` to convert to/from the protobuf classes so callers can choose either representation.
4) Consider a one-time migration if we need to read old cache rows written by betterproto JSON (current caches will be regenerated on miss).

## Open Questions
- Do we still need protobuf artifacts for cross-language work? If so, add the standard generator; otherwise prune vendor dependencies.
- Do we need to migrate old cache rows? (Current approach regenerates caches as needed; we can add a compatibility loader if required.)

## Artifacts to Inspect
- `src/query_spec.py` (new dataclasses + serde)
- `src/heritage_spec.py` (Heritage response dataclasses)
- `vendor/langnet-spec/justfile` (codegen commands) if we still need protobuf generation

## Ready-to-Run Checks
- `python -m nose2 -s tests test_normalizer_cache` for cache behavior; `python -m nose2 -s tests test_plan_execution` for planner/store round-trips.
- `time just cli normalize grc thea` to validate startup improvement (should no longer import pydantic/betterproto2).
