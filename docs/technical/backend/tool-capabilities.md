# Tool Capabilities

| Tool | Languages | Strengths | Current claim use |
| --- | --- | --- | --- |
| Whitaker's Words | Latin | morphology, lemmas, senses | scoped interpretations, morphology, senses |
| Diogenes | Latin, Greek | dictionary entries, citations | senses, glosses, citations, some morphology |
| CLTK | Latin, Greek | supplemental lexicon/IPA/NLP | pronunciation, Lewis lines, inflection links |
| spaCy | Greek where configured | NLP annotations | supplemental claims |
| Sanskrit Heritage | Sanskrit | morphology | morphology claims |
| CDSL | Sanskrit | dictionary senses/source refs | sense/gloss/source-ref claims |

## Selection Rule

Planner behavior should prefer tools that add distinct evidence. Reducers should merge source witnesses later rather than suppressing backend differences early.
