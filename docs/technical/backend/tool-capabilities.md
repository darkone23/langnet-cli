# Tool Capabilities

Current catalog source: `just cli tools --output json`.

| Tool filter | Languages | Strengths | Current claim/use |
| --- | --- | --- | --- |
| `diogenes` | Latin, Greek | dictionary entries, morphology, citations, inflection tables | senses, glosses, citations, morphology, paradigms |
| `whitakers` | Latin | morphology, lemmas, compact senses | scoped interpretations, morphology, senses, word-index source |
| `cltk` | Latin, Greek | supplemental lexicon and IPA | pronunciation, lexicon, inflection links; disabled by default for encounter unless requested |
| `gaffiot` | Latin | Latin-French dictionary entries | local DuckDB entry claims; translation-cache capable; word-index source |
| `lewis_1890` | Latin | Latin-English dictionary entries | local DuckDB entry claims; word-index source |
| `bailly` | Greek | Greek-French dictionary entries | local DuckDB entry claims; translation-cache capable; word-index source |
| `cts_index` | Greek | CTS citation/reader metadata | citation hydration claims and reader metadata support |
| `spacy` | Greek where configured | supplemental morphology | supplemental morphology claims |
| `heritage` | Sanskrit | morphology and segmentation | morphology claims and Sanskrit paradigm resolver input |
| `cdsl` | Sanskrit | MW/AP90 dictionary senses/source refs | sense/gloss/source-ref claims; word-index source |
| `dico` | Sanskrit | Sanskrit-French dictionary entries | local DuckDB entry claims; translation-cache capable; word-index source |

Pseudo-filter:

- `all` — all default tools for `lat`, `grc`, or `san`.

## Selection Rule

Planner behavior should prefer tools that add distinct evidence. Reducers should merge source witnesses later rather than suppressing backend differences early.
