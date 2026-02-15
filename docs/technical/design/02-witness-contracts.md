# Source Contracts and Evidence Policy

## Status

**Draft – Target for Stabilization**  
**Last Updated**: 2026-02-15  
**Implementation Note**: Source contracts require schema evolution (see below)

## Purpose

This document defines source-level contracts for all upstream providers used by the CLI pipeline. It standardizes:

* What each source is trusted for
* What each source is not trusted for
* How each source is cited (IDs, anchors, resolvers)
* How conflicts are represented (not “resolved” by deletion)
* Minimum metadata required for reproducibility

This document is normative for schema v1 `provenance`, `citations`, and `witnesses`.

---

## 1. Definitions

### Source

An upstream provider of lexical/morphological evidence (e.g., MW via CDSL, Diogenes, Heritage).

### Witness

A specific evidence unit produced by a source (dictionary entry, sense line, morphology analysis, CTS passage).

### Claim (future layer)

A normalized statement derived from a witness (e.g., `pos=noun`, `sense="auspicious"`). Claim generation must not destroy witness traceability.

---

## 2. Global Rules

### R1 — No Unattributed Facts

All outputs that assert anything semantic, morphological, or bibliographic must carry at least one `witness`.

### R2 — Conflicts Are Represented, Not Erased

If sources disagree on POS, sense grouping, or morphology:

* represent multiple hypotheses
* preserve all witnesses
* do not “pick one” unless a mode-specific policy explicitly allows it

### R3 — IDs Must Be Stable

Every witness reference must use a stable locator when available:

* CTS URN
* dictionary entry ID
* source-native key (Heritage morph key, etc.)

### R4 — Mode Affects Presentation, Not Evidence

`--mode open|skeptic` may change:

* which witnesses are surfaced by default
* how aggressively senses are merged
  It must not:
* drop provenance
* drop citations
* change core IDs for the same underlying witness

---

## 3. Source Registry

### 3.1 Diogenes (Greek/Latin lexica + text infrastructure)

**Primary responsibilities**

* Dictionary blocks for Greek/Latin (e.g., LSJ)
* Strong anchoring to structured text traditions where available

**Trusted for**

* Lexicon text payloads
* Dictionary entry structure (as provided)
* Citation references when directly embedded (IDs, anchors)

**Not trusted for**

* Uniform POS taxonomy across lexica
* Complete deduplication of senses/citations without post-processing

**Witness shape (recommended)**

```json
{
  "source": "Diogenes",
  "type": "dictionary_entry",
  "ref": "lsj:<ENTRY_ID_OR_LOCATOR>",
  "raw_hint": {"headword": "..."}
}
```

**Known failure modes**

* Duplicate senses/citations across extraction paths
* Inconsistent formatting across lexica

---

### 3.2 Perseus / CTS (Canonical Text Services identifiers)

**Primary responsibilities**

* CTS URN identity for passages and works
* Stable bibliographic addressing

**Trusted for**

* URN identity and canonical references
* Work-level metadata when available

**Not trusted for**

* “Best” citation formatting for learners (requires downstream formatting rules)

**Witness shape**

```json
{
  "source": "Perseus",
  "type": "cts",
  "ref": "urn:cts:latinLit:phi0119.phi008"
}
```

**Resolvers**

* CTS → Perseus Catalog (via resolver strategy; implementation-defined)

---

### 3.3 Whitaker’s Words (Latin morphology / lemma support)

**Primary responsibilities**

* Latin morphology analyses
* Fast lemma candidates for Latin inputs

**Trusted for**

* Morphological analyses for Latin forms
* Lemma suggestions (as hypotheses)

**Not trusted for**

* Pedagogically-curated senses (limited and not lexicon-grade)
* Citation identity (generally not a citation source)

**Operational contract**

* CLI must detect missing binary and emit a warning, not crash.
* A `verify`/health check must exist (implementation detail, but required behavior).

**Witness shape**

```json
{
  "source": "Whitaker",
  "type": "morphology",
  "ref": "whitaker:<RUN_ID_OR_HASH>",
  "raw_hint": {"input": "..."}
}
```

---

### 3.4 CLTK Backends (morphology + supplemental lexicon)

**Primary responsibilities**

* Supplemental morphology and lemma suggestions
* Backfill when primary sources are unavailable

**Trusted for**

* Morphological feature extraction (as hypothesis)
* Lightweight lexicon hints (non-authoritative)

**Not trusted for**

* Final semantic adjudication
* Canonical citation identity

**Witness shape**

```json
{
  "source": "CLTK",
  "type": "morphology",
  "ref": "cltk:<MODEL_ID>:<RUN_HASH>"
}
```

---

### 3.5 CDSL (Monier-Williams and related indices) – Sanskrit lexicon backbone

**Primary responsibilities**

* Sanskrit lexicon entries (MW via CDSL)
* Stable dictionary IDs used as witnesses for senses

**Trusted for**

* MW entry identity and lexicon content
* Dictionary IDs for citation to MW

**Not trusted for**

* Uniform transliteration in raw content (requires normalization policy)
* Learner-facing sense grouping (must be distilled)

**Normalization contract**

* Raw MW payload may be normalized to a canonical output (e.g., IAST)
* Normalization must not destroy the ability to link back to MW IDs

**Witness shape**

```json
{
  "source": "MW",
  "type": "dictionary_entry",
  "ref": "mw:<ENTRY_ID>"
}
```

---

### 3.6 Heritage (Sanskrit morphology + lexical hints)

**Primary responsibilities**

* Sanskrit morphology analyses from observed forms
* Additional lexical metadata where available

**Trusted for**

* Morphology observed on input forms (case/number/gender, etc.)
* Lemma linkage when explicitly provided

**Not trusted for**

* Complete lexicon coverage compared to MW
* Uniform POS taxonomy without mapping

**Witness shape**

```json
{
  "source": "Heritage",
  "type": "morphology",
  "ref": "heritage:morph:<KEY>"
}
```

**Known failure modes**

* Encoding/SLP1 issues in input; must surface warnings when normalization is uncertain.

---

### 3.7 Abbreviation Maps (rendering and pedagogy support)

**Primary responsibilities**

* Expanding abbreviations in lexicon payloads and morphology tags
* Rendering stable learner-facing labels

**Trusted for**

* Deterministic mapping of known abbreviation sets
* Supporting Foster functional labels downstream

**Not trusted for**

* Introducing new semantic content
* Overriding primary source information

**Witness shape**

```json
{
  "source": "AbbrevMap",
  "type": "mapping",
  "ref": "abbrev:<MAP_NAME>:<VERSION>"
}
```

---

### 3.8 Foster Mapping (functional grammar labels)

**Primary responsibilities**

* Mapping technical morphology → Foster functional descriptions
* Cross-language consistency in “function over form” labels

**Trusted for**

* Display-layer mapping only
* Deterministic label generation

**Not trusted for**

* Determining morphology features (depends on morphology sources)

**Witness shape**

```json
{
  "source": "FosterMap",
  "type": "rendering",
  "ref": "foster:<VERSION>"
}
```

---

### 3.9 DICO (planned) – Sanskrit translation / sense enrichment

**Primary responsibilities**

* Enrichment and alignment signals for sense bucketing (later phase)

**Trusted for**

* Supplemental evidence for clustering and translation support (once integrated)

**Not trusted for (initial integration)**

* Overriding MW/primary lexica
* Acting as sole witness for core senses

**Integration rule**

* DICO is enhancement, not prerequisite.
* DICO witnesses must always be labeled as secondary unless policy changes.

---

## 4. Conflict Handling Policy (Normative)

### POS conflicts

* Represent as `pos_hypotheses` or equivalent (schema-specific structure)
* Each hypothesis must list witnesses

### Sense overlap / merge disputes

* In `open` mode, merging is allowed if overlap thresholds are met (defined in bucketing doc)
* In `skeptic` mode, merging requires shared witness support or explicit primary lexicon agreement

### Morphology vs lemma POS

* Morphology analysis applies to the surface form only
* Lemma POS remains hypothesis-based and evidence-backed

---

## 5. Provenance Requirements

Every CLI response must include:

* tool name
* version
* timestamp (UTC)
* optional: runtime flags impacting output (mode, normalization settings)

Example:

```json
{
  "tool": "heritage_adapter",
  "version": "0.2.0",
  "timestamp": "2026-02-12T22:10:05Z",
  "config": {"mode": "open", "normalize": "iast"}
}
```

---

## 6. Implementation Reality

### **Current Architecture Gap**
These witness contracts assume granular source tracking at the sense level, but current `DictionaryDefinition` schema lacks `source_ref` field.

**Required Schema Evolution**:
```python
# In src/langnet/schema.py DictionaryDefinition
source_ref: str | None = None  # Required for witness contracts
```

### **Migration Strategy**
1. **Phase 0**: Add `source_ref` to schema (non-breaking)
2. **Phase 1**: Update CDSL adapter to populate from `sense_lines`
3. **Phase 2**: Gradually update other adapters
4. **Phase 3**: Implement witness contract validation

### **Temporary Workaround**
Until schema is enhanced, witness extraction will use:
- CDSL: Parse `sense_lines` from metadata
- Diogenes: Extract from `dictionary_blocks`
- Whitakers: Generate synthetic references
- Fallback: Entry-level source tracking only

## 7. Completion Criteria

* [ ] Schema enhanced with `source_ref` field
* [ ] CDSL adapter populates `source_ref` from sense lines
* [ ] All sources have an entry in this registry
* [ ] Every adapter emits witnesses using the agreed `source/type/ref` pattern
* [ ] Resolver strategy documented for each citation type
* [ ] CLI `--evidence` output lists witnesses grouped by source
* [ ] Missing critical dependencies emit warnings (not crashes)
