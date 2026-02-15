# Dictionary Entry Parsing: Lark Grammar Pipeline

**Date**: 2026-02-15
**Status**: PLANNING
**Priority**: HIGH (Prerequisite for Semantic Struct Output)
**Blocks**: Semantic reduction clustering quality

## Problem Statement

Current dictionary adapters conflate distinct information types into single "definition" strings. This pollutes semantic clustering and confuses learners.

**Actual Examples from Current Output**:

| Source | Raw Entry (repr) | What's Conflated |
|--------|------------------|------------------|
| CDSL | `'agni/   m. (√ ag, Uṇ.) fire, sacrificial fire...'` | headword + gender + **root** + sense |
| CDSL | `'bile, L.'` | sense + **citation abbreviation** (lexicographers) |
| Diogenes Latin | `'I.  Lit.: torva leaena lupum sequitur, Verg. E. 2, 63; Plin.'` | marker + **citation text** + source refs |
| Diogenes Latin | `'β.  Lupum auribus tenere, to have a wolf by the ears...'` | Greek letter marker + sense |
| Diogenes Greek | `'1.  account of money handled, σανίδες εἰς ἃς τὸν λ. ἀναγράφομεν IG 1(2).374.191;...'` | marker + sense + **embedded citations** |
| Diogenes Greek | `'λόγος, ὁ, verbal noun of λέγω (B)...'` | headword + gender + **etymology** + sense |
| CLTK Lewis | `'sēdō\n\n\n āvī, ātus, āre \n\nSED-, \nto bring to rest...'` | headword + **principal parts** + **root** + sense |
| CLTK Lewis | `'...: pulverem, Ph.—\nTo settle...'` | sense + **example** + **author abbrev** + em-dash separator |
| CLTK Lewis | `'...sitim, \nslake\n, O.:...'` | example + **newline-wrapped gloss** + author abbrev |

**Key Observations**:
- Diogenes uses `MARKER.  ` (marker + period + TWO spaces) for sense hierarchy
- CLTK Lewis uses `\n` newlines, `: ` separators, and `—` em-dashes
- CLTK Lewis wraps glosses in `\n...\n` (newline on both sides)

**Impact on Semantic Reduction**:
- WSUs like "bile, L." cluster with "L." noise
- "√ ag" appears in gloss text, not recognized as root info
- Citation texts mixed with lexicographer glosses dilute similarity scores
- `logos` returns 65 buckets because every sub-sense is treated independently

## Architecture: Lark Grammars

Following the pattern established in `src/langnet/whitakers_words/lineparsers/`:

```
src/langnet/parsing/
├── __init__.py
├── types.py                    # ParsedEntry, ParsedSense, ParsedCitation
├── cdsl/
│   ├── __init__.py
│   ├── cdsl_entry.ebnf         # Lark grammar for CDSL entries
│   └── cdsl_transformer.py     # Transformer → ParsedEntry
├── diogenes/
│   ├── __init__.py
│   ├── diogenes_block.ebnf     # Lark grammar for Diogenes blocks
│   └── diogenes_transformer.py # Transformer → ParsedEntry
├── cltk_lewis/
│   ├── __init__.py
│   ├── cltk_lewis_entry.ebnf   # Lark grammar for Lewis & Short entries
│   ├── cltk_lewis_transformer.py
│   └── author_abbrevs.py       # Ph., O., L., etc. lookup
└── heritage/
    ├── __init__.py
    ├── heritage_entry.ebnf
    └── heritage_transformer.py
```

Each dictionary gets its own grammar + transformer, matching Whitaker's pattern:

```python
# Example: cdsl_transformer.py
from lark import Lark, Transformer
from pathlib import Path

def get_cdsl_grammar():
    return (Path(__file__).parent / "cdsl_entry.ebnf").read_text()

class CDSLTransformer(Transformer):
    def start(self, args):
        return args[0]
    
    def entry_head(self, args):
        return {"headword": args[0], "gender": args[1] if len(args) > 1 else None}
    
    def root_spec(self, args):
        return {"root": args[0]}  # √ ag
    
    def sense_text(self, args):
        return {"gloss": args[0]}
    
    # ...

class CDSLParser:
    parser = Lark(get_cdsl_grammar())
    xformer = CDSLTransformer()
    
    @staticmethod
    def parse(line: str) -> ParsedEntry:
        tree = CDSLParser.parser.parse(line)
        return CDSLParser.xformer.transform(tree)
```

## Grammar Specifications

### CDSL Entry Grammar (`cdsl/cdsl_entry.ebnf`)

**Actual inputs** (from `repr()` of real output):
```
'agni/   m. (√ ag, Uṇ.) fire, sacrificial fire (of three kinds, Gārhapatya, Āhavanīya, and Dakṣiṇa)'
'bile, L.'
'gold, L.'
'the number three, Sūryas.'
```

```ebnf
start: entry

entry: entry_head? grammatical_spec* sense_body citation_abbrev?

entry_head: WORD "/" WS+         // "agni/   " (note: multiple spaces)

grammatical_spec: gender_spec | root_spec | grammar_ref

gender_spec: GENDER "."           // "m." "f." "n."

root_spec: "(" "√" ROOT_TEXT ["," grammar_ref] ")"  // "(√ ag, Uṇ.)"

grammar_ref: GRAM_ABBR "."        // "Uṇ." "RV." etc.

sense_body: sense_text (citation_abbrev sense_text)*

sense_text: /[^\n]+/

citation_abbrev: "," WS* CIT_ABBR "." // ", L." ", RV."

WORD: /[a-zA-Zāīūṛṝḷḹéóṃṁḥḍṭṇṣśṛ]+/
GENDER: /[mfn]+/
ROOT_TEXT: /[a-zA-Zāīūṛṝḷḹéóṃṁḥḍṭṇṣśṛ ]+/
GRAM_ABBR: /[A-Z][a-zṇśṭ]*/
CIT_ABBR: /[A-Z][a-z]?/

%import common.WS
```

### Diogenes Block Grammar (`diogenes/diogenes_block.ebnf`)

**Actual inputs** (from `repr()` of real output):
```
'I.  Lit.: torva leaena lupum sequitur, lupus ipse capellam, Verg. E. 2, 63; Plin. 10, 63, 88, § 173'
'β.  Lupum auribus tenere, to have a wolf by the ears, to be unable to hold and afraid to let go, T'
'1.  account of money handled, σανίδες εἰς ἃς τὸν λ. ἀναγράφομεν IG 1(2).374.191; ἐδίδοσαν τὸν λ. ib. 232.2'
'b.  public accounts, i. e. branch of treasury, ἴδιος λ., in Egypt, OGI 188.2, 189.3, 669.38'
```

**Key pattern**: Sense markers use `MARKER.  ` (period + TWO spaces) before content.

```ebnf
start: block

block: sense_marker? sense_content

sense_marker: (ROMAN | GREEK_LETTER | ARABIC | LOWERCASE) "." WS WS  // TWO spaces required!
            // "I.  " "β.  " "1.  " "b.  "

sense_content: etymology_note? gloss_body embedded_citations?

etymology_note: "verbal noun of" WORD 
              | "kindred with" WORD 
              | "cf." WORD

gloss_body: /[^,;]+/              // text before citations

embedded_citations: embedded_citation (";" embedded_citation)*

embedded_citation: citation_text source_ref

citation_text: /[A-Za-zāīūṛṝḷḹéóṃṁḥḍṭṇṣśṛ ]+/  // the actual classical text

source_ref: AUTHOR "." WORK? REF_NUMBERS?
          // "Verg. E. 2, 63" "IG 1(2).374.191" "S. OC 1225"

ROMAN: /[IVX]+/
GREEK_LETTER: /[αβγδεζηθικλμνξοπρστυφχψω]/
ARABIC: /[0-9]+/
LOWERCASE: /[a-z]/
AUTHOR: /[A-Z][a-z]+/
WORK: /[A-Z]?\.?[0-9]*/
REF_NUMBERS: /[0-9,\s§]+/

%import common.WS
%ignore WS  // except the TWO spaces after markers are significant!
```

**Challenge**: The two-space pattern after sense markers is structurally significant but `%ignore WS` would consume it. Need to handle explicitly in marker rule.

### CLTK Lewis Grammar (`cltk_lewis/cltk_lewis_entry.ebnf`)

**Actual inputs** (from `repr()` of real output):
```
'sēdō\n\n\n āvī, ātus, āre \n\nSED-, \nto bring to rest, lay\n: pulverem, Ph.—\nTo settle, still, calm...'
```

**Key patterns**:
- Headword with macrons: `sēdō`
- Principal parts: `āvī, ātus, āre`
- Root marker: `SED-,` (uppercase with hyphen)
- Senses separated by `—` (em-dash)
- Examples introduced by `: `
- Author abbreviations: `Ph.` (Phaedrus), `O.` (Ovid), `L.` (Livy), etc.
- Glosses wrapped in `\n...\n`

```ebnf
start: entry

entry: headword principal_parts? root_marker? sense_list

headword: LATIN_WORD         // "sēdō" (may have macrons)

principal_parts: PARTS_PART ("," PARTS_PART)*  // "āvī, ātus, āre"

root_marker: ROOT_CAPS "-,"   // "SED-," (uppercase root + hyphen)

sense_list: sense (EM_DASH sense)*

sense: sense_gloss example_list?

sense_gloss: /[^\n:—]+/       // text before : or —

example_list: example (":" example)*

example: example_text author_abbrev?

example_text: /[^,\n—]+/      // Latin example phrase

author_abbrev: "," WS* AUTHOR_ABBR "."  // ", Ph." ", O." ", L."

// Terminals
LATIN_WORD: /[a-zA-ZāēīōūȳăĕĭŏŭAEIOUY]+/
PARTS_PART: /[a-zA-Zāēīōūȳ]+/
ROOT_CAPS: /[A-Z]+/
AUTHOR_ABBR: /[A-Z][a-z]?/
EM_DASH: "—"

%import common.WS
%ignore WS  // But newlines are significant - handle in grammar
```

**Challenge**: Newlines are structurally significant. The `\nslake\n` pattern wraps English glosses inside examples. Need to preserve or strip these appropriately.

## Implementation Phases

### Phase 1: Types & Infrastructure (1 day)

**Files**:
- `src/langnet/parsing/__init__.py`
- `src/langnet/parsing/types.py`

```python
@dataclass
class ParsedEntry:
    headword: str
    language: str
    source: str
    source_ref: str | None = None
    pos: str | None = None
    gender: str | None = None
    root: str | None = None
    etymology_note: str | None = None
    principal_parts: list[str] = field(default_factory=list)  # CLTK Lewis: ["āvī", "ātus", "āre"]
    senses: list[ParsedSense] = field(default_factory=list)
    citations: list[ParsedCitation] = field(default_factory=list)
    raw_text: str = ""

@dataclass
class ParsedSense:
    gloss: str
    sense_id: str = ""
    domains: list[str] = field(default_factory=list)
    examples: list[ParsedExample] = field(default_factory=list)  # CLTK Lewis examples

@dataclass
class ParsedCitation:
    text: str
    source_ref: str
    cts_urn: str | None = None

@dataclass
class ParsedExample:
    """Example usage from Lewis & Short entries."""
    text: str              # "pulverem"
    author: str | None = None  # "Ph." (Phaedrus)
    gloss: str | None = None   # "slake" (newline-wrapped gloss)
```

### Phase 2: CDSL Lark Parser (2-3 days)

**Files**:
- `src/langnet/parsing/cdsl/__init__.py`
- `src/langnet/parsing/cdsl/cdsl_entry.ebnf`
- `src/langnet/parsing/cdsl/cdsl_transformer.py`
- `src/langnet/parsing/cdsl/citation_abbrevs.py`

**Validation**:
```bash
python -c "
from langnet.parsing.cdsl import CDSLParser

# Test root extraction
r = CDSLParser.parse('agni/   m. (√ ag, Uṇ.) fire, sacrificial fire')
assert r.headword == 'agni'
assert r.gender == 'm'
assert r.root == 'ag'
assert '√' not in r.senses[0].gloss

# Test citation abbreviation stripping
r = CDSLParser.parse('bile, L.')
assert r.senses[0].gloss == 'bile'
# L. should be identified as citation abbreviation, not part of gloss
"
```

### Phase 3: Diogenes Lark Parser (2-3 days)

**Files**:
- `src/langnet/parsing/diogenes/__init__.py`
- `src/langnet/parsing/diogenes/diogenes_block.ebnf`
- `src/langnet/parsing/diogenes/diogenes_transformer.py`

**Validation**:
```bash
python -c "
from langnet.parsing.diogenes import DiogenesParser

# Test sense marker parsing (two spaces!)
r = DiogenesParser.parse('I.  Lit.: torva leaena lupum sequitur, Verg. E. 2, 63')
assert r.sense_id == 'I'
assert 'torva leaena' in r.senses[0].gloss
assert 'Verg' in r.citations[0].source_ref

# Test Greek letter marker
r = DiogenesParser.parse('β.  Lupum auribus tenere, to have a wolf by the ears')
assert r.sense_id == 'β'

# Test Greek LSJ format
r = DiogenesParser.parse('1.  account of money handled, IG 1(2).374.191')
assert r.sense_id == '1'
assert 'account of money' in r.senses[0].gloss
"
```

### Phase 3b: CLTK Lewis Lark Parser (2 days)

**Files**:
- `src/langnet/parsing/cltk_lewis/__init__.py`
- `src/langnet/parsing/cltk_lewis/cltk_lewis_entry.ebnf`
- `src/langnet/parsing/cltk_lewis/cltk_lewis_transformer.py`
- `src/langnet/parsing/cltk_lewis/author_abbrevs.py` - Lewis & Short abbreviations

**Validation**:
```bash
python -c "
from langnet.parsing.cltk_lewis import CLTKLewisParser

# Test headword and principal parts
r = CLTKLewisParser.parse('sēdō\n\n\n āvī, ātus, āre \n\nSED-, \nto bring to rest, lay')
assert r.headword == 'sēdō'
assert r.principal_parts == ['āvī', 'ātus', 'āre']
assert r.root == 'SED'

# Test sense separation by em-dash
r = CLTKLewisParser.parse('to bring to rest, lay\n: pulverem, Ph.—\nTo settle, still')
assert len(r.senses) == 2
assert 'bring to rest' in r.senses[0].gloss
assert 'To settle' in r.senses[1].gloss

# Test author abbreviation extraction
r = CLTKLewisParser.parse('pulverem, Ph.')
assert r.senses[0].examples[0].text == 'pulverem'
assert r.senses[0].examples[0].author == 'Ph.'  # Phaedrus
"
```

### Phase 4: Adapter Integration (1-2 days)

Wire parsers into:
- `src/langnet/cologne/adapter.py` → uses `CDSLParser`
- `src/langnet/diogenes/adapter.py` → uses `DiogenesParser`
- `src/langnet/adapters/cltk.py` → uses `CLTKLewisParser`

### Phase 5: WSU Extraction Update (1 day)

Add `wsu_type` field to distinguish `sense` vs `citation` WSUs

## Success Metrics

### Before (Current State)
| Metric | Value |
|--------|-------|
| `logos` buckets | 65 (no multi-witness) |
| `agni` glosses with root noise | 3/10 contain "√" |
| `lupus` citations in gloss | 12/19 mixed |
| `ratio` citation extraction | 0 (embedded in text) |

### After (Target State)
| Metric | Value |
|--------|-------|
| `logos` buckets | ~20-30 (hierarchical clustering) |
| `agni` glosses with root noise | 0 |
| `lupus` citations separated | 100% |
| `ratio` citation extraction | All citations extracted |
| WSU types distinguished | `sense` vs `citation` |

## Edge Cases

1. **Ambiguous abbreviations**: `L.` could be lexicographers or a line number
   - Heuristic: position in entry, surrounding context
    
2. **Nested citations**: Entry text quotes other works
   - Track quote depth, attribute to correct source

3. **Multi-word roots**: `√ anj` vs `√ anu-jñā`
   - Parse until comma or closing paren

4. **Missing source refs**: Some Diogenes citations lack `.origjump`
   - Fallback to text pattern matching

## Related Documents

- **`docs/technical/design/entry-parsing.md`** - Design specification for parsing layer
- **`docs/plans/active/dictionary-entry-parsing-handoff.md`** - Handoff checklist for next developer
- `docs/plans/active/semantic-reduction/semantic-reduction-current-status.md` - Will benefit from this
- `docs/technical/design/classifier-and-reducer.md` - WSU extraction (downstream)
- `src/langnet/schema.py` - Current schema (will extend)
- `src/langnet/whitakers_words/lineparsers/` - Reference implementation

## Owners / Mentions

- @architect for parser design and types
- @coder for implementation
- @sleuth for edge case discovery via fuzzing
- @auditor for validation against golden snapshots
