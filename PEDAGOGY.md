# Pedagogy Goals – Langnet CLI Guiding Principles

langnet-cli is designed to be a **pedagogical engine** that helps learners of Latin, Greek, and Sanskrit understand language through functional grammar, contextual citations, and intelligent search.  The following goals drive all development and prioritisation.

## 🎯 High‑Impact Priorities (ordered by impact)

| Priority | Feature | Effort | Pedagogical Impact | Why it matters |
|----------|---------|--------|-------------------|----------------|
| **P0** | **Lemmatization** | Low | **Huge** | Provides a reliable head‑word for dictionary look‑ups and morphological analysis. |
| **P0** | **Foster Functional Grammar** | Low | **Huge** | Shows *what words do* in sentences (case, tense, voice, etc.) rather than just technical labels, following Reginald Foster’s teaching method. |
| **P1** | **Citation Display** | Medium | **Huge** | Shows authentic textual examples (“see the word in the wild”), reinforcing vocabulary in context. |
| **P1** | **Fuzzy Searching** | Low | High | Handles common miss‑spelling and orthographic variants (e.g., `v` vs `u`) so users receive results even with imperfect input. |
| **P2** | **CDSL Reference Enhancement** | Low | High | Exposes `<ls>` lexicon references, linking Sanskrit dictionary entries to related resources. |
| **P2** | **Enhanced Citation Formatting** | Low | Medium | Presents citations in a learner‑friendly format, improving readability and comprehension. |
| **P3** | **Cross‑Lexicon Etymology** | High | Medium | Enables scholars to trace word origins across Latin, Greek, and Sanskrit – valuable for advanced study. |
| **P3** | **Performance / Scaling** | High | **Low** | The CLI already performs well for single‑user use; scaling is a lower priority but remains on the roadmap. |

