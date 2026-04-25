# Compound Term Lookup Implementation Plan
## Focus: Sanskrit compounds like "dharma-kṣhetre" and "kuru-kṣhetre"

**Feature Area**: Pedagogy  
**Status**: 🚧 ACTIVE  
**Priority**: High  
**Estimated Effort**: 3-4 weeks  
**AI Personas**: @architect @coder @artisan  
**Target**: Bhagavad Gītā 1.1 passage analysis

## 1. Current State Assessment

### ✅ What Works
1. **Sanskrit normalization** (`src/langnet/normalizer/sanskrit.py`)
   - Encoding detection (IAST, Devanagari, Velthuis, SLP1)
   - Heritage Platform query building
   - Basic ASCII variant handling

2. **Heritage Platform integration** (`src/langnet/execution/handlers/heritage.py`)
   - Morphology analysis via sktreader
   - Compound detection with `_group_compounds()`
   - Color coding for compound roles (yellow=stem, cyan=final)
   - Analysis code parsing with compound markers (`iic.`, `ifc.`)

3. **CDSL dictionary access** (via `codesketch/src/langnet/heritage/morphology.py`)
   - Monier-Williams lookup
   - Structured sense extraction (incomplete)

### ❌ What's Missing for Compound Analysis
1. **No compound splitting** - hyphenated terms not broken into components
2. **No component lookup** - individual parts not looked up in dictionary
3. **No compound type identification** - tatpuruṣa, bahuvrīhi, etc.
4. **No educational explanations** - students get raw analysis without context
5. **No sandhi-aware processing** - joined compounds can't be split

## 2. Implementation Phases

### Phase 1: Compound Splitting & Query Enhancement (Week 1)
**Goal**: Make hyphenated compounds work with existing Heritage pipeline

#### 1.1 Update Sanskrit Normalizer
- Add `_split_compound()` method to handle hyphenated terms
- Remove hyphens for Heritage queries (send "dharmakshetre" not "dharma-kshetre")
- Return both joined form (for Heritage) and components (for analysis)

#### 1.2 Enhance Heritage Handler
- Modify `extract_html()` to recognize compound terms
- Preserve component information in payload
- Add component tracking to `_group_compounds()`

**Files**: `src/langnet/normalizer/sanskrit.py`, `src/langnet/execution/handlers/heritage.py`

### Phase 2: Component Analysis & Dictionary Integration (Week 2)
**Goal**: Look up each component in dictionary and provide meanings

#### 2.1 Create Compound Analyzer Service
- New module: `src/langnet/compounds/analyzer.py`
- Takes compound term, splits, analyzes components
- Uses existing Heritage/CDSL services for lookups
- Aggregates results into structured output

#### 2.2 Wire Dictionary Lookup
- Extract components from Heritage analysis
- Query CDSL for each component lemma
- Select appropriate sense based on context
- Store in analysis payload

**Files**: New `src/langnet/compounds/` module, updates to heritage handler

### Phase 3: Educational Context & Explanation (Week 3)
**Goal**: Generate student-friendly explanations of compound structure

#### 3.1 Compound Type Detection
- Classify compounds: tatpuruṣa, bahuvrīhi, dvandva, etc.
- Use morphological features and dictionary data
- Add to analysis output

#### 3.2 Explanation Generator
- Template-based explanations for each compound type
- Include literal meaning, grammatical structure
- Provide translation suggestions

**Files**: `src/langnet/compounds/types.py`, `src/langnet/compounds/explanations.py`

### Phase 4: CLI Integration & Testing (Week 4)
**Goal**: Make compound analysis accessible via CLI

#### 4.1 New CLI Command
```bash
langnet-cli analyze-compound "dharma-kṣhetre" --output json
langnet-cli analyze-compound "kuru-kṣhetre" --output text
```

#### 4.2 Test Suite
- Gītā 1.1 compounds: dharma-kṣhetre, kuru-kṣhetre
- Various compound types
- Edge cases: sandhi, multi-part compounds

**Files**: `src/langnet/cli.py`, `tests/test_compound_analysis.py`

## 3. Technical Specifications

### 3.1 Data Structures

```python
@dataclass
class CompoundAnalysis:
    surface_form: str
    normalized_form: str
    components: list[ComponentAnalysis]
    compound_type: CompoundType
    explanation: str
    translation: str
    
@dataclass  
class ComponentAnalysis:
    surface: str
    lemma: str
    morphology: dict
    dictionary_senses: list[dict]
    selected_meaning: str
    compound_role: str  # initial, medial, final
```

### 3.2 Compound Type Classification

1. **Tatpuruṣa (Determinative)**: "field of duty" (karmadhāraya, dvitīyā, etc.)
2. **Bahuvrīhi (Possessive)**: "one who has a red arm" (exocentric)
3. **Dvandva (Coordinative)**: "mother and father" (copulative)
4. **Avyayībhāva (Adverbial)**: "in the house" (adverbial)

### 3.3 Heritage Color Mapping for Compounds
- **Yellow**: Initial/medial compound member (pūrvapada)
- **Cyan**: Final compound member (uttarapada)
- **Analysis codes**: `iic.` (initial), `ifc.` (final)

## 4. Example Output

### For "dharma-kṣhetre":
```
COMPOUND ANALYSIS: dharma-kṣhetre
──────────────────────────────────
Type: Tatpuruṣa (Determinative)
Components: dharma + kṣhetre

1. dharma (noun, locative singular neuter)
   • Meanings: duty, law, righteousness, justice
   • Selected: duty (context: religious/ethical field)
   • Role: Initial member (specifier)

2. kṣhetre (noun, locative singular neuter)  
   • Lemma: kṣetra
   • Meanings: field, land, place, region
   • Selected: field
   • Role: Final member (head)

Explanation: A tatpuruṣa compound where "dharma" specifies the type of "kṣetra".
Literal meaning: "field of duty"
Contextual translation: "in the field of religious duty"
```

### JSON Output:
```json
{
  "compound": "dharma-kṣhetre",
  "normalized": "dharmakṣetre",
  "type": "tatpuruṣa",
  "components": [
    {
      "surface": "dharma",
      "lemma": "dharma", 
      "meanings": ["duty", "law", "righteousness"],
      "selected": "duty",
      "role": "initial"
    },
    {
      "surface": "kṣhetre", 
      "lemma": "kṣetra",
      "meanings": ["field", "land", "place"],
      "selected": "field", 
      "role": "final"
    }
  ],
  "explanation": "Tatpuruṣa compound: 'field of duty'",
  "translation": "in the field of duty"
}
```

## 5. Dependencies & Integration Points

### 5.1 Existing Services to Use
1. **SanskritNormalizer** - encoding, Heritage query prep
2. **HeritageHandler** - morphology analysis, compound detection
3. **CDSL Dictionary** (via `SanskritCologneLexicon`) - component meanings
4. **Foster Grammar** - sense selection based on grammatical features

### 5.2 New Services to Create
1. **CompoundAnalyzer** - orchestrates analysis pipeline
2. **CompoundTypeClassifier** - identifies compound type
3. **ExplanationGenerator** - creates educational output

## 6. Success Criteria

### Technical
- [ ] Hyphenated compounds split correctly
- [ ] Components looked up in dictionary
- [ ] Compound type identified (80% accuracy)
- [ ] Clear explanations generated
- [ ] CLI command functional

### Educational
- [ ] Students understand compound structure
- [ ] Appropriate meanings selected for context
- [ ] Explanation helps with passage comprehension
- [ ] Output usable for Gītā study

## 7. Risks & Mitigations

### 7.1 Heritage Platform Limitations
- **Risk**: Heritage may not analyze all compounds
- **Mitigation**: Fallback to heuristic analysis, use CDSL data

### 7.2 Dictionary Sense Selection
- **Risk**: Wrong meaning selected for context
- **Mitigation**: Use Foster grammar codes, prioritize common senses

### 7.3 Performance
- **Risk**: Multiple API calls slow down analysis
- **Mitigation**: Implement caching, parallel requests where possible

## 8. Next Steps

### Immediate (Week 1)
1. [ ] Add compound splitting to SanskritNormalizer
2. [ ] Test with "dharma-kṣhetre" and "kuru-kṣhetre"
3. [ ] Verify Heritage can analyze joined forms

### Short-term (Week 2)
1. [ ] Create CompoundAnalyzer service
2. [ ] Wire component dictionary lookup
3. [ ] Test end-to-end with Gītā examples

### Medium-term (Week 3-4)
1. [ ] Add compound type classification
2. [ ] Create explanation generator
3. [ ] Add CLI command
4. [ ] Write comprehensive tests

## 9. References

1. **Existing Code**: 
   - `src/langnet/normalizer/sanskrit.py`
   - `src/langnet/execution/handlers/heritage.py`
   - `codesketch/src/langnet/heritage/morphology.py`

2. **Documentation**:
   - `docs/plans/todo/pedagogy/contextual-word-meaning-lookup.md`
   - `docs/technical/design/tool-fact-architecture.md`
   - `docs/handoff/semantic-triples-impl.md`

3. **Sanskrit Resources**:
   - Heritage Platform: https://sanskrit.inria.fr/
   - Compound types in Sanskrit grammar
   - Gītā 1.1 passage for testing