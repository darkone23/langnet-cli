# Hydration and Reduction

Hydration means enriching already-stable claims or sense buckets with additional metadata.

Examples:

- CTS URN → author/work/title labels
- citation reference → source text location
- dictionary source reference → entry URL or display label

## Rule

Hydration must not change base claim IDs, witness IDs, or sense bucket IDs.

The same claims should reduce to the same buckets with or without hydration.

## Correct Order

```text
claims/triples
  → semantic reduction
  → optional hydration
  → learner display
```

Hydration may also run before display when it only adds metadata and does not alter grouping.

## Storage Policy

Store hydrated metadata separately from base evidence where possible. This allows hydration to be rebuilt without refetching dictionaries or recomputing claims.

## Non-Goals For Now

- broad citation UI
- passage context ranking
- source-text downloads during unit tests
