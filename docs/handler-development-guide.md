# Handler Development Guide

Handlers turn backend output into staged effects and claims.

## Handler Stages

Most real backends use three stages:

```text
raw response → extraction → derivation → claim
```

### Extract

`extract_*` decodes raw backend output into a structured payload.

Expected inputs:

- `ToolCallSpec`
- `RawResponseEffect`

Expected output:

- `ExtractionEffect`

Keep raw response references and enough parsed structure to reproduce downstream derivations.

### Derive

`derive_*` normalizes extraction payloads into tool-specific facts.

Expected inputs:

- `ToolCallSpec`
- `ExtractionEffect`

Expected output:

- `DerivationEffect`

Add provenance pointing back to the extraction and response.

### Claim

`claim_*` projects derivations into stable claims/triples.

Expected inputs:

- `ToolCallSpec`
- `DerivationEffect`

Expected output:

- `ClaimEffect`

Claims should be suitable input for semantic reduction.

## Versioning

Use `@versioned("vN")` on handlers. Bump the version when output semantics change in a way that should invalidate cached extraction, derivation, or claim rows.

Examples:

- Parser bug fix with same payload shape: version bump may be optional.
- New field added to claim payload: bump.
- Anchor/predicate semantics changed: bump.

## Evidence Rules

Each claim should preserve:

- `call_id`
- `response_id` where available
- `extraction_id`
- `derivation_id`
- `claim_id`
- `source_ref` where a stable dictionary/source ID exists
- `raw_blob_ref` for raw payload location

For triples, put this under `metadata.evidence`.

Do not put evidence into `subject` or `object` IDs.

## Anchor Rules

Use stable, readable anchors:

- `form:<surface>`
- `interp:<form>→<lexeme>`
- `lex:<lemma>` or `lex:<lemma>#<pos>`
- `sense:<lex>#<hash>`

Ambiguous forms should link to scoped interpretations. Senses should attach to lexemes/sense nodes, not directly to a surface form.

## Tests

Every handler change should have a service-free fixture test.

Use helpers from `tests/claim_contract.py`:

- `make_call`
- `assert_claim_contract`
- `claim_triples`
- `find_triple`

Good examples:

- `tests/test_whitakers_triples.py`
- `tests/test_cdsl_triples.py`
- `tests/test_claim_contracts.py`

Run:

```bash
just test tests.test_claim_contracts
just lint-all
```

## Registration

Handlers are wired through the execution registry. When adding a backend:

1. Add fetch/client behavior or a stub.
2. Add extract/derive/claim functions.
3. Register them in the default registry.
4. Add planner coverage if the tool should be selected automatically.
5. Add fixture tests before relying on live services.

## Checklist

- Handler has a clear stage boundary.
- Handler is versioned.
- Payload preserves raw/source references.
- Claims include evidence.
- Triples use canonical predicates where possible.
- Tests do not require live services.
- `just lint-all` and targeted tests pass.
