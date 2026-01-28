# Phase 2 Implementation Plan: Foster Functional Grammar

## Overview

Transform langnet-cli into a pedagogical engine by translating technical grammar into learner-friendly language for **all three languages** (Latin, Greek, Sanskrit). Foster terms are displayed **by default** alongside technical terms.

## Architecture Decision

**Separate logic from rendering**: Foster mappings use enum values/codes (canonical), while display strings are handled separately in a lexicon/abbreviation module. This makes display a rendering concern, allowing flexibility to change display strings without touching core logic.

---

## Task Checklist

### 2.1 Foster Mapping Module

#### New Directory Structure
- [ ] Create `src/langnet/foster/` directory
- [ ] Create `src/langnet/foster/__init__.py`
- [ ] Create `src/langnet/foster/latin.py`
- [ ] Create `src/langnet/foster/greek.py`
- [ ] Create `src/langnet/foster/sanskrit.py`
- [ ] Create `src/langnet/foster/lexicon.py` (display string mappings)

#### Foster Enum Definitions
- [ ] Define `FosterCase` enum (NAMING, CALLING, RECEIVING, POSSESSING, TO_FOR, BY_WITH_FROM_IN, IN_WHERE, OH)
- [ ] Define `FosterTense` enum (TIME_NOW, TIME_LATER, TIME_PAST, TIME_WAS_DOING, TIME_HAD_DONE, ONCE_DONE)
- [ ] Define `FosterGender` enum (MALE, FEMALE, NEUTER)
- [ ] Define `FosterNumber` enum (SINGLE, GROUP, PAIR)
- [ ] Define `FosterMisc` enum (PARTICIPLE, DOING, BEING_DONE_TO, STATEMENT, WISH_MAY_BE, MAYBE_WILL_DO, COMMAND, FOR_SELF)

#### Lexicon/Display Mappings (`src/langnet/foster/lexicon.py`)
- [ ] Create `FOSTER_CASE_DISPLAY` dict: maps FosterCase enum to display strings (e.g., `FosterCase.NAMING: "Naming Function"`)
- [ ] Create `FOSTER_TENSE_DISPLAY` dict: maps FosterTense enum to display strings
- [ ] Create `FOSTER_GENDER_DISPLAY` dict: maps FosterGender enum to display strings
- [ ] Create `FOSTER_NUMBER_DISPLAY` dict: maps FosterNumber enum to display strings
- [ ] Create `FOSTER_MISC_DISPLAY` dict: maps FosterMisc enum to display strings
- [ ] Create `FOSTER_ABBREVIATIONS` dict: maps enum values to short codes (e.g., `FosterCase.NAMING: "NAM"`)

#### Latin Mappings (`src/langnet/foster/latin.py`)
- [ ] Define `FOSTER_LATIN_CASES` dict: maps Latin technical tags to FosterCase enum values (e.g., `"nom": FosterCase.NAMING`)
- [ ] Define `FOSTER_LATIN_TENSES` dict: maps Latin technical tags to FosterTense enum values
- [ ] Define `FOSTER_LATIN_GENDERS` dict: maps Latin technical tags to FosterGender enum values
- [ ] Define `FOSTER_LATIN_NUMBERS` dict: maps Latin technical tags to FosterNumber enum values
- [ ] Define `FOSTER_LATIN_MISCELLANEOUS` dict: maps Latin technical tags to FosterMisc enum values

#### Greek Mappings (`src/langnet/foster/greek.py`)
- [ ] Define `FOSTER_GREEK_CASES` dict: maps Greek technical tags to FosterCase enum values
- [ ] Define `FOSTER_GREEK_TENSES` dict: maps Greek technical tags to FosterTense enum values
- [ ] Define `FOSTER_GREEK_GENDERS` dict: maps Greek technical tags to FosterGender enum values
- [ ] Define `FOSTER_GREEK_NUMBERS` dict: maps Greek technical tags to FosterNumber enum values
- [ ] Define `FOSTER_GREEK_MISCELLANEOUS` dict: maps Greek technical tags to FosterMisc enum values

#### Sanskrit Mappings (`src/langnet/foster/sanskrit.py`)
- [ ] Define `FOSTER_SANSKRIT_CASES` dict: maps Sanskrit case numbers to FosterCase enum values (e.g., `"1": FosterCase.NAMING`)
- [ ] Define `FOSTER_SANSKRIT_GENDERS` dict: maps Sanskrit gender codes to FosterGender enum values
- [ ] Define `FOSTER_SANSKRIT_NUMBERS` dict: maps Sanskrit number codes to FosterNumber enum values

#### Package Initialization (`src/langnet/foster/__init__.py`)
- [ ] Export all mapping dicts from latin, greek, sanskrit modules
- [ ] Export Foster enums
- [ ] Export display/abbreviation lexicon

---

### 2.2 Apply Foster View Function

#### Create `src/langnet/foster/apply.py`
- [ ] Import mapping dicts and enums from latin, greek, sanskrit modules
- [ ] Define `apply_foster_view(result: dict) -> dict` function

#### Diogenes Morphology Processing
- [ ] Check for `"diogenes"` key in result
- [ ] Iterate through `result["diogenes"]["chunks"]`
- [ ] Check for `"morphology"` key in chunks
- [ ] Iterate through `morphology["morphs"]`
- [ ] For each morph, iterate through `morph["tags"]`
- [ ] Map tags to Foster enum values (try Latin first, then Greek if not found)
- [ ] Create `foster_tags` list of Foster enum values (not display strings)
- [ ] Store in `morph["foster_codes"]` field (enum values, can be serialized)

#### CLTK Greek Morphology Processing
- [ ] Check for `"cltk"` key and `"greek_morphology"` subkey
- [ ] Extract `morphological_features` dict
- [ ] Map case using `FOSTER_GREEK_CASES` to FosterCase enum
- [ ] Map tense using `FOSTER_GREEK_TENSES` to FosterTense enum
- [ ] Map gender using `FOSTER_GREEK_GENDERS` to FosterGender enum
- [ ] Map number using `FOSTER_GREEK_NUMBERS` to FosterNumber enum
- [ ] Map miscellaneous features (act, mid, pass, ind, subj, opt, imper) to FosterMisc enum
- [ ] Store in `result["cltk"]["greek_morphology"]["foster_codes"]` as dict of enum values

#### CDSL Sanskrit Processing
- [ ] Check for `"cologne"` key
- [ ] Iterate through dictionaries and entries
- [ ] Check for `"grammar_tags"` in entries
- [ ] Store original grammar_tags
- [ ] Create `foster_codes` dict with mapped Foster enum values
- [ ] Add `foster_codes` to entry

#### Return Statement
- [ ] Return modified result with Foster enum codes applied (not display strings)

---

### 2.3 Engine Integration

#### Modify `src/langnet/engine/core.py`
- [ ] Import `apply_foster_view` from `langnet.foster.apply`
- [ ] Call `apply_foster_view(result)` at end of `handle_query()` method
- [ ] Ensure Foster view is applied **after all backend lookups complete**
- [ ] Ensure Foster view is applied **before returning result**

---

### 2.4 CLI Display Format

#### Rendering Helper Function
- [ ] Create `render_foster_term(foster_enum, display_style="full")` function
- [ ] If `display_style == "full"`: return display string from lexicon (e.g., "Naming Function")
- [ ] If `display_style == "short"`: return abbreviation from lexicon (e.g., "NAM")
- [ ] Handle None/unmapped values gracefully

#### Modify `src/langnet/cli.py`
- [ ] Import rendering helper and display lexicon from `langnet.foster.lexicon`
- [ ] Update CLI formatter to display technical term + Foster function together
- [ ] For Diogenes morphology: iterate `foster_codes`, render each with display lexicon
- [ ] For CLTK morphology: render `foster_codes` dict with display lexicon
- [ ] For Sanskrit CDSL entries: render `foster_codes` dict with display lexicon

#### Example Output Format
- [ ] Latin morphology display: "Nominal: Nominative (Naming Function), Masculine (Male Function), Singular (Single Function)"
- [ ] Greek morphology display: "Nominal: Nominative (Naming Function), Masculine (Male Function), Singular (Single Function)"
- [ ] Sanskrit morphology display: "Case 3 (By-With Function), Instrumental case"

#### API Serialization
- [ ] Update `LanguageEngine.handle_query()` or add serialization step to convert enum values to string codes for JSON
- [ ] API response includes `foster_codes` as string codes (enum names or abbreviation codes)
- [ ] Optionally include both `foster_codes` (canonical) and `foster_display` (rendered) for flexibility

---

## Testing Checklist

### Unit Tests
- [ ] Create `tests/test_foster_enums.py`
- [ ] Test FosterCase enum has all expected values
- [ ] Test FosterTense enum has all expected values
- [ ] Test FosterGender enum has all expected values
- [ ] Test FosterNumber enum has all expected values
- [ ] Test FosterMisc enum has all expected values

- [ ] Create `tests/test_foster_lexicon.py`
- [ ] Test all display strings are defined for each enum value
- [ ] Test all abbreviations are defined for each enum value
- [ ] Test display lexicon is complete (no missing mappings)

- [ ] Create `tests/test_foster_mappings.py`
- [ ] Test all Latin case mappings return correct FosterCase enum
- [ ] Test all Latin tense mappings return correct FosterTense enum
- [ ] Test all Latin gender mappings return correct FosterGender enum
- [ ] Test all Latin number mappings return correct FosterNumber enum
- [ ] Test all Latin miscellaneous mappings return correct FosterMisc enum
- [ ] Test all Greek case mappings return correct FosterCase enum
- [ ] Test all Greek tense mappings return correct FosterTense enum
- [ ] Test all Greek gender mappings return correct FosterGender enum
- [ ] Test all Greek number mappings return correct FosterNumber enum
- [ ] Test all Greek miscellaneous mappings return correct FosterMisc enum
- [ ] Test all Sanskrit case mappings return correct FosterCase enum
- [ ] Test all Sanskrit gender mappings return correct FosterGender enum
- [ ] Test all Sanskrit number mappings return correct FosterNumber enum

### Integration Tests
- [ ] Create `tests/test_foster_apply.py`
- [ ] Test Foster view application to Diogenes Latin results (stores enum codes)
- [ ] Test Foster view application to Diogenes Greek results (stores enum codes)
- [ ] Test Foster view application to CLTK Greek results (stores enum codes)
- [ ] Test Foster view application to CDSL Sanskrit results (stores enum codes)
- [ ] Test unmapped tags remain unchanged (no Foster code added)
- [ ] Test fallback from Latin to Greek mappings where applicable

### Rendering Tests
- [ ] Create `tests/test_foster_rendering.py`
- [ ] Test `render_foster_term()` with full display style
- [ ] Test `render_foster_term()` with short display style
- [ ] Test rendering handles None/unmapped values gracefully
- [ ] Test rendering produces expected output strings for all enum values

### Engine Integration Tests
- [ ] Test `LanguageEngine.handle_query()` applies Foster view to Latin queries
- [ ] Test `LanguageEngine.handle_query()` applies Foster view to Greek queries
- [ ] Test `LanguageEngine.handle_query()` applies Foster view to Sanskrit queries
- [ ] Verify Foster view doesn't break existing functionality
- [ ] Verify enum codes are properly serialized for JSON response

### CLI Display Tests
- [ ] Test CLI output shows technical term + Foster display string for Latin
- [ ] Test CLI output shows technical term + Foster display string for Greek
- [ ] Test CLI output shows technical term + Foster display string for Sanskrit
- [ ] Verify both technical and Foster display terms are displayed together
- [ ] Test short display mode if implemented

### API Tests
- [ ] Test API response includes `foster_codes` field for Diogenes morphology
- [ ] Test API response includes `foster_codes` field for CLTK morphology
- [ ] Test API response includes `foster_codes` field for Sanskrit entries
- [ ] Verify JSON structure matches expected format (enum codes as strings)
- [ ] Test with example: `curl -s -X POST "http://localhost:8000/api/q" -d "l=lat&s=sumpturi" | jq .diogenes.chunks[0].morphology`

---

## Verification Checklist

### Code Quality
- [ ] Run `just ruff-format` on all new files
- [ ] Run `just ruff-check` - no errors
- [ ] Run `just typecheck` - no type errors
- [ ] Run `just test` - all tests pass

### Manual Testing
- [ ] Restart langnet server after code changes
- [ ] Run `langnet-cli cache-clear`
- [ ] Test Latin query with morphology: `curl -s -X POST "http://localhost:8000/api/q" -d "l=lat&s=sumpturi"`
- [ ] Verify API response includes `foster_codes` as string codes (e.g., `"foster_codes": ["TIME_LATER", "PARTICIPLE", "DOING"]`)
- [ ] Test Greek query with morphology: `curl -s -X POST "http://localhost:8000/api/q" -d "l=grc&s=λόγος"`
- [ ] Test Sanskrit query: `curl -s -X POST "http://localhost:8000/api/q" -d "l=san&s=योगेन"`
- [ ] Verify CLI output displays Foster display strings (e.g., "Future (Time-Later Function)")
- [ ] Verify API response JSON is valid and enum codes serialize correctly

### Documentation
- [ ] Update DEVELOPER.md if needed
- [ ] Update AGENTS.md if needed
- [ ] Consider adding Foster grammar explanation to README.md

---

## Dependencies

No new external dependencies required. All mappings use standard Python dicts and strings.

---

## Estimated Effort

| Component | Estimated Time | Complexity |
|-----------|----------------|------------|
| Foster Enum Definitions | 30 min | Low |
| Foster Lexicon (display/abbreviations) | 1 hour | Low |
| Foster Mapping Module (technical → enum) | 1-2 hours | Low |
| Apply Foster View Function (enum codes) | 2-3 hours | Medium |
| Engine Integration (enum codes) | 30 min | Low |
| Rendering Helper Functions | 1 hour | Low |
| CLI Display Format (enum → string) | 1-2 hours | Low |
| API Serialization (enum → JSON) | 30 min | Low |
| Testing (enums, mappings, rendering) | 3-4 hours | Medium |
| Verification | 1 hour | Low |
| **Total** | **11-15 hours** | **Low-Medium** |

---

## Success Criteria

Phase 2 is complete when:

1. ✅ All Foster enums are defined (Case, Tense, Gender, Number, Misc)
2. ✅ Foster mappings are defined for Latin, Greek, and Sanskrit (technical tags → enum values)
3. ✅ Foster lexicon/display mappings are defined (enum values → display strings and abbreviations)
4. ✅ Foster view is automatically applied to all query results (stores enum codes)
5. ✅ CLI renderer converts enum codes to display strings (separation of concerns)
6. ✅ API serializes enum codes to JSON strings
7. ✅ Both technical terms and Foster display strings are shown together in CLI
8. ✅ All unit tests pass (enums, lexicon, mappings)
9. ✅ All integration tests pass (apply, rendering, engine)
10. ✅ CLI output shows "tag (Foster Function)" format
11. ✅ API responses include Foster metadata in expected JSON structure
12. ✅ Code passes all linting/typechecking
13. ✅ Manual testing confirms functionality works end-to-end

---

## File Structure

```
src/langnet/
├── foster/
│   ├── __init__.py       # Export enums, mappings, lexicon
│   ├── enums.py          # FosterCase, FosterTense, FosterGender, FosterNumber, FosterMisc
│   ├── lexicon.py        # Display strings and abbreviations for enums
│   ├── latin.py          # Latin technical tag → enum mappings
│   ├── greek.py          # Greek technical tag → enum mappings
│   ├── sanskrit.py       # Sanskrit technical tag → enum mappings
│   ├── apply.py          # Apply Foster view to results (stores enum codes)
│   └── render.py         # Rendering helpers (enum → display string)
├── fuzzy/
│   └── core.py           # Levenshtein distance & fuzzy matching
├── classics_toolkit/
│   └── core.py           # Add sanskrit_morphology_query()
├── engine/
│   └── core.py           # Lemmatization chain, Foster integration (enum codes)
├── cologne/
│   └── core.py           # Sanskrit entry formatter for <ls> tags
├── diogenes/
│   ├── parser.py         # Improved parsing
│   └── citation_formatter.py  # Enhanced citation display
└── cli.py                # Update display format (use render helpers)

tests/
├── test_foster_enums.py      # Test enum definitions
├── test_foster_lexicon.py    # Test display/abbreviation mappings
├── test_foster_mappings.py    # Test technical → enum mappings
├── test_foster_apply.py      # Test Foster view application
└── test_foster_rendering.py  # Test enum → display string conversion
```