> Archived during the 2026-05 documentation overhaul. Retained for historical context; current planning guidance lives in docs/ROADMAP.md, docs/EXECUTION_PLAN.md, and the current active plans under docs/plans/active/.

# CTSv2 Reader Addressing Design

Generated: 2026-05-19

Implementation status: initial additive integration is underway in the active
reader stack. Current builds populate `works.canonical_text_id`, generated
CTSv2/source aliases, `source_witnesses`, and `work_relations`; reader lookups
accept CTSv2 resource addresses such as
`urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23`. Storage primary keys still
use existing `work_id` values for compatibility.

## Goal

Move the reader toward a LangNet-owned CTSv2 addressing system where canonical
reader IDs identify logical texts, while TLG, PHI, Perseus, First1KGreek, DCS,
GRETIL, and other source identifiers are preserved as metadata, aliases, and
source-witness links.

The design is intentionally flat and graph-based. It should not encode author,
genre, period, edition, or source hierarchy into the canonical ID.

## Motivation

The current reader accepts catalog-native `work_id`, CTS work URNs, and aliases.
That was enough to make the corpus usable, but it also inherited several source
catalog assumptions:

- TLG and PHI IDs look canonical even when they are only external authority IDs.
- CTS edition/version components are often used for materially different texts,
  recensions, selections, epitomes, codices, and abridgements.
- Source corpora sometimes model embedded or virtual texts as if they were
  ordinary works.
- Author-first hierarchy is brittle for anonymous, attributed, scholia,
  lexicon, anthology, and embedded-text material.
- Genre or period buckets are useful for browsing, but unsafe as identity
  claims.

LangNet needs stable reader IDs that say "this logical text" and nothing more.
Everything else should live in metadata or graph relations.

## Core Principle

IDs identify. Parameters address. Metadata describes. Relations structure.
Witnesses preserve provenance.

## Canonical Logical Text IDs

Canonical IDs use this shape:

```text
urn:ctsv2:<language>:<stable-text-slug>
```

Examples:

```text
urn:ctsv2:lat:aeneid-arma-virumque-cano
urn:ctsv2:grc:iliad-menin-aeide-thea
urn:ctsv2:grc:odyssey-andra-moi-ennepe
urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca
urn:ctsv2:grc:suda-alpha
```

The slug is text-centered. The normal preferred form is:

```text
<conventional-title>-<incipit-key>
```

The incipit key is a disambiguator, not a title claim. It should be generated
from cleaned text after stripping source headers, catalog preambles, boilerplate,
and non-textual notes. When the incipit is unstable or unsuitable, a curated
source-neutral disambiguator is allowed.

The canonical ID should not include:

- source authority IDs such as `tlg2200` or `phi0690`;
- author hierarchy;
- genre or category buckets;
- historical period buckets;
- edition/version/witness labels;
- citation references.

## Resource Addressing

The logical text ID identifies the node. Query parameters select a resource
projection or address within the node.

Preferred parameter names:

```text
ref=<citation>
range=<start>..<end>
witness=<source-witness-id>
source=<source-family>
layer=<text|translation|morphology|notes|classification>
script=<source|iast|devanagari|betacode|unicode>
```

Examples:

```text
urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23
urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca?ref=1.1
urn:ctsv2:grc:suda-alpha?ref=alpha.1
urn:ctsv2:lat:aeneid-arma-virumque-cano?ref=1.23&witness=phi0690.phi003
```

Avoid `edition=` as the default parameter name. The term has inherited too much
ambiguity from CTS1. If a caller needs a specific textual witness, use
`witness=`. If a caller needs a source family, use `source=`.

If strict URN tooling objects to query components, expose the same address as a
URI form while keeping the same conceptual contract:

```text
ctsv2://lat/aeneid-arma-virumque-cano?ref=1.23&witness=phi0690.phi003
```

## Source Witnesses

Every imported source row should preserve its original identifier as source
metadata. These are not canonical LangNet text IDs.

Examples:

```yaml
source_witnesses:
  - witness_id: phi0690.phi003
    source_family: phi
    source_urn: urn:cts:latinLit:phi0690.phi003
  - witness_id: perseus-grc-tlg9010-tlg001
    source_family: first1kgreek
    source_urn: urn:cts:greekLit:tlg9010.tlg001.1st1K-grc1
```

Source identifiers can also be registered as aliases or AKA names:

```yaml
aliases:
  - alias: urn:cts:latinLit:phi0690.phi003
    target: urn:ctsv2:lat:aeneid-arma-virumque-cano
    kind: source_urn
  - alias: phi0690.phi003
    target: urn:ctsv2:lat:aeneid-arma-virumque-cano
    kind: external_authority_id
```

## Logical Text Versus Witness

Minor editorial variation remains the same logical text with multiple witnesses.
Material change of textual identity or extent gets explicit modeling.

Same logical text:

- punctuation or orthography changes;
- line numbering differences;
- minor variant readings;
- editorial apparatus differences;
- source-specific segmentation differences.

Separate logical text or explicit relation:

- recension;
- epitome;
- abridgement;
- selection;
- excerpt;
- contained text with stable reader identity;
- codex-specific text that materially differs;
- anthology item treated as a distinct text.

The builder should never decide this solely from CTS dotted components. It should
classify source candidates into LangNet reader concepts.

## Graph Relations

The data model should support explicit relations between logical texts, source
witnesses, structure nodes, people, and collections.

Initial relation types:

```text
source_witness_of
same_as
contains
contained_in
part_of
member_of
selection_of
epitome_of
recension_of
translation_of
supersedes
attributed_to
```

These relations should carry provenance and confidence. They should be queryable
but should not be inferred from URN paths.

## ToC And Embedded Text Pattern

The existing `contained_works` and `work_map_nodes` tables are the first version
of this pattern:

- `contained_works` exposes reader-facing embedded texts such as the
  Bhagavadgita inside the Mahabharata.
- `work_map_nodes` exposes navigational structure such as chapters, books, and
  sections.

CTSv2 should make that distinction foundational:

- a logical text can be contained inside another logical text;
- a structure node is a range inside a text, not automatically another work;
- a source witness can map to a range in a parent source;
- a source witness can map directly to a child logical text;
- a visible reader catalog should be produced from accepted logical-text
  resolution, not from raw source IDs.

For Bhagavadgita, the logical text should be a CTSv2 node:

```text
urn:ctsv2:san:bhagavadgita-dhrtarastra-uvaca
```

It should map to the Mahabharata source range that begins with the opening
`dhrtarastra uvaca` segment. The current curated range should be audited because
it may start too late.

For Libanius, First1KGreek split works such as `tlg2200.tlg00401` should be
treated as source witnesses or candidate logical child texts, not blindly as
canonical LangNet IDs. If accepted, they should resolve to stable CTSv2 IDs
whose relation to the aggregate oration/declamation source is explicit.

## Category, Author, And Time

Author, category, and period are metadata facets, not ID hierarchy.

This avoids forcing texts into brittle boxes:

- anonymous works;
- disputed authorship;
- lexica;
- scholia;
- anthologies;
- commentaries;
- embedded canonical texts;
- multi-author or tradition-owned texts.

Category buckets still matter for discovery and clipping, but they should be
metadata queries:

```text
language = san AND category CONTAINS epic
language = grc AND category CONTAINS lexicon
relation ancestor = urn:ctsv2:san:mahabharata-...
```

They should not be URN prefixes.

## Build-Time Resolution

The reader build should eventually follow this staged flow:

```text
source files
  -> parsed source witnesses
  -> source candidate records
  -> logical text resolution
  -> relation and structure overlays
  -> visible reader catalog
  -> search/index artifacts
```

Key rules:

- exact same logical text should produce one visible reader work;
- lower-priority source witnesses should be retained as metadata or suppressed
  from the visible catalog, not exposed as duplicates;
- TLG/PHI/Perseus/First1K IDs should become aliases and source-witness records;
- aggregate/subwork cases should become explicit graph relations;
- destructive suppression should require either exact logical identity or an
  accepted relation, not identifier shape alone.

## Migration Strategy

Phase 1: Add CTSv2 metadata without changing current IDs.

- Add `canonical_text_id` / CTSv2 field to work metadata.
- Register TLG/PHI/Perseus/First1K/DCS/GRETIL IDs as source aliases.
- Keep existing `work_id` lookups working.
- Add validation for duplicate `canonical_text_id` among visible works.

Phase 2: Add resolver support.

- Resolve CTSv2 IDs in `reader contents`, `reader show`, and API routes.
- Support query-style addressing for `ref`, `range`, and `witness`.
- Preserve old `work_id` and CTS1 behavior as aliases.

Phase 3: Move catalog identity.

- Make CTSv2 the preferred reader-facing identifier.
- Keep old `work_id`, `cts_work_urn`, TLG/PHI, and source URNs as AKA names.
- Update generated search indexes and UI links to prefer CTSv2.

Phase 4: Source preference and relation-aware imports.

- Integrate First1KGreek as source witnesses.
- Prefer accepted First1KGreek witnesses over legacy TLG for exact logical text
  matches when quality checks pass.
- Model aggregate/subwork patterns as relations rather than duplicates.
- Rebuild search from the deduped logical catalog.

## Validation Requirements

The catalog validator should report:

- visible duplicate logical text IDs;
- aliases that target missing logical text IDs;
- source witnesses with no linked logical text;
- material source variants lacking a relation type;
- contained texts with missing or invalid parent mapping;
- work-map nodes whose ranges do not resolve;
- source headers/preambles leaking into incipit extraction;
- suspect incipit keys generated from non-textual material.

## Open Questions

- Exact transliteration policy for incipit keys across Greek, Latin, Sanskrit,
  and future languages.
- Maximum incipit key length and collision policy.
- Whether canonical CTSv2 IDs should be stored directly in `works.work_id` or in
  a new `canonical_text_id` column during migration.
- Whether strict URN strings with query components are acceptable everywhere, or
  whether API-facing resource links should use `ctsv2://`.
- How much source-witness data should be exposed to downstream consumers by
  default versus behind a metadata/detail endpoint.

## Near-Term Candidate Work

1. Done: audit the Bhagavadgita contained range and adjust it to begin at
   `dhrtarastra uvaca` if the current range starts too late.
2. Add a small CTSv2 registry/metadata fixture for a few known texts:
   Bhagavadgita, Aeneid, Iliad, Odyssey, Suda.
3. Done: add catalog validation for duplicate canonical logical text IDs.
4. Done: extend alias registration so TLG/PHI/First1K/source URNs resolve as AKA
   names for canonical CTSv2 IDs.
5. Done: design First1KGreek import as source-witness ingestion plus logical-text
   resolution, not direct source-ID catalog registration.
