# Entry Parsing

Entry parsing turns dictionary-like text or HTML into structured extraction payloads.

## Current Use

Parsers support:

- Diogenes dictionary HTML
- Whitaker line groups
- CLTK Lewis lines
- CDSL XML-ish body fields
- Heritage HTML morphology snippets

## Design Rules

- Preserve raw text/HTML references.
- Prefer partial structured output over total failure.
- Keep parser-specific quirks inside extract/derive handlers.
- Do not force every backend into the same raw parser schema; normalize at claim/triple projection.

## Testing

Parser tests should use realistic fixture strings. Live backends are not required for parser correctness.

## Relationship To Semantic Reduction

Entry parsing is upstream. Semantic reduction should not consume parser internals directly. It should consume claims/triples derived from parsed entries.
