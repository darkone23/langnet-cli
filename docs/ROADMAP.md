# ROADMAP.md

# LangNet CLI – Engineering Roadmap

## Status

Active Development

## Purpose

This document defines the phased engineering plan for stabilizing and expanding the LangNet CLI into a deterministic, pedagogically-oriented semantic lexicon engine.

The roadmap is structured around:

1. Architectural stabilization
2. Semantic distillation
3. CLI contract hardening
4. Pedagogical surfacing
5. Source expansion and enrichment
6. Performance and resilience

All milestones assume adherence to:

* Schema v1 Specification
* Source Contracts Specification
* Semantic Distillation & Constant Design

---

# Phase 1 – Architectural Stabilization (Foundation)

**Objective:** Freeze structural contracts before expanding features.

---

## 1.1 Schema v1 Finalization

* [ ] Implement Schema v1 JSON validator
* [ ] Ensure all CLI `--json` outputs conform
* [ ] Add regression snapshot tests
* [ ] Expose `schema_version` in output
* [ ] Ensure Avro/typed mapping compatibility

---

## 1.2 Source Adapter Contracts

Formalize per-source behavior:

* [ ] Diogenes adapter stability pass
* [ ] CDSL (MW) adapter normalization review
* [ ] Heritage adapter guardrails for mangled SLP1
* [ ] CLTK backend consistency check
* [ ] Abbreviation map versioning
* [ ] Foster mapping versioning

Required:

* Stable `source/type/ref` witness format
* No silent evidence loss

---

## 1.3 CLI Contract Hardening

Define stable behaviors:

* [ ] `lookup WORD`
* [ ] `lookup WORD --json`
* [ ] `lookup WORD --mode open`
* [ ] `lookup WORD --mode skeptic`
* [ ] `lookup WORD --evidence`
* [ ] `lookup WORD --links`

Mode must not alter schema shape.

---

## 1.4 Output Ordering + Snapshot Tests

Standardize didactic output order:

```
Head → Senses → References → Foster Features
```

* [ ] Add regression snapshots
* [ ] Prevent accidental reordering

---

## 1.5 Tool Availability & Verification

* [ ] Whitaker binary detection
* [ ] CLI `verify` hook
* [ ] Clear error messaging if unavailable
* [ ] Non-fatal failure policy for optional sources

---

# Phase 2 – Semantic Distillation Engine

**Objective:** Implement deterministic bucketing and constant registry.

---

## 2.1 Witness Extraction (All Sources)

* [ ] LSJ via Diogenes
* [ ] MW via CDSL
* [ ] Lewis lines via CLTK (Latin)
* [ ] Perseus CTS anchors
* [ ] Heritage morphology as WSUs (where applicable)

Ensure:

* Stable `sense_ref`
* Deterministic extraction

---

## 2.2 Bucketing Engine

* [ ] Implement WSU similarity scoring
* [ ] Deterministic clustering
* [ ] Mode-dependent merge thresholds
* [ ] Confidence scoring
* [ ] Stable `sense_id` generation

---

## 2.3 Semantic Constant Registry

* [ ] Implement constant registry store
* [ ] Matching policy (choose from known constants)
* [ ] Provisional constant creation
* [ ] Status field (`provisional` / `curated`)
* [ ] Constant ID stability guarantees

---

## 2.4 Reduction Pipeline (“Spine of Meaning”)

* [ ] Detect overlapping glosses
* [ ] Reduce redundant senses
* [ ] Identify semantic expansion/drift
* [ ] Ensure minor technical senses collapsible via `ui_hints`

---

## 2.5 Conflict Representation

* [ ] POS hypotheses with confidence
* [ ] Morphology observed vs lemma-level POS separation
* [ ] No evidence suppression in skeptic mode

---

# Phase 3 – Pedagogical Surface Layer

**Objective:** Stabilize learner-facing output without sacrificing evidence.

---

## 3.1 Didactic View Layer

Derived from Schema v1:

* [ ] Most likely lemma
* [ ] Top 3–7 buckets
* [ ] Semantic constant alignment (if assigned)
* [ ] Morphology summary
* [ ] Warning notes

---

## 3.2 Foster Functional Grammar Integration

* [ ] Unified mapping across Latin/Greek/Sanskrit
* [ ] Display format: “Technical Term (Functional Label)”
* [ ] Extend Foster enrichment to:

  * Heritage
  * Diogenes where metadata allows
* [ ] Document fallback behavior

---

## 3.3 Citation UI Plan

* [ ] Stable citation object model
* [ ] CTS URN formatting
* [ ] DuckDuckGo `!ducky` resolver strategy
* [ ] Outbound DCS search links (Sanskrit)
* [ ] `--links` CLI flag implementation

---

## 3.4 Example Passage Engine

* [ ] Surface 1–3 short passages per major sense
* [ ] Keep snippets skimmable
* [ ] Preserve CTS URN traceability
* [ ] Avoid long raw dumps

---

# Phase 4 – Schema Convergence & Universal Structure

**Objective:** Minimize branching across languages.

---

## 4.1 Universal Morphology Schema

* [ ] Align morphology structures for Latin/Greek/Sanskrit
* [ ] Normalize case/number/gender feature keys
* [ ] Make POS plural-capable (noun, adjective, masc/fem/etc.)
* [ ] Ensure consistent JSON typing

---

## 4.2 LexemeCore / Claim Model (Internal Layer)

Introduce structured claim representation:

* [ ] Define semantic atom
* [ ] Implement Claim object (subject/predicate/value/witness)
* [ ] Map bucket results into claims
* [ ] Preserve witness traceability

This layer must not break Schema v1.

---

# Phase 5 – Source Expansion & Enrichment

**Objective:** Enhance semantic evidence without destabilizing core.

---

## 5.1 DICO Integration

* [ ] Basic parser
* [ ] Extraction pipeline
* [ ] DuckDB-backed adapter
* [ ] Fuzz snapshot tests
* [ ] Treat as secondary evidence initially

DICO enhances distillation; it is not a prerequisite.

---

## 5.2 CDSL Normalization Improvements

* [ ] Normalize to IAST
* [ ] Document normalization contract
* [ ] Preserve source ID fidelity

---

## 5.3 Cross-Lexicon Etymology (Deferred)

* [ ] Investigate cross-language constant alignment
* [ ] Map constants to etymological clusters
* [ ] Do not block v1 stabilization

---

# Phase 6 – Fuzzy Search & Robustness

**Objective:** Improve resilience for real-world input.

---

## 6.1 Fuzzy Search

* [ ] Accent tolerance
* [ ] Encoding normalization (SLP1/IAST)
* [ ] Minor spelling variance handling
* [ ] Cross-language tolerant lookup

Must not introduce nondeterminism in bucket IDs.

---

## 6.2 Encoding Guardrails

* [ ] Mangled SLP1 detection
* [ ] Unicode normalization enforcement
* [ ] Explicit warnings when ambiguity detected

---

# Phase 7 – Performance & Observability

**Objective:** Ensure responsiveness and regression visibility.

---

## 7.1 Caching Strategy

* [ ] Cache hot MW headwords
* [ ] Cache Whitaker inflection tables
* [ ] Cache LSJ entries
* [ ] Mode-specific cache keys

---

## 7.2 Timing Instrumentation

* [ ] Add `timing_ms` to provenance
* [ ] Track per-source latency
* [ ] Detect regressions via benchmarks

---

# Phase 8 – CLI Stability Milestone

**Target:** Stable 1.0 CLI contract.

Requirements:

* [ ] Schema v1 frozen
* [ ] Deterministic bucketing
* [ ] Semantic constants operational
* [ ] Source contracts enforced
* [ ] CLI modes stable
* [ ] 60+ regression snapshot coverage
* [ ] Performance baseline documented

---

# Non-Goals (Pre-1.0)

* Full semantic ontology curation
* Cross-language philosophical mapping
* Aggressive gloss paraphrasing
* Replacing primary lexica with AI summarization

---

# Guiding Engineering Principles

1. Determinism over cleverness
2. Traceability over summarization
3. Constants over strings
4. Stability before expansion
5. Presentation must not alter evidence
