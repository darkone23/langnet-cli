# Dictionary Entry Parsing: Handoff Checklist

**Date**: 2026-02-15
**Purpose**: Ensure another developer can pick up dictionary entry parsing work seamlessly
**Related Plan**: `docs/plans/active/dictionary-entry-parsing.md`

## 📋 Quick Start for Next Developer

### 1. Read These First (15 min)
1. `docs/plans/active/dictionary-entry-parsing.md` - Full plan
2. This document - Handoff context
3. `src/langnet/whitakers_words/lineparsers/` - Reference implementation

### 2. Understand the Problem (10 min)
```bash
# See what we're trying to fix - CDSL
python -c "
from langnet.core import LangnetWiring
w = LangnetWiring()
entries = w.engine.handle_query('san', 'agni')
for e in entries:
    if e.source == 'cdsl':
        for d in e.definitions[:3]:
            print(repr(d.definition[:80]))
" 2>/dev/null

# See what we're trying to fix - Diogenes
python -c "
from langnet.core import LangnetWiring
w = LangnetWiring()
entries = w.engine.handle_query('lat', 'lupus')
for e in entries:
    if e.source == 'diogenes':
        for b in e.dictionary_blocks[:3]:
            print(repr(b.entry[:80]))
" 2>/dev/null

# See what we're trying to fix - CLTK Lewis
python -c "
from langnet.core import LangnetWiring
w = LangnetWiring()
entries = w.engine.handle_query('lat', 'sedat')
for e in entries:
    if e.source == 'cltk':
        for d in e.definitions[:1]:
            print(repr(d.definition[:200]))
" 2>/dev/null
```

**What you should see wrong**:
- `'bile, L.'` - "L." is a citation abbreviation, not part of the sense (CDSL)
- `'agni/   m. (√ ag, Uṇ.) fire...'` - Root symbol √ polluting sense text (CDSL)
- `'I.  Lit.: torva leaena lupum sequitur, Verg. E. 2, 63'` - Citation text mixed with source ref (Diogenes)
- `'sēdō\n\n\n āvī, ātus, āre \n\nSED-, \nto bring to rest...'` - Principal parts, root, and senses all mixed (CLTK Lewis)
- `'...pulverem, Ph.—\nTo settle...'` - Em-dash sense separator, author abbrevs embedded (CLTK Lewis)

### 3. Study the Reference Implementation
```bash
# Whitaker's already uses Lark grammars - copy this pattern
cat src/langnet/whitakers_words/lineparsers/parse_senses.py
cat src/langnet/whitakers_words/lineparsers/grammars/senses.ebnf
```

## 🎯 Design Principles

### WSU Types vs Grammatical Metadata

**Critical distinction**: Not everything extracted becomes a WSU.

| Becomes WSU | Stays as Entry Metadata |
|-------------|------------------------|
| Senses (lexicographer definitions) | POS (part of speech) |
| Citations (usage examples) | Gender (m/f/n) |
| | Root (√ ag) |
| | Principal parts (āvī, ātus, āre) |
| | Conjugation/declension class |

**Why**: WSUs exist for semantic similarity clustering. "Noun" doesn't cluster with "noun" - it's a grammatical category, not semantic content. POS is used for **filtering**, not clustering.

See `docs/technical/design/04-entry-parsing.md` for full rationale.

## ✅ Success Criteria

### Phase 1: Types & Infrastructure
- [ ] `ParsedEntry`, `ParsedSense`, `ParsedCitation` dataclasses defined
- [ ] Types importable from `langnet.parsing.types`
- [ ] Unit tests for type construction pass

### Phase 2: CDSL Parser
- [ ] Grammar parses all 10 `agni` definitions without errors
- [ ] Root extraction: `√ ag` → `root="ag"` (not in gloss)
- [ ] Citation abbreviation stripping: `bile, L.` → `gloss="bile"`
- [ ] Gender extraction: `m.` → `gender="m"`
- [ ] Headword extraction: `agni/` → `headword="agni"`
- [ ] Grammar reference preserved: `Uṇ.` in metadata, not discarded

**Validation command**:
```bash
python -c "
from langnet.parsing.cdsl import CDSLParser

# Must pass
r = CDSLParser.parse('agni/   m. (√ ag, Uṇ.) fire, sacrificial fire')
assert r.headword == 'agni'
assert r.gender == 'm'
assert r.root == 'ag'
assert '√' not in r.senses[0].gloss
assert 'fire' in r.senses[0].gloss

# Must pass
r = CDSLParser.parse('bile, L.')
assert r.senses[0].gloss == 'bile'
print('CDSL parser: OK')
"
```

### Phase 3: Diogenes Parser
- [ ] Grammar parses `lupus` blocks (16 blocks) without errors
- [ ] Grammar parses `logos` blocks (65 blocks) without errors
- [ ] Sense marker extraction: `I.  ` → `sense_id="I"`
- [ ] Two-space pattern recognized (not consumed by WS ignore)
- [ ] Citation text separated from source ref
- [ ] Greek letter markers handled: `β.  ` → `sense_id="β"`
- [ ] Arabic numeral markers handled: `1.  ` → `sense_id="1"`

**Validation command**:
```bash
python -c "
from langnet.parsing.diogenes import DiogenesParser

# Must pass - Latin
r = DiogenesParser.parse('I.  Lit.: torva leaena lupum sequitur, Verg. E. 2, 63')
assert r.sense_id == 'I'
assert 'torva leaena' in r.senses[0].gloss
assert 'Verg' in r.citations[0].source_ref

# Must pass - Greek letter marker
r = DiogenesParser.parse('β.  Lupum auribus tenere, to have a wolf by the ears')
assert r.sense_id == 'β'

# Must pass - LSJ format
r = DiogenesParser.parse('1.  account of money handled, IG 1(2).374.191')
assert r.sense_id == '1'
print('Diogenes parser: OK')
"
```

### Phase 3b: CLTK Lewis Parser
- [ ] Grammar parses `sedat` Lewis entry without errors
- [ ] Headword extraction: `sēdō` with macrons preserved
- [ ] Principal parts extraction: `āvī, ātus, āre`
- [ ] Root marker extraction: `SED-,` → `root="SED"`
- [ ] Em-dash sense separation: senses split by `—`
- [ ] Author abbreviation extraction: `Ph.` → Phaedrus, `O.` → Ovid
- [ ] Newline-wrapped glosses handled: `\nslake\n` → "slake"

**Validation command**:
```bash
python -c "
from langnet.parsing.cltk_lewis import CLTKLewisParser

# Must pass - headword and principal parts
r = CLTKLewisParser.parse('sēdō\n\n\n āvī, ātus, āre \n\nSED-, \nto bring to rest')
assert r.headword == 'sēdō'
assert r.root == 'SED'

# Must pass - em-dash sense separation
r = CLTKLewisParser.parse('to bring to rest—\nTo settle, still')
assert len(r.senses) == 2
assert 'bring to rest' in r.senses[0].gloss
assert 'To settle' in r.senses[1].gloss

# Must pass - author abbreviation
r = CLTKLewisParser.parse('pulverem, Ph.')
assert 'Ph.' in str(r.senses[0].examples)
print('CLTK Lewis parser: OK')
"
```

### Phase 4: Adapter Integration
- [ ] `cologne/adapter.py` uses `CDSLParser`
- [ ] `diogenes/adapter.py` uses `DiogenesParser`
- [ ] Existing API responses unchanged (backward compatible)
- [ ] New fields populated: `root`, `etymology_note`, clean `gloss`

### Phase 5: WSU Extraction
- [ ] `wsu_extractor.py` generates `wsu_type="sense"` for glosses
- [ ] `wsu_extractor.py` generates `wsu_type="citation"` for citations
- [ ] Semantic reduction uses new WSU types correctly
- [ ] `logos` bucket count decreases from 65 to ~20-30

## ⚠️ Potential Roadblocks

### 1. Lark Grammar Complexity

**Problem**: The two-space pattern `MARKER.  ` in Diogenes conflicts with `%ignore WS`.

**Symptoms**: Parser fails to distinguish sense markers from regular text.

**Solution**:
```ebnf
# Don't use %ignore WS for Diogenes - handle whitespace explicitly
sense_marker: (ROMAN | GREEK_LETTER) "." "  "  # Literal two spaces
```

**Fallback**: Pre-process to replace `"  "` with `"\t"` before parsing.

### 2. CDSL Citation Abbreviation Ambiguity

**Problem**: `L.` could be:
- Lassen (Sanskrit scholar citation)
- A line number reference
- Part of the actual definition

**Symptoms**: Parser strips valid content or keeps citation noise.

**Solution**: Build lookup table of known abbreviations:
```python
# src/langnet/parsing/cdsl/citation_abbrevs.py
CDSL_CITATION_ABBREVS = {
    "L.": "Lassen",
    "RV.": "Rig Veda",
    "AV.": "Atharva Veda",
    "TS.": "Taittiriya Samhita",
    # ... (see MW preface for full list)
}
```

**Heuristic**: Only strip if abbreviation appears at end of sense text (before newline).

### 3. Greek Unicode in Lark

**Problem**: Greek characters in LSJ entries may not match terminal patterns.

**Symptoms**: Parser fails on entries with `λόγος`, `ὁ`, etc.

**Solution**: Use Unicode ranges in terminals:
```ebnf
GREEK_LETTER: /[\u0370-\u03FF]/
GREEK_WORD: /[\u0370-\u03FF]+/
```

### 4. Nested Citation Structures

**Problem**: Some Diogenes entries have citations within citations.

**Example**: `"text (cf. Author. Work 1.2), more text, Other. 3.4"`

**Symptoms**: Parser incorrectly splits citation text.

**Solution**: Parse parentheses as a unit, defer nested citations to post-processing.

### 5. Performance on Large Entries

**Problem**: `logos` has 65 blocks; parser may be slow.

**Symptoms**: Query latency increases significantly.

**Mitigation**:
- Profile parser with `cProfile`
- Cache parsed entries in DuckDB
- Consider incremental parsing for very large entries

### 6. CLTK Lewis Newline Structure

**Problem**: Lewis entries use `\n` in multiple ways:
- `\n\n\n` before principal parts
- `\n\n` before root marker
- `\n` before sense text
- `\n...\n` wrapping glosses inside examples

**Symptoms**: Parser conflates different newline patterns, produces garbled output.

**Solution**: Handle newlines explicitly in grammar, not via `%ignore WS`:
```ebnf
entry: headword "\n\n\n" principal_parts "\n\n" root_marker "\n" sense_list
example: example_text ("\n" gloss "\n")? author_abbrev?
```

**Fallback**: Pre-process to normalize newlines, or use regex pre-parsing for header section.

## 💥 Breaking Changes

### 1. DictionaryDefinition Schema Extension

**Change**: Add new fields to `DictionaryDefinition`.

```python
# Before
@dataclass
class DictionaryDefinition:
    definition: str
    pos: str
    gender: str | None = None
    etymology: str | None = None

# After
@dataclass
class DictionaryDefinition:
    definition: str          # Now CLEAN (no root/citation noise)
    pos: str
    gender: str | None = None
    etymology: str | None = None
    root: str | None = None          # NEW: extracted root
    etymology_note: str | None = None  # NEW: "verbal noun of..."
    citations: list[Citation] = field(default_factory=list)  # NEW: extracted
```

**Impact**: Existing code accessing `definition` sees cleaner text.

**Migration**: None required - new fields are optional with defaults.

### 2. DictionaryBlock.content Split

**Change**: Split `entry` field into structured parts.

```python
# Before
@dataclass  
class DictionaryBlock:
    entry: str  # "I.  Lit.: torva leaena..., Verg. E. 2, 63"
    entryid: str
    citations: dict[str, str]  # Only URN mappings

# After
@dataclass
class DictionaryBlock:
    entry: str              # Original (preserved for compatibility)
    entryid: str
    sense_id: str | None = None      # NEW: "I", "β", "1"
    sense_gloss: str | None = None   # NEW: "torva leaena..."
    embedded_citations: list[EmbeddedCitation] = field(default_factory=list)  # NEW
    citations: dict[str, str]  # Existing, now populated from embedded
```

**Impact**: Existing code using `entry` still works. New code can use structured fields.

**Migration**: Update consumers to use `sense_gloss` for cleaner text.

### 3. WSU Type Field Addition

**Change**: Add `wsu_type` to `WitnessSenseUnit`.

```python
# Before
@dataclass
class WitnessSenseUnit:
    source: str
    sense_ref: str
    gloss_raw: str
    gloss_normalized: str

# After  
@dataclass
class WitnessSenseUnit:
    source: str
    sense_ref: str
    gloss_raw: str
    gloss_normalized: str
    wsu_type: str = "sense"  # NEW: "sense" | "citation"
```

**Impact**: Semantic reduction can now cluster senses and citations separately.

**Migration**: Update similarity scoring to weight by type.

### 4. Adapter Return Value Changes

**Change**: Adapters return cleaner `definition` text.

**Before**: `'bile, L.'`
**After**: `'bile'`

**Impact**: Downstream code expecting citation abbreviations in gloss text will break.

**Mitigation**: Check `citations` field for extracted abbreviations.

### 5. CLTK Lewis Principal Parts and Root

**Change**: CLTK adapter returns structured principal parts and root.

```python
# Before
@dataclass
class DictionaryDefinition:
    definition: str  # Contains "sēdō\n\n\n āvī, ātus, āre \n\nSED-,..."
    
# After
@dataclass
class DictionaryDefinition:
    definition: str              # Cleaned: "to bring to rest, lay"
    principal_parts: list[str]   # NEW: ["āvī", "ātus", "āre"]
    root: str | None = None      # NEW: "SED"
```

**Impact**: `definition` field is cleaner but loses principal parts info.

**Mitigation**: Use new `principal_parts` field for verb conjugation info.

## 🧪 Testing Strategy

### Unit Tests Required

```
tests/test_parsing/
├── test_cdsl_parser.py
│   ├── test_root_extraction
│   ├── test_gender_extraction
│   ├── test_citation_abbrev_stripping
│   ├── test_headword_extraction
│   └── test_edge_cases
├── test_diogenes_parser.py
│   ├── test_sense_marker_roman
│   ├── test_sense_marker_greek
│   ├── test_sense_marker_arabic
│   ├── test_citation_separation
│   └── test_lsj_format
├── test_cltk_lewis_parser.py
│   ├── test_headword_with_macrons
│   ├── test_principal_parts_extraction
│   ├── test_root_marker_extraction
│   ├── test_em_dash_sense_separation
│   ├── test_author_abbrev_extraction
│   └── test_newline_wrapped_glosses
└── fixtures/
    ├── cdsl_agni.json
    ├── diogenes_lupus.json
    ├── diogenes_logos.json
    └── cltk_lewis_sedat.json
```

### Integration Tests Required

```
tests/test_parsing_integration.py
├── test_cdsl_adapter_uses_parser
├── test_diogenes_adapter_uses_parser
├── test_wsu_extraction_with_types
└── test_semantic_reduction_improved_clustering
```

### Golden Snapshot Tests

Create expected outputs for known entries:

```bash
# After implementation, run:
python -c "
from langnet.parsing.cdsl import CDSLParser
from langnet.parsing.diogenes import DiogenesParser
import json

# CDSL snapshots
for text in [
    'agni/   m. (√ ag, Uṇ.) fire, sacrificial fire',
    'bile, L.',
    'the number three, Sūryas.',
]:
    result = CDSLParser.parse(text)
    print(json.dumps(result.__dict__, indent=2))

# Diogenes snapshots  
for text in [
    'I.  Lit.: torva leaena lupum sequitur, Verg. E. 2, 63',
    'β.  Lupum auribus tenere, to have a wolf by the ears',
    '1.  account of money handled, IG 1(2).374.191',
]:
    result = DiogenesParser.parse(text)
    print(json.dumps(result.__dict__, indent=2))
" > tests/fixtures/parsing_golden_snapshots.json
```

## 📁 File Structure After Implementation

```
src/langnet/parsing/
├── __init__.py              # Exports: ParsedEntry, CDSLParser, DiogenesParser, CLTKLewisParser
├── types.py                 # ParsedEntry, ParsedSense, ParsedCitation
├── cdsl/
│   ├── __init__.py
│   ├── cdsl_entry.ebnf      # Lark grammar
│   ├── cdsl_transformer.py  # Lark Transformer
│   └── citation_abbrevs.py  # L., RV., etc. lookup
├── diogenes/
│   ├── __init__.py
│   ├── diogenes_block.ebnf  # Lark grammar
│   └── diogenes_transformer.py
└── cltk_lewis/
    ├── __init__.py
    ├── cltk_lewis_entry.ebnf  # Lark grammar
    ├── cltk_lewis_transformer.py
    └── author_abbrevs.py    # Ph., O., L., etc. lookup

tests/test_parsing/
├── __init__.py
├── test_cdsl_parser.py
├── test_diogenes_parser.py
├── test_cltk_lewis_parser.py
└── fixtures/
    ├── cdsl_samples.json
    ├── diogenes_samples.json
    ├── cltk_lewis_samples.json
    └── golden_snapshots.json
```

## 🚦 Pre-Implementation Checklist

Before writing any code, verify:

- [ ] Read `docs/plans/active/dictionary-entry-parsing.md` completely
- [ ] Understood the Whitaker's Lark parser pattern
- [ ] Ran the "See what we're trying to fix" commands above
- [ ] Confirmed Lark is in dependencies (`grep lark pyproject.toml`)
- [ ] Reviewed `src/langnet/schema.py` for current types
- [ ] Understood semantic reduction WSU extraction flow

## 🎯 Definition of Done

A parser is "done" when:

1. **All sample inputs parse without errors**
   - 10+ CDSL definitions (agni, deva, etc.)
   - 20+ Diogenes blocks (lupus, logos, ratio)

2. **Extraction is accurate**
   - Roots extracted, not in gloss
   - Citation abbrevs stripped, not in gloss
   - Sense markers captured
   - Citations separated from source refs

3. **No regressions**
   - Existing API responses still valid
   - Semantic reduction still produces buckets
   - No new type errors in `just typecheck`

4. **Tests pass**
   - Unit tests for parser
   - Integration tests for adapter wiring
   - Golden snapshot tests match

---

*Update this checklist as you learn during implementation. Add new roadblocks and solutions for the next developer.*
