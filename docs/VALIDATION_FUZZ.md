Fuzz Tool Validation Checklist

- Commands
  - Run `just autobot fuzz list` to confirm tool/action/lang defaults (Diogenes search/parse lat+grc, Whitaker search lat, Heritage full stack, CDSL lookup, CLTK morphology/parse/dictionary).
  - Run `just fuzz-all` (alias for `just autobot fuzz run --validate --compare --save examples/debug/fuzz_results`).

- Outputs
  - Expect `examples/debug/fuzz_results/` with one JSON per target plus `summary.json`.
  - Spot-check a few files: Diogenes search lat lupus, Heritage morphology agni, Whitaker search amo; ensure raw payloads are non-empty and pedagogically meaningful.

- Server dependency
  - Ensure `http://localhost:8000` is up; if failures look like connection refused or stale modules, run `just restart-server` then rerun fuzz.

- Compare expectations
  - Optional sources (CDSL/CLTK, Heritage entry) are marked compare-optional; status may show `skip` or `optional-missing` until unified adapters emit those sources.

- Coverage sanity
  - Verify Greek Diogenes search/parse (e.g., logos, anthropos, agathos/lego) complete without errors.
  - Heritage canonical/lemmatize/entry should not crash even if shapes evolve; empty entry responses are allowed.

- Artifacts for review
  - Use `examples/debug/fuzz_results/summary.json` to guide manual review; prioritize any rows with `raw_ok=false` or `compare_error` (should be none after a clean run).

- Future fixes (optional)
  - If desired, wire CDSL/CLTK into unified query to eliminate compare skips.
  - If compare shapes change, adjust `compare_optional` flags in `.justscripts/fuzz_tool_outputs.py`.
