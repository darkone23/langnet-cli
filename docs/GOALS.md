# LangNet – Project Philosophy and Goals

## Purpose

LangNet (aka project orion) is a pedagogically-oriented semantic lexicon engine for Greek, Latin, and Sanskrit.

Its purpose is to support deep language learning through structured meaning, transparent evidence, and functional grammar presentation. The project integrates morphology, lexica, and citations into a coherent system that emphasizes clarity, traceability, and semantic structure.

This document defines the principles that guide development decisions and long-term direction.

---

# 1. Educational Orientation

LangNet is built to support learners at multiple stages:

* Beginners encountering inflected forms
* Intermediate students building semantic intuition
* Advanced readers and researchers engaging with primary texts

The system prioritizes clarity before exhaustiveness. It surfaces high-signal semantic structure first, while preserving access to full lexical evidence.

Language study is treated as formative: careful attention to words refines perception and strengthens interpretive skill.

---

# 2. Meaning as Structure

Words are organized around structured semantic patterns.

LangNet models meaning across four layers:

1. Witness sense units (source-derived evidence)
2. Sense buckets (clustered related meanings)
3. Semantic constants (stable conceptual identifiers)
4. Display glosses (human-readable descriptions)

This layered structure supports:

* Reduction of redundancy
* Clear identification of core meanings
* Cross-language comparison
* Long-term semantic curation

Glosses describe meaning.
Semantic constants identify meaning.

---

# 3. Function Over Form

Grammatical categories are presented with functional clarity.

Technical terminology is preserved and paired with its functional role in a sentence.

Examples:

* Nominative (Naming Function)
* Accusative (Receiving Function)
* Dative (To-For Function)
* Instrumental (By-With Function)

This approach is applied consistently across:

* Greek
* Latin
* Sanskrit

The objective is to make grammatical structure intelligible and usable.

---

# 4. Dual Epistemic Modes

LangNet supports two complementary interpretive perspectives.

## Open Mode

* Emphasizes semantic coherence.
* Merges closely related senses.
* Surfaces a clear “spine of meaning.”
* Supports learner engagement.

## Skeptic Mode

* Applies stricter merging thresholds.
* Preserves finer distinctions.
* Requires stronger lexical agreement.
* Highlights source-level evidence.

Both modes preserve the same underlying data.
They differ in clustering strictness and presentation strategy.

---

# 5. Evidence and Traceability

All semantic claims are grounded in identifiable sources.

The system:

* Preserves dictionary entry identifiers
* Preserves CTS URNs
* Preserves morphology references
* Records provenance metadata
* Avoids paraphrasing without traceability

Every sense bucket is supported by witnesses.
Evidence remains inspectable through dedicated CLI flags.

Transparency is a core design constraint.

---

# 6. Semantic Constants

LangNet introduces semantic constants as stable concept identifiers.

Constants:

* Represent recurring conceptual nodes
* Are language-agnostic
* Begin provisional when introduced
* Become curated over time
* Remain stable once curated

Constant assignment follows a structured policy:

1. Attempt to match a bucket to an existing constant.
2. If no match exists, introduce a provisional constant.
3. Curate and refine over time.

This enables:

* Cross-language semantic alignment
* Domain grouping
* Semantic drift analysis
* Etymological reasoning at the concept level

Meaning is treated as a structured node rather than a flat string.

---

# 7. Cross-Language Consistency

LangNet serves three classical language traditions.

The system maintains:

* Unified JSON schema across languages
* Consistent morphology representation
* Shared functional grammar labels
* Comparable semantic structures

Language-specific nuances are respected within a common structural framework.

---

# 8. Progressive Disclosure

Information is layered intentionally.

Default view emphasizes:

1. Most likely lemma
2. Major semantic buckets (3–7)
3. Morphology summary
4. Key citations

Extended detail remains accessible via explicit flags.

This preserves usability while retaining scholarly depth.

---

# 9. Sanskrit Commitments

Sanskrit support emphasizes:

* Root-focused learning (e.g., √yuj)
* Lemmatization of inflected forms
* Multiple encoding support (IAST, SLP1, Devanagari, Velthuis)
* Transparent normalization contracts

The system connects surface forms to roots and lexica in a way that supports both beginners and advanced readers.

---

# 10. Greek and Latin Commitments

Greek and Latin support emphasizes:

* Primary lexicon authority (e.g., LSJ and related sources)
* CTS anchoring for citations
* Integration with textual evidence
* Functional grammar mapping

The system encourages engagement with words in real textual contexts.

---

# 11. Engineering Priorities Aligned with Philosophy

Development follows these principles:

* Determinism over heuristic opacity
* Stability before feature expansion
* Constants over ad hoc gloss manipulation
* Traceability over summarization
* Structural coherence across languages

Architectural stabilization precedes enrichment.

---

# 12. Long-Term Aim

LangNet aims to provide a structured environment in which:

* Words are encountered as semantic structures
* Grammar is understood functionally
* Lexical evidence remains transparent
* Conceptual relationships can be explored systematically

The system supports disciplined reading and meaningful engagement with classical texts.

Every word carries structure.
Clarity emerges from careful organization of that structure.
