# Pedagogical TODO & Roadmap (concise)
Priorities drawn from `docs/PEDAGOGICAL_PHILOSOPHY.md` and current code. Use this as the living shortlist.

## P0 (do now)
- Fix CTS URN citations (diogenes → normalized URNs).
- Wire Sanskrit canonical forms end-to-end (sktsearch in normalization/tools).

## P1 (high impact)
- Diogenes sense extraction quality (drop noisy “about this usage”).
- Heritage citation abbreviations (use upstream ABBR list).

## P2 (medium)
- Universal schema refinements (clean mapping/grouping; trim pointless fields).
- CDSL SLP1 encoding cleanup (transliterate/replace valid Sanskrit terms).

## P3 (dev/pedagogy polish)
- Standardize tool debug interface (passthrough JSON + verbs).
- Complete functional grammar mapping coverage.

## P4 (longer term)
- DICO dictionary integration.
- Web UI for manual fuzzing/UX.
### Immediate (P0):
1. **@coder**: Fix CTS URN citation parsing in `src/langnet/diogenes/core.py:300-323`
2. **@coder**: Wire sktsearch into normalization pipeline (`src/langnet/normalization/core.py`)

### Short-term (P1):
3. **@sleuth**: Debug diogenes sense extraction (`src/langnet/diogenes/core.py:274-297`)
4. **@coder**: Integrate abbreviation list from `docs/upstream-docs/skt-heritage/ABBR.md`

### Medium-term (P2):
5. **@architect**: Design automated SLP1 transliteration pipeline
6. **@artisan**: Refactor universal schema for hierarchical organization

## Related Existing Plans
- `docs/plans/todo/diogenes/REMOVE_UNRELIABLE_SENSES.md`
- `docs/plans/todo/normalization/CANONICAL_QUERY_NORMALIZATION_TODO.md`
- `docs/plans/todo/dico/DICO_INTEGRATION_PLAN.md`

## Success Metrics
- **Educational**: Citations show proper CTS URNs, Sanskrit inflected forms resolve to lemmas
- **Technical**: Sense extraction reliability > 95%, schema consistency across tools
- **User Experience**: CLI tools provide consistent JSON output, web UI enables manual fuzzing

## Closeout criteria (move this roadmap to completed)
- P0 and P1 items above shipped with tests/docs; CTS URN parsing and Sanskrit canonical wiring verified.
- Fuzz/spot outputs captured to prove sense extraction + schema consistency did not regress.
- Abbreviation list wired or explicitly deferred in docs with rationale.
- `docs/plans/README.md` updated to move this file into `completed/roadmap/` once checks pass.
