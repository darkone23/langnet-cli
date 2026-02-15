# Dictionary Entry Parsing Layer

## Status

**Draft – Target for Stabilization**
**Date**: 2026-02-15
**Prerequisite For**: 03-classifier-and-reducer.md (WSU extraction)

## Purpose

This document defines the parsing layer that sits between raw adapter output and WSU extraction. It addresses the fundamental problem:

**Raw dictionary entries conflate distinct information types into single text fields.**

## The Problem

### Current State

| Source | Raw Entry | What's Conflated |
|--------|-----------|------------------|
| CDSL | `agni/   m. (√ ag, Uṇ.) fire, sacrificial fire` | headword + gender + root + sense |
| CDSL | `bile, L.` | sense + citation abbrev (lexicographers) |
| Diogenes | `I.  Lit.: torva leaena lupum sequitur, Verg. E. 2, 63` | sense marker + citation text + source ref |
| CLTK Lewis | `sēdō\n\n\n āvī, ātus, āre \n\nSED-, \nto bring...` | headword + principal parts + root + sense |

### Impact on Downstream

1. **WSU extraction** produces "dirty" glosses with root symbols, abbreviations
2. **Similarity scoring** penalized by noise (e.g., "L." treated as content)
3. **Citation WSUs** cannot be distinguished from sense WSUs
4. **Etymology/grammar info** lost in undifferentiated text

## Architecture Position

```
Raw Adapter Output
       ↓
┌─────────────────────────────────────┐
│  ENTRY PARSING LAYER (this doc)     │
│  - Lark grammars per dictionary      │
│  - Extract: headword, root, senses   │
│  - Separate: citations from glosses  │
└─────────────────────────────────────┘
       ↓
ParsedEntry (clean, structured)
       ↓
┌─────────────────────────────────────┐
│  WSU EXTRACTION (03-classifier)     │
│  - Generate WSUs from ParsedEntry   │
│  - Type: sense | citation            │
└─────────────────────────────────────┘
       ↓
WSU (Witness Sense Unit)
       ↓
Similarity & Clustering...
```

## ParsedEntry Schema

```python
@dataclass
class ParsedEntry:
    """Clean, structured dictionary entry after parsing."""
    
    # Identity
    headword: str                    # "agni" (cleaned)
    language: str                    # "san", "lat", "grc"
    source: str                      # "cdsl", "diogenes", "cltk"
    source_ref: str | None           # "mw:217497"
    
    # Grammar (entry-level, not per-sense)
    pos: str | None                  # "noun", "verb"
    gender: str | None               # "m", "f", "n"
    inflection_class: str | None     # "1st", "2nd" (declension/conjugation)
    
    # Etymology (entry-level)
    root: str | None                 # "ag" (from √ ag)
    etymology_note: str | None       # "verbal noun of λέγω"
    principal_parts: list[str]       # ["āvī", "ātus", "āre"] (Lewis)
    cognates: list[str]              # ["λύκος"] (Diogenes head)
    
    # Senses (multiple per entry)
    senses: list[ParsedSense]
    
    # Citations (usage examples, not definitions)
    citations: list[ParsedCitation]
    
    # Raw preserved for debugging
    raw_text: str


@dataclass
class ParsedSense:
    """A lexicographer's definition/gloss (NOT a citation)."""
    gloss: str                       # "fire, sacrificial fire" (clean!)
    sense_id: str                    # "I", "1", "β" (hierarchical)
    domains: list[str]               # ["religion", "ritual"]
    register: list[str]              # ["vedic"]
    examples: list[ParsedExample]    # Embedded examples (Lewis)


@dataclass
class ParsedCitation:
    """Actual usage from classical texts."""
    text: str                        # "torva leaena lupum sequitur"
    source_ref: str                  # "Verg. E. 2, 63"
    cts_urn: str | None              # Normalized CTS URN
    author: str | None
    work: str | None


@dataclass
class ParsedExample:
    """Example within a sense (Lewis & Short style)."""
    text: str                        # "pulverem"
    author_abbrev: str | None        # "Ph." (Phaedrus)
    embedded_gloss: str | None       # "slake" (wrapped in newlines)
```

## WSU Type Distinction

After parsing, WSU extraction produces two types:

| WSU Type | Source | Purpose |
|----------|--------|---------|
| `sense` | `ParsedSense.gloss` | Lexicographer's definition |
| `citation` | `ParsedCitation.text` | Actual usage in literature |

**Why this matters**: Senses and citations should cluster separately. A "wolf" sense clusters with "canine" senses. A Latin sentence about wolves clusters with similar usage patterns, not with the definition.

## What Is NOT a WSU Type

### Grammatical Metadata vs Semantic Content

Not everything extracted from an entry becomes a WSU. The distinction is:

| Category | Examples | Becomes WSU? | Why |
|----------|----------|--------------|-----|
| **Semantic content** | glosses, citation texts | **Yes** | Needs similarity clustering |
| **Grammatical metadata** | POS, gender, conjugation | **No** | Used for filtering, not clustering |
| **Etymological info** | root, cognates | **No** | Entry-level reference, not sense-level |

### Why POS Is Not a WSU Type

If we made POS a WSU type:
```
WSU(type="pos", gloss="noun")
WSU(type="pos", gloss="verb")  
```

**This is meaningless for clustering** - "noun" doesn't cluster with "noun" semantically. POS is:
- A **filter**: "only match senses where lemma is a noun"
- A **constraint**: "this form is 3rd declension"
- An **entry-level property**, not a sense-level claim

### Design Principle

> **WSU types are for content that requires semantic similarity analysis. 
> Grammatical metadata stays at the entry level and is used for filtering and display.**

### Schema Implications

```python
@dataclass
class ParsedEntry:
    # These are ENTRY-LEVEL metadata (not WSU candidates)
    pos: str | None              # Used for filtering
    gender: str | None           # Used for morphology display  
    root: str | None             # Used for etymology reference
    principal_parts: list[str]   # Used for verb identification
    
    # These become WSUs (semantic content)
    senses: list[ParsedSense]    # → WSU type "sense"
    citations: list[ParsedCitation]  # → WSU type "citation"
```

## Parser Architecture

### Lark Grammars

Each dictionary gets its own Lark grammar (EBNF) + Transformer:

```
src/langnet/parsing/
├── types.py                    # ParsedEntry, ParsedSense, ParsedCitation
├── cdsl/
│   ├── cdsl_entry.ebnf         # Sanskrit (MW, AP90)
│   └── cdsl_transformer.py
├── diogenes/
│   ├── diogenes_block.ebnf     # Latin (Lewis-Short), Greek (LSJ)
│   └── diogenes_transformer.py
└── cltk_lewis/
    ├── cltk_lewis_entry.ebnf   # CLTK Lewis output
    └── cltk_lewis_transformer.py
```

### Pattern: Following Whitaker's

This pattern is already proven in `src/langnet/whitakers_words/lineparsers/`:

```python
# Example: cdsl_transformer.py
class CDSLTransformer(Transformer):
    def root_spec(self, args):
        return {"root": args[0]}  # Extract "ag" from "√ ag"
    
    def citation_abbrev(self, args):
        # Strip "L." from sense, record as metadata
        return {"citation_abbrev": args[0]}

class CDSLParser:
    parser = Lark(get_cdsl_grammar())
    xformer = CDSLTransformer()
    
    @staticmethod
    def parse(line: str) -> ParsedEntry:
        tree = CDSLParser.parser.parse(line)
        return CDSLParser.xformer.transform(tree)
```

## Grammar Design Principles

### 1. Preserve Semantically Significant Whitespace

Diogenes uses `MARKER.  ` (two spaces) for sense hierarchy. This must not be consumed by `%ignore WS`.

```ebnf
sense_marker: (ROMAN | GREEK_LETTER) "." "  "  # Literal two spaces
```

### 2. Handle Unicode Properly

Greek and Sanskrit require Unicode-aware terminals:

```ebnf
GREEK_LETTER: /[\u0370-\u03FF]/
SANSKRIT_WORD: /[\u0900-\u097F]+/
```

### 3. Extract, Don't Discard

Roots, etymology notes, and citation abbreviations should be **extracted to structured fields**, not thrown away. They're evidence for downstream clustering.

## Integration Points

### Adapter Integration

```python
# In cologne/adapter.py
def adapt_cdsl_to_universal(cdsl_data):
    parsed = CDSLParser.parse(cdsl_data['text'])
    return DictionaryEntry(
        word=parsed.headword,
        definitions=[
            DictionaryDefinition(
                definition=s.gloss,        # CLEAN!
                pos=parsed.pos,
                gender=parsed.gender,
                etymology=f"√ {parsed.root}" if parsed.root else None,
                # NEW fields
                root=parsed.root,
                source_ref=parsed.source_ref,
            )
            for s in parsed.senses
        ],
    )
```

### WSU Extraction Update

```python
# In semantic_reducer/wsu_extractor.py
def extract_wsus_from_parsed(parsed: ParsedEntry) -> list[WSU]:
    wsus = []
    
    # Senses → sense-type WSUs
    for sense in parsed.senses:
        wsus.append(WSU(
            wsu_type="sense",
            gloss_raw=sense.gloss,
            source=parsed.source,
            sense_ref=parsed.source_ref,
        ))
    
    # Citations → citation-type WSUs  
    for cit in parsed.citations:
        wsus.append(WSU(
            wsu_type="citation",
            gloss_raw=cit.text,
            source=parsed.source,
            source_ref=cit.cts_urn,
        ))
    
    return wsus
```

## Stability Guarantees

Parsing must be:
1. **Deterministic**: Same input → same `ParsedEntry`
2. **Lossless**: All information preserved (either in fields or `raw_text`)
3. **Traceable**: `source_ref` maintained through transformation

## Test Strategy

### Golden Snapshots

```python
# tests/test_parsing/test_cdsl_parser.py
def test_cdsl_agni_snapshot():
    result = CDSLParser.parse("agni/   m. (√ ag, Uṇ.) fire, sacrificial fire")
    snapshot = {
        "headword": "agni",
        "gender": "m", 
        "root": "ag",
        "senses": [{"gloss": "fire, sacrificial fire"}],
    }
    assert result_to_dict(result) == snapshot
```

### Regression Tests

If grammar changes, snapshot must be explicitly updated with justification.

## Completion Criteria

- [ ] `ParsedEntry` types defined in `langnet/parsing/types.py`
- [ ] CDSL grammar handles root extraction (`√`)
- [ ] CDSL grammar strips citation abbreviations (`L.`, `RV.`)
- [ ] Diogenes grammar handles sense markers (two-space pattern)
- [ ] Diogenes grammar separates citation text from source refs
- [ ] CLTK Lewis grammar handles principal parts and em-dash senses
- [ ] All adapters wired to parsers
- [ ] WSU extractor generates `wsu_type` field
- [ ] Golden snapshot tests pass for 20+ entries per dictionary

---

*This layer is a prerequisite for the WSU extraction defined in `03-classifier-and-reducer.md`.*