# Langnet CLI Pedagogical Roadmap

## Philosophy

**Foster functional grammar as a default pedagogical approach** — always show what words *do* in sentences, not just technical categories. This applies to **Greek, Latin, and Sanskrit**.

Display format: **Technical Term + Foster Function** (e.g., "Nominative (Naming Function)")

The goal is to transform langnet-cli into a **pedagogical engine** rather than just a **data browser**. This means ruthlessly prioritizing features that help learners understand word function in context, inspired by Reginald Foster's functional approach to language teaching.

---

## The "Bang for the Buck" Matrix

| Priority | Feature | Effort | Pedagogical Impact | Why it matters |
| --- | --- | --- | --- | --- |
| **P0** | **Lemmatization** | Low | **Huge** | Beginners can't use a dictionary if they can't find the headword. |
| **P0** | **Foster Functional Grammar** | Low | **Huge** | Students learn grammar by understanding what words *do*, not just technical labels. |
| **P1** | **Citation Display** | Medium | **Huge** | Foster's method: "See the word in the wild." |
| **P1** | **Fuzzy Searching** | Low | High | Handles typos and orthographic variants (e.g., *v* vs *u*). |
| **P2** | **CDSL Reference Enhancement** | Low | High | Display `<ls>` lexicon references for cross-dictionary exploration. |
| **P2** | **Enhanced Citation Formatting** | Low | Medium | Display citations in learner-friendly format. |
| **P3** | **Cross-Lexicon Etymology** | High | Medium | Amazing for philology, but secondary for day-to-day learning. |
| **P3** | **Performance/Scaling** | High | **Low** | DuckDB is already fast enough for a single-user CLI. |

---

## Phase 1: Sanskrit Foundation (P0 - Critical)

### Goal: Make Sanskrit as functional as Latin/Greek for learners

### Current State

| Feature | Latin | Greek | Sanskrit |
|---------|-------|-------|----------|
| Lemmatization | CLTK ✅ | spaCy ✅ | CLTK ✅ |
| Morphology | Whitaker's ✅ | spaCy ✅ | CLTK ✅ (inflection morphology via CLTK) |
| Dictionary lookup | Lewis ✅ | Diogenes ✅ | CDSL ✅ |

### 1.1 Integrate CLTK SanskritPipeline

**File:** `src/langnet/classics_toolkit/core.py`

Add to existing `ClassicsToolkit` class:

```python
from cltk import NLP
from dataclasses import dataclass

@dataclass
class SanskritMorphologyResult:
    lemma: str
    pos: str
    morphological_features: dict

def sanskrit_morphology_query(self, word: str) -> SanskritMorphologyResult:
    """Use CLTK SanskritPipeline for morphological analysis"""
    cltk_nlp = NLP(language="san")
    cltk_doc = cltk_nlp.analyze(text=word)
    
    first_word = cltk_doc.sentences[0][0]
    return SanskritMorphologyResult(
        lemma=first_word.lemma,
        pos=first_word.upos,
        morphological_features=first_word.features
    )
```

**Pedagogical Value:** Users can search `योगेन` (instrumental) and get `yoga` (stem) + morphology

### 1.2 Sanskrit Lemmatization Fallback

**File:** `src/langnet/engine/core.py`

Modify `handle_query()` method:

```python
if lang == "san":
    # Try direct CDSL lookup
    result = cologne.lookup_ascii(word)
    
    # If no results, try lemmatized form via CLTK
    if not result or not result.get("cologne"):
        morphology = classics_toolkit.sanskrit_morphology_query(word)
        if morphology.lemma:
            result = cologne.lookup_ascii(morphology.lemma)
            if result:
                result["_lemmatized_from"] = word  # Track transformation
```

**Example:** User searches `योगेन` → CLTK returns `yoga` → CDSL lookup succeeds

### 1.3 Display Sanskrit Root Prominently

**Current:** CDSL captures etymology: `{"type": "verb_root", "root": "ag"}`  
**File:** `src/langnet/cologne/core.py` or CLI formatter

Display at top of results:
```
ROOT: √ag (fire, motion)
WORD: agni
DEFINITION: fire, god of fire
```

**Pedagogical Value:** Connecting to roots is fundamental in Sanskrit pedagogy

---

## Phase 2: Foster Functional Grammar (P0 - Core Philosophy)

### Goal: Translate technical grammar into learner-friendly language for **all three languages**

### 2.1 Foster Mapping Module

**File:** New `src/langnet/foster/__init__.py`

```python
from langnet.foster.latin import FOSTER_LATIN_CASES, FOSTER_LATIN_TENSES
from langnet.foster.greek import FOSTER_GREEK_CASES, FOSTER_GREEK_TENSES
from langnet.foster.sanskrit import FOSTER_SANSKRIT_CASES, FOSTER_SANSKRIT_TENSES
```

**File:** New `src/langnet/foster/latin.py`

```python
FOSTER_LATIN_CASES = {
    "nom": "Naming Function",
    "voc": "Calling Function",
    "acc": "Receiving Function",
    "gen": "Possessing Function",
    "dat": "To-For Function",
    "abl": "By-With-From-In Function",
    "loc": "In Function",
}

FOSTER_LATIN_TENSES = {
    "pres": "Time-Now Function",
    "fut": "Time-Later Function",
    "perf": "Time-Past Function",
    "imperf": "Time-Was-Doing Function",
    "plup": "Time-Had-Done Function",
}

FOSTER_LATIN_GENDERS = {
    "masc": "Male Function",
    "fem": "Female Function",
    "neut": "Neuter Function",
}

FOSTER_LATIN_NUMBERS = {
    "sg": "Single Function",
    "pl": "Group Function",
}

FOSTER_LATIN_MISCELLANEOUS = {
    "part": "Participle Function",
    "act": "Doing Function",
    "pass": "Being-Done-To Function",
    "ind": "Statement Function",
    "subj": "Wish-May-Be Function",
}
```

**File:** New `src/langnet/foster/greek.py`

```python
FOSTER_GREEK_CASES = {
    "nom": "Naming Function",
    "voc": "Calling Function",
    "acc": "Receiving Function",
    "gen": "Possessing Function",
    "dat": "To-For Function",
}

FOSTER_GREEK_TENSES = {
    "pres": "Time-Now Function",
    "fut": "Time-Later Function",
    "perf": "Time-Past Function",
    "aor": "Once-Done Function",
    "imperf": "Time-Was-Doing Function",
    "plup": "Time-Had-Done Function",
}

FOSTER_GREEK_GENDERS = {
    "masc": "Male Function",
    "fem": "Female Function",
    "neut": "Neuter Function",
}

FOSTER_GREEK_NUMBERS = {
    "sg": "Single Function",
    "pl": "Group Function",
    "dual": "Pair Function",
}

FOSTER_GREEK_MISCELLANEOUS = {
    "act": "Doing Function",
    "mid": "For-Self Function",
    "pass": "Being-Done-To Function",
    "ind": "Statement Function",
    "subj": "Wish-May-Be Function",
    "opt": "Maybe-Will-Do Function",
    "imper": "Command Function",
}
```

**File:** New `src/langnet/foster/sanskrit.py`

```python
# CDSL uses numbers (1-8) for cases
FOSTER_SANSKRIT_CASES = {
    "1": "Naming Function",
    "2": "Receiving Function",
    "3": "By-With Function",  # ← Foster's instrumental emphasis
    "4": "To-For Function",
    "5": "From Function",
    "6": "Possessing Function",
    "7": "In-Where Function",
    "8": "Oh! Function",
}

FOSTER_SANSKRIT_GENDERS = {
    "m": "Male Function",
    "f": "Female Function",
    "n": "Neuter Function",
}

FOSTER_SANSKRIT_NUMBERS = {
    "s": "Single Function",
    "d": "Pair Function",
    "p": "Group Function",
}
```

### 2.2 Apply Foster View (Always On)

**File:** New `src/langnet/foster/apply.py`

```python
from langnet.foster.latin import FOSTER_LATIN_CASES, FOSTER_LATIN_TENSES, FOSTER_LATIN_GENDERS, FOSTER_LATIN_NUMBERS, FOSTER_LATIN_MISCELLANEOUS
from langnet.foster.greek import FOSTER_GREEK_CASES, FOSTER_GREEK_TENSES, FOSTER_GREEK_GENDERS, FOSTER_GREEK_NUMBERS, FOSTER_GREEK_MISCELLANEOUS
from langnet.foster.sanskrit import FOSTER_SANSKRIT_CASES, FOSTER_SANSKRIT_GENDERS, FOSTER_SANSKRIT_NUMBERS

def apply_foster_view(result: dict) -> dict:
    """Add Foster functional labels to morphology - always displayed"""

    # Apply to Diogenes morphology (Latin and Greek)
    if "diogenes" in result:
        for chunk in result["diogenes"]["chunks"]:
            if "morphology" in chunk:
                for morph in chunk["morphology"]["morphs"]:
                    foster_tags = []
                    for tag in morph["tags"]:
                        foster_term = None

                        # Try Latin mappings
                        if tag in FOSTER_LATIN_CASES:
                            foster_term = FOSTER_LATIN_CASES[tag]
                        elif tag in FOSTER_LATIN_TENSES:
                            foster_term = FOSTER_LATIN_TENSES[tag]
                        elif tag in FOSTER_LATIN_GENDERS:
                            foster_term = FOSTER_LATIN_GENDERS[tag]
                        elif tag in FOSTER_LATIN_NUMBERS:
                            foster_term = FOSTER_LATIN_NUMBERS[tag]
                        elif tag in FOSTER_LATIN_MISCELLANEOUS:
                            foster_term = FOSTER_LATIN_MISCELLANEOUS[tag]

                        # Try Greek mappings (if not found in Latin)
                        elif tag in FOSTER_GREEK_CASES:
                            foster_term = FOSTER_GREEK_CASES[tag]
                        elif tag in FOSTER_GREEK_TENSES:
                            foster_term = FOSTER_GREEK_TENSES[tag]
                        elif tag in FOSTER_GREEK_GENDERS:
                            foster_term = FOSTER_GREEK_GENDERS[tag]
                        elif tag in FOSTER_GREEK_NUMBERS:
                            foster_term = FOSTER_GREEK_NUMBERS[tag]
                        elif tag in FOSTER_GREEK_MISCELLANEOUS:
                            foster_term = FOSTER_GREEK_MISCELLANEOUS[tag]

                        if foster_term:
                            foster_tags.append(f"{tag} ({foster_term})")
                        else:
                            foster_tags.append(tag)

                    morph["foster_function"] = foster_tags

    # Apply to CLTK Greek morphology
    if "cltk" in result and "greek_morphology" in result["cltk"]:
        morph_features = result["cltk"]["greek_morphology"]["morphological_features"]
        foster_features = {}

        for key, value in morph_features.items():
            key_lower = key.lower() if isinstance(key, str) else str(key).lower()
            value_lower = value.lower() if isinstance(value, str) else str(value).lower()

            if key_lower == "case":
                foster_term = FOSTER_GREEK_CASES.get(value_lower, value)
                foster_features["case"] = f"{value} ({foster_term})"
            elif key_lower == "tense":
                foster_term = FOSTER_GREEK_TENSES.get(value_lower, value)
                foster_features["tense"] = f"{value} ({foster_term})"
            # ... more mappings

        result["cltk"]["greek_morphology"]["foster_view"] = foster_features

    # Apply to CDSL Sanskrit entries
    if "cologne" in result:
        for dict_name, entries in result["cologne"]["dictionaries"].items():
            for entry in entries:
                if entry.get("grammar_tags"):
                    foster_tags = {}

                    # Map declension
                    if "declension" in entry["grammar_tags"]:
                        decl = entry["grammar_tags"]["declension"]
                        # Can map to Foster if needed

                    foster_tags["original"] = entry["grammar_tags"]
                    entry["foster_view"] = foster_tags

    return result
```

**File:** `src/langnet/engine/core.py`

Integrate into `LanguageEngine`:

```python
def handle_query(self, lang: str, word: str) -> dict:
    # ... existing query logic ...

    # Always apply Foster view
    result = apply_foster_view(result)

    return result
```

**Key Decision:** Foster terms are added to results **by default**, not via flag

### 2.3 CLI Display Format

**File:** `src/langnet/cli.py`

Format output to show technical term + Foster function together:

```
Morphology:
  Nominal: Nominative (Naming Function), Masculine (Male Function), Singular (Single Function)
  Verbal: Future (Time-Later Function), Participle (Participle Function), Active (Doing Function)
```

**API Response Format:**

```json
{
  "diogenes": {
    "chunks": [{
      "morphology": {
        "morphs": [{
          "tags": ["fut", "part", "act", "masc", "nom", "voc", "pl"],
          "foster_function": [
            "fut (Time-Later Function)",
            "part (Participle Function)",
            "act (Doing Function)",
            "masc (Male Function)",
            "nom (Naming Function)",
            "voc (Calling Function)",
            "pl (Group Function)"
          ]
        }]
      }
    }]
  }
}
```

**Pedagogical Value:** Students learn traditional terms by seeing them with functional descriptions

---

## Phase 3: Lemmatization Infrastructure (P1 - High Priority)

### Goal: Ensure users can find headwords across all languages

### 3.1 Fuzzy Searching & Typo Tolerance

**File:** `src/langnet/engine/core.py` or new `src/langnet/fuzzy/core.py`

Implement Levenshtein distance fallback:

```python
def fuzzy_search(word: str, language: str, threshold=0.8) -> list[str]:
    """Find similar headwords on miss"""
    # When direct lookup fails, use fuzzy matching
    # e.g., 'amavit' might suggest 'amabat'
    pass
```

**Effort:** Low  
**Pedagogical Value:** High — students can learn despite typos and orthographic variants

### 3.2 Backoff Lemmatization Chain

**File:** `src/langnet/engine/core.py`

Implement priority order:

```python
def handle_query(self, lang: str, word: str) -> dict:
    # 1. Direct lookup
    result = self._lookup_direct(lang, word)
    
    if not result or not result.get(lang):
        # 2. Try fuzzy matching
        result = self._lookup_fuzzy(lang, word)
    
    if not result or not result.get(lang):
        # 3. Try lemmatization
        if lang == "san":
            result = self._lookup_via_lemmatizer(lang, word)
        elif lang == "lat":
            result = self._lookup_via_lemmatizer(lang, word)
        elif lang == "grc":
            result = self._lookup_via_lemmatizer(lang, word)
    
    if result:
        result["_search_method"] = "direct|fuzzy|lemmatized"
    
    return result
```

---

## Phase 4: Citation Display & Context (P1 - High Priority)

### Goal: Foster's method — "See the word in the wild"

### 4.1 Regex Citation Extraction

**File:** New `src/langnet/diogenes/citation_formatter.py`

```python
def format_citations(citations: dict) -> list[dict]:
    """Transform raw citations into learner-friendly format"""
    formatted = []
    for ref_id, ref_text in citations.items():
        # Parse "perseus:abo:phi,1254,001:2:19:6"
        # Extract: Author, Work, Book, Section, Line
        author = parse_author_from_ref(ref_id)
        formatted.append({
            "author": author,
            "reference": ref_text,
            "original_id": ref_id,
            "context_snippet": extract_context(ref_text)
        })
    return formatted
```

**Pedagogical Value:** Students see the word used in real classical texts

### 4.2 Snippet Previews & Context

For each citation, provide a "one-line context" from parsed lexicon data.

**Example:**

```
Citations:
  - Cicero (Cic. Off. 1.2.5): "...in rerum gestarum..."
  - Virgil (Verg. Aen. 2.101): "...arma virumque cano..."
```

### 4.3 Morphology Breakdown Prominently

Display principal parts (Latin) or the root/class (Sanskrit) at the top of results.

---

## Phase 5: CDSL Reference Enhancement (P2 - Nice-to-Have)

### Goal: Display CDSL `<ls>` tags (lexicon references)

### Current State

CDSL parser captures `<ls>` tags but doesn't display them:
```python
references: [{"source": "L.", "type": "lexicon"}]
```

### 5.1 Display Lexicon References

**File:** `src/langnet/cologne/core.py` or CLI formatter

```python
def format_sanskrit_entry(entry: SanskritDictionaryEntry) -> str:
    """Format Sanskrit entry with lexicon references"""
    lines = []

    # Root first (if available)
    if entry.etymology:
        etype = entry.etymology.get("type")
        if etype == "verb_root":
            root = entry.etymology.get("root")
            lines.append(f"ROOT: √{root}")

    # Definition
    lines.append(f"DEFINITION: {entry.meaning}")

    # Grammar info
    if entry.pos:
        lines.append(f"PART OF SPEECH: {entry.pos}")

    # Lexicon references (from <ls> tags)
    if entry.references:
        lex_refs = [r["source"] for r in entry.references if r["type"] == "lexicon"]
        if lex_refs:
            lines.append(f"SEE ALSO: {', '.join(lex_refs)}")

    return "\n".join(lines)
```

**Example Output:**

```
ROOT: √ag (to move, go)
DEFINITION: fire, god of fire
PART OF SPEECH: m.
SEE ALSO: L., TS., Vop.
```

**Pedagogical Value:** Helps students explore related entries in dictionary

---

## Phase 6: Dictionary Entry Parsers (P2 - Infrastructure)

### Goal: Improve parsing of dictionary entries across all data sources

### 6.1 Lewis Latin Parser

**File:** `src/langnet/classics_toolkit/core.py`

Parse CLTK's `LatinLewisLexicon.lookup()` raw text into structured `LewisEntry` dataclass:

- [ ] Analyze Lewis entry format: headword, part of speech, etymology, definitions, word family, citations
- [ ] Create `LewisEntry` model with robust handling of edge cases
- [ ] Wire parsed output to `LatinQueryResult`
- [ ] Add comprehensive test coverage

### 6.2 CDSL Entry Enhancements

**File:** `src/langnet/cologne/parser.py`

Improve Sanskrit dictionary entry parsing:

- [ ] Parse granular sense structures from MW/AP90 entries
- [ ] Extract citation references (Ṛgveda, etc.) as linked data
- [ ] Handle variant readings and alternate etymologies
- [ ] Improve Devanagari/IAST/HK transliteration consistency

### 6.3 Diogenes Greek & Latin Parser

**File:** `src/langnet/diogenes/parser.py`

Improve Greek and Latin lexicon entry structuring:

- [ ] Parse morphological annotations into structured morphology data
- [ ] Extract semantic relationships between senses
- [ ] Handle cross-references and citations

---

## Phase 7: Local Data Storage Layer (P3 - Future Infrastructure)

### Goal: Build a language-neutral knowledge base for derived lexicon data

### Schema Design

```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    term VARCHAR NOT NULL,
    language VARCHAR NOT NULL,
    headword VARCHAR,
    ipa VARCHAR,
    part_of_speech VARCHAR
);

CREATE TABLE senses (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    definition VARCHAR,
    citations VARCHAR,
    source_lemma VARCHAR,
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE morphology (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    tags VARCHAR,
    stems VARCHAR,
    endings VARCHAR,
    FOREIGN KEY (word_id) REFERENCES words(id)
);

CREATE TABLE cognates (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    related_word_id INTEGER,
    relationship_type VARCHAR,
    related_word_language VARCHAR,
    FOREIGN KEY (word_id) REFERENCES words(id),
    FOREIGN KEY (related_word_id) REFERENCES words(id)
);
```

### Future Work

- [ ] **Phonetics:** Searching and indexing by 'sounds-like'
- [ ] **Precomputed Indexes:** IPA, lemmas, morphological tags for fast search
- [ ] **Cross-lexicon Queries:** Enable etymology research ("find Latin words with Greek cognates")
- [ ] **Cognate Schema:** Implement the `cognates` table to link `Sanskrit.agni` <-> `Latin.ignis`
- [ ] **Automated Etymology Links:** Scrape the "Etymology" section of entries to find mentions of other target languages

---

## Phase 8: Performance & Advanced Features (P3 - Future)

### 8.1 CLTK Enhancements

**Latin CLTK:**
- [ ] Integrate Latin stemmer/lemmatizer for faster lookups
- [ ] Add prosody data support (syllable quantities)
- [ ] Improve Old Latin variant handling
- [ ] Cross-reference Lewis with other Latin lexica

**Greek CLTK:**
- [ ] Evaluate Ancient Greek morphological models beyond spaCy
- [ ] Add Greek prosody and meter information
- [ ] Support for Homeric Greek specific forms

**Sanskrit CLTK:**
- [ ] Add Sanskrit morphological analyzer integration (if available in CLTK)
- [ ] Support for Vedic Sanskrit variants
- [ ] Enhance IAST transliteration handling

### 8.2 Performance Optimization

- [ ] **Async Multi-Search:** Query Lewis, Diogenes, and CDSL in parallel
- [ ] **Sharded Database Build:** Implement divide-and-conquer indexing with parallel workers
- [ ] **Bulk Loading:** Use DuckDB COPY for faster imports
- [ ] **Transaction Batching:** Split bulk inserts into smaller commits

### 8.3 Observability

- [ ] **Distributed Tracing:** Add correlation IDs for request tracing
- [ ] **Query Profiling:** Track latency breakdown by backend

### 8.4 Export Features

- [ ] **Export to Flashcards:** A single command to export a looked-up word + its primary definition + one citation to an Anki-readable CSV

### 8.5 Sanskrit Heritage Platform Integration

When Sanskrit Heritage Platform is activated:

- Defer sandhi splitting to their specialized tool
- Integrate their API as additional backend
- Keep CDSL as primary dictionary, use SHP for morphological/sandhi services

---

## Implementation Priority Matrix

| Phase | Task | Effort | Pedagogical Impact | Priority | Prerequisite |
|-------|------|--------|-------------------|----------|--------------|
| **2.1** | Foster mapping (all languages) | Low | **Huge** | P0 | — |
| **2.2** | Apply Foster view (always on) | Low | **Huge** | P0 | 2.1 |
| **2.3** | CLI/API formatting | Medium | **Huge** | P0 | 2.2 |
| **1.1** | CLTK Sanskrit morphology | Medium | **Critical** | P0 | — |
| **1.2** | Sanskrit lemmatization fallback | Low | **Critical** | P0 | 1.1 |
| **1.3** | Sanskrit root display | Low | High | P1 | — |
| **3.1** | Fuzzy searching | Low | High | P1 | — |
| **3.2** | Backoff lemmatization chain | Low | High | P1 | 1.1, 1.2 |
| **4.1** | Citation extraction & formatting | Medium | **Huge** | P1 | — |
| **4.2** | Snippet previews | Medium | High | P1 | 4.1 |
| **4.3** | Morphology at top | Low | High | P1 | — |
| **5.1** | CDSL `<ls>` tag display | Low | High | P2 | — |
| **6.1** | Lewis Latin Parser | Medium | Medium | P2 | — |
| **6.2** | CDSL Entry Enhancements | Medium | Medium | P2 | — |
| **6.3** | Diogenes Parser Improvements | Medium | Medium | P2 | — |
| **7** | Local Data Storage Layer | High | Medium | P3 | — |
| **8** | Performance & Advanced Features | High | Low | P3 | — |

---

## File Structure

```
src/langnet/
├── foster/
│   ├── __init__.py
│   ├── latin.py          # Foster Latin mappings
│   ├── greek.py          # Foster Greek mappings
│   ├── sanskrit.py       # Foster Sanskrit mappings
│   └── apply.py          # Function to apply Foster view to results
├── fuzzy/
│   └── core.py           # Levenshtein distance & fuzzy matching
├── classics_toolkit/
│   └── core.py           # Add sanskrit_morphology_query()
├── engine/
│   └── core.py           # Lemmatization chain, Foster integration
├── cologne/
│   └── core.py           # Sanskrit entry formatter for <ls> tags
├── diogenes/
│   ├── parser.py         # Improved parsing
│   └── citation_formatter.py  # Enhanced citation display
└── cli.py                # Update display format
```

---

## Example Output Comparison

### Before (Technical Only)

```
Latin: sumpturi
Morphology: fut, part, act, masc, nom, voc, pl

Greek: λόγος
Morphology: masc, nom, sg

Sanskrit: योगेन
[No morphology available]
```

### After (Foster-Enabled + Complete Morphology)

```
Latin: sumpturi
ROOT/STEMS: sum-, su- (future participle of "sum" + "is")
DEFINITION: about to go, about to be
Morphology:
  - fut (Time-Later Function)
  - part (Participle Function)
  - act (Doing Function)
  - masc (Male Function)
  - nom (Naming Function)
  - pl (Group Function)

Greek: λόγος
STEMS: λεγ- (to speak, collect)
DEFINITION: word, speech, reason, account
Morphology:
  - masc (Male Function)
  - nom (Naming Function)
  - sg (Single Function)

Citations:
  - Plato (Pl. Phaedrus 229c): "ὁ λόγος σοι δίδοται"

Sanskrit: योगेन
ROOT: √yuj (to join, unite)
DEFINITION: yoga, union, connection
PART OF SPEECH: m.
Morphology:
  - Case 3 (By-With Function)
  - Instrumental case
  - Singular

SEE ALSO: L., TS., Vop.
```

---

## Testing Plan

### Phase 1 Tests (Sanskrit Foundation) ✅

- [x] Test CLTK Sanskrit morphology query with various words
- [x] Test lemmatization fallback for inflected Sanskrit forms
- [x] Test root display in Sanskrit output
- [x] Test integration with existing CDSL lookup

### Phase 2 Tests (Foster Grammar)

- [ ] Test Foster mapping for all Latin cases/tenses/numbers
- [ ] Test Foster mapping for all Greek cases/tenses/numbers/moods
- [ ] Test Foster mapping for Sanskrit cases/genders/numbers
- [ ] Test Foster view application to full query results
- [ ] Verify both technical and Foster terms displayed consistently
- [ ] Test with API: `curl -s -X POST "http://localhost:8000/api/q" -d "l=lat&s=sumpturi" | jq .diogenes.chunks[0].morphology`

### Phase 3 Tests (Lemmatization)

- [ ] Test fuzzy matching with typos
- [ ] Test lemmatization fallback for flexed forms
- [ ] Test backoff chain priority order

### Phase 4 Tests (Citation Display)

- [ ] Test citation formatter with Diogenes results
- [ ] Verify author/work extraction from ref IDs
- [ ] Test snippet preview generation

### Phase 5 Tests (CDSL References)

- [ ] Test CDSL `<ls>` tag display with entries that have references
- [ ] Verify lexicon references shown prominently

### Phase 6 Tests (Dictionary Parsers)

- [ ] Test Lewis entry parsing with various entry formats
- [ ] Test CDSL Sanskrit parser with variant readings
- [ ] Test Diogenes parser with cross-references

---

## Next Steps

1. ✅ **Synthesize roadmaps** (this document)
2. ✅ **Phase 1 Complete:** Sanskrit foundation - CLTK integration, lemmatization fallback, root display
3. Start implementation with Phase 2 (Foster mappings) — low effort, maximum pedagogical impact
4. Integrate Phases 3-4 (lemmatization + citations) — complete the pedagogical circle
5. Add unit tests as each phase is completed
6. Run existing test suite to ensure no regressions: `just test`
7. Verify with API queries:
   ```bash
   langnet-cli cache-clear && curl -s -X POST "http://localhost:8000/api/q" -d "l=san&s=योगेन"
   ```

---

## Questions Resolved

✅ **Foster Grammar Scope:** All three languages (Latin, Greek, Sanskrit)

✅ **Display Format:** Technical term + Foster function (e.g., "Nominative (Naming Function)")

✅ **Sanskrit Case Numbers:** Display both number and Foster function (e.g., "Case 3: By-With Function")

✅ **Root Display Priority:** Root appears at top of Sanskrit results

✅ **CDSL References:** Display `<ls>` tags (lexicon references) in Sanskrit output

✅ **Diogenes Citations:** Existing data is rich enough — just display better

✅ **Sandhi Splitting:** Defer to Sanskrit Heritage Platform (future integration)

✅ **Lemmatization Priority:** Direct lookup → Fuzzy → Lemmatization chain

✅ **Pedagogical Philosophy:** Foster method — always show what words *do*, not just what they are

---

**End of Pedagogical Roadmap**
