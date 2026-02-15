# Semantic Distillation, Sense Bucketing, and Constant Assignment Design

## Status

**Draft – Target for Stabilization**  
**Last Updated**: 2026-02-15  
**Implementation Reality Check**: See "Current Architecture Gap" section below

## Purpose

This document specifies the semantic distillation pipeline that converts raw lexical evidence into structured semantic output suitable for:

* Stable JSON (`senses[]` in Schema v1)
* Didactic CLI rendering
* Evidence inspection (`--evidence`)
* Epistemic mode variation (`open` vs `skeptic`)
* Gradual construction of a curated semantic constant registry

This document defines:

* Witness extraction
* Clustering (sense bucketing)
* Semantic constant assignment
* Deterministic behavior guarantees
* Mode-dependent strictness rules
* Testing and stability requirements

---

# 1. Conceptual Layers

The system distinguishes four semantic layers:

| Layer                    | Definition                            | Stability           |
| ------------------------ | ------------------------------------- | ------------------- |
| Witness Sense Unit (WSU) | Source-derived minimal sense evidence | Source-stable       |
| Bucket                   | Cluster of related WSUs               | Algorithm-stable    |
| Semantic Constant        | Stable semantic identifier            | Registry-stable     |
| Display Gloss            | Human-readable description            | Presentation-stable |

These layers must not be conflated.

## Current Architecture Gap

**Important**: This design assumes data structures that do not fully match current implementation.

### **Design Assumption vs Current Reality**

| Design Assumption | Current Reality | Impact |
|------------------|----------------|--------|
| WSUs have `source_ref` (e.g., "mw:217497") | `DictionaryDefinition` lacks source tracking | Cannot trace definitions to source |
| Structured `metadata` with `domains`/`register` | Flat `JSONMapping` without schema | Cannot extract domains/register |
| Consistent adapter WSU output | Adapters output inconsistent data structures | Need adapter-specific extraction |
| Sense lines as first-class objects | CDSL stores `sense_lines` in metadata | Need parsing to create WSUs |

### **Required Schema Evolution**
Before implementing this pipeline, the following schema changes are needed:

```python
# In src/langnet/schema.py DictionaryDefinition
source_ref: str | None = None  # "mw:217497", "diogenes:lsj:1234"
domains: list[str] = field(default_factory=list)
register: list[str] = field(default_factory=list)
confidence: float | None = None  # For stochastic sources
```

### **Implementation Path**
See `docs/plans/todo/semantic-reduction-migration-plan.md` for detailed migration strategy.

---

# 2. Witness Sense Units (WSUs)

A WSU is the smallest semantic evidence unit extracted from a source.

## Required Fields

```json
{
  "source": "MW",
  "sense_ref": "217497",
  "gloss_raw": "auspicious; benign; favorable",
  "metadata": {
    "domain": [],
    "register": []
  }
}
```

## Requirements

* Each WSU must include a stable locator (`sense_ref`).
* Gloss text must remain traceable to the source.
* No paraphrasing at this stage.
* All WSUs must be preserved even if later hidden in UI.

---

# 3. Stage A — WSU Extraction

For each lemma:

1. Extract dictionary entry.
2. Split into granular WSUs (per numbered or structurally separable sense).
3. Attach source metadata.
4. Preserve ordering as given by the source.

Adapters must ensure deterministic extraction.

---

# 4. Stage B — Gloss Normalization (Comparison Layer Only)

Normalization applies only to comparison keys.

## Allowed Transformations

* Lowercasing
* Unicode normalization
* Whitespace normalization
* Abbreviation expansion (via AbbrevMap)
* Tokenization

## Prohibited

* Paraphrasing
* Translation
* Semantic summarization

Output:

```json
{
  "gloss_display": "auspicious; benign; favorable",
  "gloss_key": "auspicious benign favorable"
}
```

---

# 5. Stage C — Similarity Graph Construction

Compute pairwise similarity between WSUs.

## Signals

1. Token overlap (Jaccard or cosine)
2. Shared domain/register metadata
3. Shared entity-type indicators
4. Primary lexicon agreement boost
5. Negation penalty (e.g., “not X”)

## Score Range

0.0 – 1.0

Similarity scoring must be deterministic.

---

# 6. Stage D — Sense Bucketing (Clustering)

Cluster WSUs into buckets.

## Deterministic Clustering Algorithm

Recommended method: greedy agglomerative clustering.

1. Sort WSUs by:

   * Source priority
   * Stable `sense_ref`
2. Start new bucket with next unused WSU.
3. Add WSUs with similarity ≥ threshold.
4. Repeat until exhausted.

Threshold depends on mode (see Section 10).

---

# 7. Bucket Structure

A bucket represents a cluster artifact and must include:

```json
{
  "sense_id": "B1",
  "semantic_constant": null,
  "display_gloss": "auspicious; benign; favorable",
  "confidence": 0.91,
  "witnesses": [...]
}
```

## Bucket Rules

* `sense_id` must be deterministic.
* Witness list must not overlap between buckets.
* Buckets may be re-ordered but must remain reproducible.

---

# 8. Semantic Constant Layer

## 8.1 Definition

A semantic constant is a stable, language-agnostic identifier representing a concept.

Examples:

* AUSPICIOUSNESS
* MORAL_LAW
* DEITY_IDENTITY
* WELFARE_PROSPERITY

Constants are stored in a registry (external to query output).

---

## 8.2 Registry Structure

```json
{
  "constant_id": "AUSPICIOUSNESS",
  "canonical_label": "auspiciousness",
  "description": "state or quality of being favorable or blessed",
  "domains": ["religion"],
  "status": "provisional | curated",
  "created_from": ["mw:217497"],
  "created_at": "timestamp"
}
```

---

# 9. Constant Assignment Policy

## Step 1 — Attempt Match

For each bucket:

* Compare bucket centroid gloss against existing constants.
* If similarity ≥ match_threshold:

  * Assign that constant.

## Step 2 — Introduce Provisional Constant

If no match:

* Generate new constant ID:

  * Uppercase snake case from centroid tokens
  * Example:

    * “moral law; righteous conduct” → `MORAL_LAW`
* Mark as `status: provisional`
* Add to registry.

## Step 3 — Curation

Later review may:

* Merge constants
* Rename canonical label
* Add domains
* Mark as curated

Constants must not change identity once curated.

---

# 10. Mode Behavior

Modes alter clustering strictness and constant assignment behavior.

---

## 10.1 Open Mode

Purpose: learner-friendly consolidation.

* Merge threshold: lower (e.g., ≥ 0.62)
* Allow merging by gloss similarity alone
* Broader buckets
* Constant assignment optional but encouraged

---

## 10.2 Skeptic Mode

Purpose: conservative evidence-first grouping.

* Merge threshold: higher (e.g., ≥ 0.78)
* Require primary lexicon agreement OR strong similarity
* Smaller buckets
* Constant assignment allowed only if:

  * Supported by primary lexicon-backed cluster
* More buckets surfaced by default

---

# 11. Confidence Calculation

Confidence may include:

* Number of independent sources
* Primary lexicon presence
* Intra-bucket coherence
* Absence of entity-type contradictions

Confidence must be numeric 0–1.

---

# 12. Ranking and Surfacing

Buckets must be ranked by:

1. Independent source count
2. Primary lexicon presence
3. Domain importance
4. Generality (non-technical > obscure technical by default)

Hidden-by-default buckets must appear in `ui_hints.collapsed_senses`.

---

# 13. Stability Guarantees

The following must remain stable if input evidence unchanged:

* Bucket count
* Witness assignments
* `sense_id`
* Constant assignment
* Ranking order (unless algorithm version incremented)

---

# 14. Test Strategy

## 14.1 Golden Snapshots

Store expected:

* Bucket count
* `sense_id`
* `semantic_constant`
* Witness refs
* Rank order

Test across 60+ entries (20 per language).

---

## 14.2 Fuzz Testing

Include:

* Encoding variants (IAST/SLP1/Devanagari)
* Abbreviation variants
* Punctuation variants

Assert:

* No duplicate witnesses
* No bucket instability
* Deterministic constant generation

---

## 14.3 Regression Rules

If algorithm version changes:

* Version increment required
* Snapshot updates justified in commit notes

---

# 15. CLI Contract

### Default View

* Show top 3–7 buckets
* Show display_gloss
* Show source tags

### `--evidence`

* Show bucket → witness mapping
* Show constant ID

### `--json`

* Emit full `senses[]`
* Include `semantic_constant`
* Include collapsed hints

---

# 16. Completion Criteria

* [ ] WSU extraction implemented per source
* [ ] Deterministic clustering stable
* [ ] Constant registry implemented
* [ ] Match + introduce policy operational
* [ ] Mode thresholds defined
* [ ] Snapshot suite passing
* [ ] Documentation synchronized with Schema v1
