Fuzz Tool Validation Checklist

- Commands
  - Run `just autobot fuzz list` to confirm tool/action/lang defaults (Diogenes parse lat+grc, Whitaker search lat, Heritage morphology/canonical/lemmatize, CDSL lookup, CLTK morphology/dictionary).
  - Tool endpoints only: `just fuzz-tools` (only /api/tool/*, saves to examples/debug/fuzz_results).
  - Unified query endpoint only: `just fuzz-query` (only /api/q, saves to examples/debug/fuzz_results_query).
  - Side-by-side comparison (hits both): `just fuzz-compare` if you want to check unified sources after tools.

- Outputs
  - Tool fuzz: `examples/debug/fuzz_results/` with one JSON per target plus `summary.json`.
  - Query fuzz: `examples/debug/fuzz_results_query/` with one JSON per target plus `summary.json`.
  - Spot-check a few files: Diogenes search lat lupus, Heritage morphology agni, Whitaker search amo; ensure raw payloads are non-empty and pedagogically meaningful.

- Server dependency
  - Ensure `http://localhost:8000` is up; if failures look like connection refused or stale modules, run `just restart-server` then rerun fuzz.

- Compare expectations (for `fuzz-query` / `fuzz-compare`)
  - Optional sources (CDSL/CLTK) are marked compare-optional; status may show `skip` or `optional-missing` until unified adapters emit those sources.

- Coverage sanity
  - Verify Greek/Latin Diogenes parses (e.g., logos, anthropos, agathos/lego) complete without errors.
  - Heritage canonical/lemmatize should not crash even if shapes evolve.

- Artifacts for review
  - Use the relevant `summary.json` to guide manual review; prioritize any rows with `tool_ok=false`, `unified_error`, or `source_present=false` (when running compare).

- Future fixes (optional)
  - If desired, wire CDSL/CLTK into unified query to eliminate compare skips.
  - If compare shapes change, adjust `compare_optional` flags in `.justscripts/fuzz_tool_outputs.py`.
