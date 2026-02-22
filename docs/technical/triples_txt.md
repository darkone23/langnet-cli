# Flat Facts → Scoped Interpretations (DuckDB)

This document describes a **flat, extraction-first** data structure for ambiguous lexical variants (e.g., *ea* in Latin), and how to later **resolve / query** it into an educational summary.

The approach borrows the discipline of RDF (subject–predicate–object), but is designed for a **columnar SQL store (DuckDB)** during the extraction phase.

---

## 1) Problem restatement

You are extracting dictionary-like statements keyed by a **search term** (surface string) such as `"ea"`. The same surface form can map to multiple underlying analyses:

* `ea` might correspond to a **verb lexeme** (e.g., lemma `eo`) with a sense like **“to go”**.
* `ea` might also correspond to a **pronoun lexeme** (e.g., lemma `is` or `idem`) with different grammatical features.
* Some lemma forms may have orthographic/manuscript variants (e.g., `eare`, `evi`).

You need:

1. To **capture ambiguity** (multiple plausible readings) without contradiction.
2. To **scope facts** correctly (e.g., the “to go” sense applies only to the **verb** reading, not the pronoun reading).
3. To keep the data **flat** during extraction.
4. To later **reduce** the facts into an educational summary.

---

## 2) The core modeling move: “scope” everything

If you attach facts directly to the surface form, you get contradictions and mis-scoping:

* ❌ `form:ea pos verb`
* ❌ `form:ea pos pronoun`
* ❌ `form:ea hasSense to go`

Instead, introduce a **scoping entity**: an **Interpretation** (aka reading / analysis).

* ✅ `form:ea hasInterpretation interp:ea→lex:eo#verb`
* ✅ `interp:ea→lex:eo#verb pos verb`
* ✅ `lex:eo#verb hasSense sense:eo#go`

This single extra layer lets you preserve ambiguity while keeping semantics correct.

---

## 3) Flat fact rows: a single universal format

### 3.1 Fact row shape

Store one extracted fact per row (or JSONL line):

* `anchor` — the thing this fact is *about* (form, interpretation, lexeme, sense)
* `predicate` — the relation/property
* `value` — IRI-like identifier or literal
* `qual` — qualifiers (case/number/gender, variant-kind, etc.)
* `source` — provenance (dictionary/work, entry id, page/line, extraction run)
* `confidence` — optional numeric estimate

Think: **Fact = (anchor, predicate, value, qualifiers, provenance)**.

### 3.2 Anchor types (the only four you usually need)

Use stable string identifiers (you can later map them to integer ids for speed):

1. **Form** (search term / surface form)

* `form:ea`
2. **Interpretation** (reading-specific)

* `interp:form:ea→lex:eo#verb`
* `interp:form:ea→lex:is#pron`
3. **Lexeme** (lemma + POS bucket)

* `lex:eo#verb`
* `lex:is#pron`
4. **Sense** (a meaning node)

* `sense:lex:eo#verb#go`

> Design rule: **POS lives on interpretations and/or lexemes; senses live on senses/lexemes; the form only links to interpretations.**

---

## 4) Minimal fact vocabulary (predicates)

You can start with a tiny set of predicates and expand:

### Form-level

* `has_interpretation` → interpretation id

### Interpretation-level

* `realizes_lexeme` → lexeme id
* `pos` → `verb | pronoun | noun | ...`
* `features` → typically represented via qualifiers rather than nested objects

### Lexeme-level

* `lemma` → canonical lemma string (literal)
* `has_sense` → sense id
* `variant_form` → variant string (literal or form id)

### Sense-level

* `gloss` → short definition (literal)
* `domain` / `register` (optional)

---

## 5) Worked example (flat facts)

### 5.1 Ambiguity: `ea` has multiple interpretations

```json
{"anchor":"form:ea","predicate":"has_interpretation","value":"interp:form:ea→lex:eo#verb","qual":{},"source":{"work":"DictX","entry":"ea"},"confidence":0.40}
{"anchor":"form:ea","predicate":"has_interpretation","value":"interp:form:ea→lex:is#pron","qual":{},"source":{"work":"DictX","entry":"ea"},"confidence":0.45}
{"anchor":"form:ea","predicate":"has_interpretation","value":"interp:form:ea→lex:idem#pron","qual":{},"source":{"work":"DictX","entry":"ea"},"confidence":0.15}
```

### 5.2 Interpretation-level facts: “ea is a verb/pronoun”

```json
{"anchor":"interp:form:ea→lex:eo#verb","predicate":"pos","value":"verb","qual":{},"source":{"work":"DictX","entry":"ea"}}
{"anchor":"interp:form:ea→lex:eo#verb","predicate":"realizes_lexeme","value":"lex:eo#verb","qual":{},"source":{"work":"DictX","entry":"ea"}}

{"anchor":"interp:form:ea→lex:is#pron","predicate":"pos","value":"pronoun","qual":{},"source":{"work":"DictX","entry":"ea"}}
{"anchor":"interp:form:ea→lex:is#pron","predicate":"realizes_lexeme","value":"lex:is#pron","qual":{},"source":{"work":"DictX","entry":"ea"}}
```

### 5.3 Sense scoping: “to go” belongs to the verb lexeme

```json
{"anchor":"lex:eo#verb","predicate":"has_sense","value":"sense:lex:eo#verb#go","qual":{},"source":{"work":"DictX","entry":"eo"}}
{"anchor":"sense:lex:eo#verb#go","predicate":"gloss","value":"to go","qual":{"lang":"en"},"source":{"work":"DictX","entry":"eo"}}
```

### 5.4 Variants: `eare`, `evi` are variants of the verb lexeme

```json
{"anchor":"lex:eo#verb","predicate":"variant_form","value":"eare","qual":{"kind":"orthographic"},"source":{"work":"MS-A","entry":"eo"}}
{"anchor":"lex:eo#verb","predicate":"variant_form","value":"evi","qual":{"kind":"orthographic"},"source":{"work":"MS-B","entry":"eo"}}
```

**Result:** you can later summarize:

* Form **ea** is ambiguous across 3 interpretations.
* Only the **EO-verb** interpretation leads to the sense **“to go.”**
* Pronoun interpretations point to **IS/IDEM**, with no “to go” sense attached.

---

## 6) DuckDB storage design

DuckDB is columnar and excels at scans + grouping. During extraction you’ll often do bulk inserts; indexes help only for selective equality lookups. The design below works well with zonemaps and keeps the data flat.

### 6.1 One-table MVP

```sql
CREATE TABLE facts (
anchor        VARCHAR,
predicate     VARCHAR,
value         VARCHAR,
value_kind    VARCHAR,  -- 'id' or 'literal' (optional)
qual_json     JSON,
source_json   JSON,
confidence    DOUBLE,
extracted_at  TIMESTAMP
);
```

Suggested ordering (helps zonemaps/compression):

* When bulk-loading, **ORDER BY (anchor, predicate)** or `(predicate, anchor)` depending on your most common reductions.

```sql
CREATE TABLE facts_sorted AS
SELECT * FROM facts
ORDER BY anchor, predicate;
```

### 6.2 Two-table “provenance friendly” upgrade (still flat)

If you have many repeated source fields, normalize them:

```sql
CREATE TABLE sources (
source_id     BIGINT,
work          VARCHAR,
entry         VARCHAR,
loc           VARCHAR,
run_id        VARCHAR,
meta_json     JSON
);

CREATE TABLE facts (
anchor        VARCHAR,
predicate     VARCHAR,
value         VARCHAR,
qual_json     JSON,
source_id     BIGINT,
confidence    DOUBLE
);
```

You can still export back to JSONL easily.

### 6.3 Indexes: what to do (given DuckDB’s behavior)

* Prefer **ordering** over indexes for extraction-phase bulk data.
* Add **single-column ART indexes** only when you start running highly selective equality filters (e.g., looking up one anchor repeatedly).

Typical helpful single-column indexes (later):

```sql
CREATE INDEX idx_facts_anchor ON facts(anchor);
CREATE INDEX idx_facts_pred   ON facts(predicate);
```

(Keep in mind DuckDB’s note: ART indexes won’t speed joins/aggregations/sorts much; they mainly help selective `anchor = ...` or `IN (...)` probes.)

---

## 7) “Resolution” without graph querying (how to reduce facts into a summary)

Even if you don’t run a graph traversal engine, you can resolve by **grouping and joining** within the flat facts.

### 7.1 Canonical resolution steps

Given a form like `form:ea`:

1. **Find interpretations**

* all rows where `(anchor = 'form:ea' AND predicate = 'has_interpretation')`

2. For each interpretation `interp:*`:

* read its `pos`
* read its `realizes_lexeme` → `lex:*`

3. For each lexeme `lex:*`:

* list `has_sense` → `sense:*`
* list `variant_form`

4. For each sense `sense:*`:

* show `gloss`

5. When there are multiple sources claiming conflicting values:

* keep all, but rank by `confidence` or “source priority”

### 7.2 DuckDB query sketches

**A) Get interpretations of a form**

```sql
SELECT value AS interpretation, confidence, source_json
FROM facts
WHERE anchor = 'form:ea'
AND predicate = 'has_interpretation';
```

**B) Get POS + lexeme for each interpretation**

```sql
WITH interps AS (
SELECT value AS interp
FROM facts
WHERE anchor='form:ea' AND predicate='has_interpretation'
)
SELECT f.anchor AS interp,
MAX(CASE WHEN f.predicate='pos' THEN f.value END) AS pos,
MAX(CASE WHEN f.predicate='realizes_lexeme' THEN f.value END) AS lexeme
FROM facts f
JOIN interps i ON f.anchor = i.interp
WHERE f.predicate IN ('pos','realizes_lexeme')
GROUP BY f.anchor;
```

**C) Get senses and glosses for the verb lexeme only**

```sql
WITH verb_lex AS (
SELECT MAX(CASE WHEN predicate='realizes_lexeme' THEN value END) AS lexeme
FROM facts
WHERE anchor='interp:form:ea→lex:eo#verb'
)
SELECT s.value AS sense_id,
g.value AS gloss
FROM facts s
JOIN verb_lex vl ON s.anchor = vl.lexeme
LEFT JOIN facts g ON g.anchor = s.value AND g.predicate='gloss'
WHERE s.predicate='has_sense';
```

**D) Summarize ambiguity with ranked interpretations**

```sql
SELECT value AS interpretation,
COALESCE(confidence, 0.0) AS confidence
FROM facts
WHERE anchor='form:ea' AND predicate='has_interpretation'
ORDER BY confidence DESC;
```

---

## 8) Practical extraction rules (so the reducer works)

### Rule 1 — Never put senses on forms

* ✅ `lex:* has_sense sense:*`
* ✅ `sense:* gloss "..."`
* ❌ `form:* has_sense ...`

### Rule 2 — POS belongs to interpretation (and optionally lexeme)

* ✅ `interp:* pos verb`
* ✅ `lex:* pos verb` (optional redundancy)
* ❌ `form:* pos verb`

### Rule 3 — Every interpretation must link to exactly one lexeme

* ✅ `interp:* realizes_lexeme lex:*`

### Rule 4 — Use qualifiers for feature bundles

Instead of inventing many columns, store morphological features in `qual_json`:

```json
{"case":"abl","number":"sg","gender":"f"}
```

### Rule 5 — Make IDs deterministic

So repeated extraction produces stable anchors:

* `form:<lowercased surface>`
* `lex:<lemma>#<pos>`
* `interp:form:<surface>→lex:<lemma>#<pos>`
* `sense:<lexeme>#<sense_key>`

If you later need collision resistance, append a short hash of the source key.

---

## 9) How “educational summaries” fall out naturally

Because each fact is scoped, summarization becomes a controlled reduction:

For a form:

* **Header**: surface form and “Ambiguity: N possible readings”.
* For each interpretation (ranked):

* POS + lemma
* short sense glosses (only those reachable via its lexeme)
* notable variants
* citations / sources

This yields text that matches human expectations:

> “*ea* may be either (a) a verb form of *eo* (‘to go’), or (b) a pronoun form related to *is/idem* …”

No contradiction, and the “to go” meaning never leaks into the pronoun reading.

---

## 10) When you start querying for real

You can keep this flat model forever, or later:

* Map anchors to integer ids for speed.
* Split into node/edge tables.
* Export to RDF/Turtle/JSON-LD if you move to a triplestore.

The extraction-phase structure described here is compatible with all of those.

---

## 11) Checklist

During extraction, ensure you emit at least:

* `form:X has_interpretation interp:*`
* `interp:* pos ...`
* `interp:* realizes_lexeme lex:*`
* `lex:* has_sense sense:*` (where applicable)
* `sense:* gloss ...`

Optional but useful:

* `lex:* variant_form ...`
* `confidence` per row
* `source_json` per row

---

## Appendix: Why this works well in DuckDB

* Flat rows compress well.
* Ordering by `(anchor, predicate)` improves zonemap skipping and often reduces IO.
* Most reductions are group-bys and joins, which DuckDB is good at.
* ART indexes can be added later for selective lookups once you begin interactive querying.

