a plan from chatgpt:

1. semantic distillation from current outputs
  - 'spine of meaning'
  - map semantic shift/expansion

Minimum fields (v1):
query (as entered), language (if known/assumed), normalized
lemmas[] (with confidence + source)
analyses[] (POS/morph features; multiple allowed)
senses[] (each with source, short gloss, optional domain tags)
citations[] (CTS urns, dictionary IDs, etc.)
provenance[] (tool/source name + version + retrieval metadata)
ui_hints (what to show first, how to group)

2. reduction pipeline for existing json outputs
  - find overlaps / colocations
  - figure out 'thesis' and 'drift'

citizens of input:

diogenes / Perseus: strongest for Greek/Latin dictionary blocks + CTS anchors
Whitaker / CLTK: fast morphology + basic senses (helpful, but not the final court)
CDSL (MW) + Heritage: essential Sanskrit lexicon + morphology
abbreviation maps: required to make everything readable
Foster mapping: unify “human-friendly morphology labels” across languages
Write down per-source “contract”:
what it’s trusted for
how it’s cited
how conflicts are resolved

a cli with 'modes'

Define the stable CLI soon, even if internals evolve.
Example behaviors (not syntax-policing, just commitments):
lookup WORD → returns didactic view
lookup WORD --evidence → shows raw evidence blocks by source
lookup WORD --mode skeptic → stricter output + more citations
lookup WORD --json → schema v1 object
lookup WORD --links → outbound citations/resolvers
  
Once the above exists, add the real pedagogical engine:
surface 3–10 short, high-signal example passages per major sense
keep them skimmable
link each example to its source
  
3. create a UI for viewing this information
  - form follows function!

Didactic View Layer (curated)
a small, stable presentation object derived from evidence:
most likely lemma
top senses (3–7)
one or two example citations
morphology summary
links out / citations

Make --mode open|skeptic a first-class CLI concept.
Open: merge senses generously, show analogies, show “semantic constellation,” allow wider inference.
Skeptic: prioritize primary lexica + attestations, hide speculative merges, require citations per claim

Implement:
internal citation objects (CTS URNs, dict IDs, line refs)
outbound resolvers:
CTS → Perseus catalog pages (ddg/ducky idea works here)
Sanskrit: MW IDs, Heritage refs, and (later) DCS links when integrated

note: sanskrit DICO translation pipeline should ENHANCE semantic distillation
  - it is not a prerequisite for it

> some more iteration is probably helpful on making a unified output

current data sources
  - cltk backends
  - cdsl indexer / db
  - perseus data CTS urns
  - heritage platform
  - foster data mapping
  - abbreviation maps
  - diogenes

we generally are returning dictionary entries
  - sometimes those entries have part of speech parsing
  - sometimes those entries have structured output graphs
  - generally takes time to load (metadata)

we should consider each individual tool output and how to best integrate its ouput

we want a stable 'cli query ...' schema quite soon

the python types are best when easily mapped to things like avro structs
thus clear datatypes are preferred

create UI plan for citations

-> use a tool like ddg / ducky:
  - eg: https://duckduckgo.com/?q=!ducky+urn:cts:latinLit:phi0119.phi008
    -> https://catalog.perseus.tufts.edu/catalog/urn:cts:latinLit:phi0119.phi008

consider outbound searches:
- http://www.sanskrit-linguistics.org/dcs/index.php?contents=abfrage&word=nirodha&query_type=1&sort_by=alpha
- http://www.sanskrit-linguistics.org/dcs/index.php?contents=impressum
- https://github.com/OliverHellwig/sanskrit
