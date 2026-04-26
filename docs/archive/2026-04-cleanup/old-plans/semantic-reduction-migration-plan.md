# Semantic Reduction Migration Plan

**Date**: 2026-02-15  
**Status**: 📋 PLANNING (Not Started)  
**Priority**: HIGH  
**Area**: infra/semantic-reduction  
**Related**: `semantic-reduction-roadmap.md`, `semantic-reduction-gap-analysis.md`

## Overview

This document outlines the step-by-step migration from current architecture to full semantic reduction pipeline. Based on gap analysis, we need schema evolution before pipeline implementation.

## Current State Snapshot

### **Current Architecture (Pre-Migration)**
- Schema: `DictionaryDefinition` lacks source references
- Adapters: Inconsistent data structures
- API: Legacy format only
- Semantic structs: Schema defined but not populated with reduced data

### **Target State (Post-Migration)**
- Schema: Enhanced with source_ref, domains, register
- Adapters: Consistent WSU-compatible output
- API: Semantic format with actual reduction
- Pipeline: Full 4-stage semantic reduction operational

## Migration Phases

### **Phase 0: Foundation & Schema Enhancement** ⏳
**Duration**: 1-2 weeks  
**Goal**: Non-breaking schema changes to enable future work

#### **Tasks**
1. **Update `DictionaryDefinition` schema** (Non-breaking)
   ```python
   # Add to src/langnet/schema.py
   source_ref: str | None = None  # "mw:217497"
   domains: list[str] = field(default_factory=list)
   register: list[str] = field(default_factory=list)
   confidence: float | None = None
   ```

2. **Update CDSL adapter** (First adapter)
   - Parse `sense_lines` into proper `DictionaryDefinition` objects
   - Populate `source_ref` from MW/AP90 IDs
   - Test with Sanskrit words (agni, śiva)

3. **Create test infrastructure**
   - Tests for new schema fields
   - Validation of source_ref population
   - Backward compatibility tests

#### **Success Criteria**
- [ ] Schema updated with new fields
- [ ] CDSL adapter populates source_ref
- [ ] Sanskrit tests pass with MW IDs
- [ ] No breaking changes to existing API

#### **Rollback Plan**
- Remove new fields from schema
- Revert CDSL adapter changes
- All tests should still pass

---

### **Phase 1: WSU Extraction Foundation** ⏳
**Duration**: 1-2 weeks  
**Goal**: Extract WSUs from enhanced schema

#### **Tasks**
1. **Create `WSUExtractor` module**
   ```python
   # src/langnet/semantic_reducer/wsu_extractor.py
   def extract_wsu_from_entry(entry: DictionaryEntry) -> List[WitnessSenseUnit]
   ```

2. **Handle mixed data**
   - Extract from enhanced entries (with source_ref)
   - Fallback extraction for legacy entries
   - Quality metrics for extraction

3. **Create normalization layer**
   - Gloss tokenization
   - Unicode normalization
   - Abbreviation expansion

#### **Success Criteria**
- [ ] WSUs extracted for CDSL entries
- [ ] Fallback working for legacy entries
- [ ] Normalization deterministic
- [ ] Performance < 50ms per entry

#### **Testing Strategy**
- Unit tests for extraction
- Integration tests with real data
- Performance benchmarks

---

### **Phase 2: Similarity Engine** ⏳
**Duration**: 2 weeks  
**Goal**: Compare and score WSU similarity

#### **Tasks**
1. **Implement token similarity**
   - Jaccard similarity for gloss tokens
   - Language-specific tokenization
   - Stop word handling

2. **Add metadata signals**
   - Domain matching
   - Register matching
   - Entity type detection

3. **Build similarity graph**
   - Pairwise similarity matrix
   - Mode-dependent weights
   - Performance optimization

#### **Success Criteria**
- [ ] Token similarity working
- [ ] Metadata signals integrated
- [ ] Mode weights configurable
- [ ] Performance < 100ms for 50 WSUs

#### **Validation**
- Human-labeled similarity pairs
- Precision/recall metrics
- Mode behavior validation

---

### **Phase 3: Clustering Core** ⏳
**Duration**: 2 weeks  
**Goal**: Cluster WSUs into semantic buckets

#### **Tasks**
1. **Implement greedy clustering**
   - Deterministic algorithm
   - Mode-dependent thresholds
   - Bucket confidence calculation

2. **Create bucket structure**
   - Deterministic sense_id generation
   - Witness preservation
   - Ranking by source importance

3. **Add mode switching**
   - OPEN vs SKEPTIC thresholds
   - UI hints for collapsed senses
   - API parameter support

#### **Success Criteria**
- [ ] Deterministic clustering
- [ ] Mode behavior correct
- [ ] No witness overlap between buckets
- [ ] Confidence scores calculated

#### **Testing**
- Golden snapshot tests
- Determinism tests
- Mode switching tests

---

### **Phase 4: Semantic Constants** ⏳
**Duration**: 2 weeks  
**Goal**: Assign stable semantic identifiers

#### **Tasks**
1. **Create constant registry**
   - JSON file storage
   - Constant matching logic
   - Provisional constant generation

2. **Implement assignment policy**
   - Match existing constants
   - Create provisional constants
   - Curation workflow

3. **Integrate with pipeline**
   - Constant assignment in reducer
   - Registry persistence
   - Version tracking

#### **Success Criteria**
- [ ] Registry storage working
- [ ] Match+introduce policy operational
- [ ] Deterministic constant IDs
- [ ] Integration with clustering

#### **Data Management**
- Registry backup strategy
- Constant merging logic
- Curation interface plan

---

### **Phase 5: Integration & Polish** ⏳
**Duration**: 1-2 weeks  
**Goal**: Full pipeline integration and polish

#### **Tasks**
1. **Integrate pipeline**
   ```python
   class SemanticReducer:
       def reduce_to_semantic_structs(entries, mode) -> QueryResponse
   ```

2. **Update semantic converter**
   - Use reducer instead of basic mapping
   - Preserve backward compatibility
   - Add performance optimizations

3. **Add evidence inspection**
   - CLI command for debugging
   - WSU visualization
   - Similarity matrix display

4. **Enhance adapters gradually**
   - Diogenes: source_ref from dictionary blocks
   - Whitakers: source_ref generation
   - Heritage: morphology source tracking

#### **Success Criteria**
- [ ] Full pipeline integrated
- [ ] Semantic format uses reduction
- [ ] Evidence inspection working
- [ ] All adapters enhanced

#### **Final Validation**
- End-to-end tests
- Performance benchmarks
- User experience testing

## Migration Strategy

### **Incremental Enhancement**
1. **Non-breaking changes first**: Schema updates optional
2. **Progressive enhancement**: New features don't break old
3. **Fallback paths**: Handle missing data gracefully
4. **Feature flags**: Control rollout of new functionality

### **Data Flow During Migration**
```
Phase 0: Legacy → Enhanced Schema (CDSL only)
Phase 1: Enhanced → WSUs (mixed data)
Phase 2: WSUs → Similarity scores
Phase 3: Similarity → Buckets
Phase 4: Buckets → Constants
Phase 5: Full pipeline integration
```

### **Backward Compatibility**
- **API**: Legacy format always available
- **CLI**: `query` command unchanged
- **Data**: Old adapters continue working
- **Schema**: New fields optional

## Risk Management

### **Technical Risks**
| Risk | Mitigation | Fallback |
|------|------------|----------|
| Performance degradation | Profile early, add caching | Keep legacy format for speed |
| Non-deterministic clustering | Strict sorting rules, extensive tests | Document as feature |
| Constant registry bloat | Automatic merging, size limits | Manual curation |
| Adapter compatibility | Optional fields, gradual updates | Fallback extraction |

### **Timeline Risks**
- **Phase delays**: Buffer time between phases
- **Dependency issues**: Independent phase completion
- **Testing bottlenecks**: Parallel test development

### **Quality Risks**
- **Data loss**: Extensive validation tests
- **Incorrect reduction**: Human review of outputs
- **Regression bugs**: Comprehensive test suite

## Success Metrics

### **Phase Completion Criteria**
Each phase must have:
- [ ] All tasks completed
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Performance targets met
- [ ] Backward compatibility verified

### **Overall Success Criteria**
- [ ] Semantic format uses actual reduction
- [ ] Performance < 500ms for typical queries
- [ ] Deterministic outputs
- [ ] All languages supported
- [ ] Evidence inspection available
- [ ] Mode switching operational

## Stakeholder Communication

### **Development Team**
- Weekly progress updates
- Phase completion announcements
- Known issues documentation

### **Users**
- `semantic` command documented as "beta"
- Legacy `query` command unchanged
- Performance characteristics documented

### **Documentation**
- Update design docs as phases complete
- API documentation for new features
- Migration guide for adapter developers

## Post-Migration Tasks

### **Cleanup**
1. Remove fallback extraction code
2. Deprecate legacy data paths
3. Optimize performance bottlenecks

### **Optimization**
1. Cache similarity calculations
2. Precompute common queries
3. Parallelize pipeline stages

### **Enhancement**
1. Add more similarity signals
2. Improve entity detection
3. Add more languages

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 0** | 1-2 weeks | Enhanced schema, CDSL adapter |
| **Phase 1** | 1-2 weeks | WSU extraction, normalization |
| **Phase 2** | 2 weeks | Similarity engine, graph builder |
| **Phase 3** | 2 weeks | Clustering, mode switching |
| **Phase 4** | 2 weeks | Constant registry, assignment |
| **Phase 5** | 1-2 weeks | Full integration, evidence inspection |
| **Total** | 9-12 weeks | Complete semantic reduction |

## Starting Point

### **Immediate Next Actions**
1. **Update schema** (`src/langnet/schema.py`)
2. **Enhance CDSL adapter** 
3. **Create Phase 0 tests**
4. **Verify backward compatibility**

### **Resources Needed**
- Development: 1-2 developers
- Testing: Comprehensive test suite
- Review: Design document updates
- Documentation: User and developer guides

## Conclusion

This migration plan provides a structured path from current architecture to full semantic reduction. The key insight is that we need **schema evolution first**, implemented in non-breaking phases with careful attention to backward compatibility.

**Recommendation**: Begin Phase 0 immediately, as it enables all future work without breaking existing functionality.

---

*This migration plan should be reviewed at the start of each phase. Adjust based on lessons learned and technical discoveries.*