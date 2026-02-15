# Semantic Reduction Project - Complete Planning Summary

**Date**: 2026-02-15  
**Status**: 📋 PLANNING COMPLETE (Ready for Implementation)  
**Priority**: HIGH  
**Area**: infra/semantic-reduction

## Project Overview

**Goal**: Implement semantic reduction pipeline to convert raw lexical evidence into structured semantic output with stable concept identifiers, witness traceability, and epistemic mode support.

**Current Status**: ✅ Schema infrastructure complete, ❌ Reduction pipeline not started

## Key Documents Created

### **Planning Documents** (in `docs/plans/todo/`)
1. **[semantic-reduction-roadmap.md](todo/semantic-reduction-roadmap.md)** - Complete 5-phase implementation plan
2. **[semantic-reduction-adapter-requirements.md](todo/semantic-reduction-adapter-requirements.md)** - WSU extraction requirements per adapter
3. **[semantic-reduction-similarity-spec.md](todo/semantic-reduction-similarity-spec.md)** - Similarity scoring algorithm specification
4. **[semantic-reduction-gap-analysis.md](todo/semantic-reduction-gap-analysis.md)** - Architecture gap analysis and solutions
5. **[semantic-reduction-migration-plan.md](todo/semantic-reduction-migration-plan.md)** - Step-by-step migration strategy

### **Design Documents** (in `docs/technical/design/`)
1. **[01-semantic-structs.md](../technical/design/01-semantic-structs.md)** - Schema definition ✅
2. **[02-witness-contracts.md](../technical/design/02-witness-contracts.md)** - Source contracts ✅  
3. **[03-classifier-and-reducer.md](../technical/design/03-classifier-and-reducer.md)** - 4-stage pipeline design ✅

## Current Architecture Assessment

### **What We Have ✅**
- Semantic structs schema (proto v0.0.1)
- API format parameter (`?format=semantic`)
- CLI semantic command (`langnet semantic`)
- Basic converter (DictionaryEntry → QueryResponse)
- Complete design documentation

### **What We Need ❌**
The actual 4-stage semantic reduction pipeline:
1. **Stage 1**: WSU extraction from adapters
2. **Stage 2**: Gloss normalization for comparison  
3. **Stage 3**: Similarity graph construction
4. **Stage 4**: Sense bucketing/clustering
5. **Stage 5**: Semantic constant assignment

## Critical Discovery: Architecture Gap

**Problem**: Design assumes granular WSUs with stable references, but current `DictionaryDefinition` schema lacks:
- `source_ref` field for sense-level source tracking
- Structured `domains` and `register` metadata
- Consistent adapter implementations

**Solution**: **Schema evolution first** before pipeline implementation.

## Recommended Implementation Path

### **Phase 0: Schema Enhancement** (Immediate)
1. Add `source_ref`, `domains`, `register` fields to `DictionaryDefinition`
2. Update CDSL adapter to populate these fields
3. Test with Sanskrit data (agni, śiva)

### **Phase 1-5: Semantic Reduction Pipeline**
Follow the 5-phase migration plan with incremental, non-breaking changes.

## Key Technical Decisions

### **Schema Evolution Strategy**
- **Approach**: Add optional fields to existing schema
- **Benefit**: Backward compatible, gradual adoption
- **Risk**: Inconsistent data during transition

### **WSU Extraction Approach**
- **Hybrid**: Extract from enhanced schema when available, fallback parsing otherwise
- **Progressive**: Update adapters gradually over time

### **Performance Targets**
- WSU extraction: < 50ms per entry
- Similarity scoring: < 100ms for 50 WSUs  
- Full pipeline: < 500ms for typical queries

## Success Metrics

### **Phase 0 Complete**
- [ ] `DictionaryDefinition` schema enhanced
- [ ] CDSL adapter populates source_ref
- [ ] Sanskrit tests pass with MW IDs
- [ ] No breaking changes

### **Project Complete**
- [ ] Semantic format uses actual reduction
- [ ] Performance < 500ms for typical queries
- [ ] Deterministic outputs
- [ ] All languages supported
- [ ] Evidence inspection available
- [ ] Mode switching operational

## Timeline Estimate

**Total**: 9-12 weeks (2-3 months)
- Phase 0: 1-2 weeks
- Phase 1: 1-2 weeks  
- Phase 2: 2 weeks
- Phase 3: 2 weeks
- Phase 4: 2 weeks
- Phase 5: 1-2 weeks

## Next Immediate Actions

### **Action 1: Schema Update**
Update `src/langnet/schema.py`:
```python
# Add to DictionaryDefinition
source_ref: str | None = None
domains: list[str] = field(default_factory=list)
register: list[str] = field(default_factory=list)
confidence: float | None = None
```

### **Action 2: CDSL Adapter Enhancement**
Modify CDSL adapter to parse `sense_lines` into proper `DictionaryDefinition` objects with `source_ref`.

### **Action 3: Test Creation**
Create tests for new schema fields and WSU extraction.

## Risk Management

### **Primary Risks**
1. **Performance degradation**: Profile early, add caching
2. **Non-deterministic outputs**: Strict sorting rules, extensive testing
3. **Adapter compatibility**: Optional fields, gradual updates
4. **Constant registry bloat**: Automatic merging, size limits

### **Mitigation Strategies**
- Feature flags for new functionality
- Fallback paths for missing data
- Comprehensive test suite
- Incremental rollout

## Stakeholder Impact

### **Users**
- `semantic` command becomes "real" semantic reduction
- Legacy `query` command unchanged
- Optional performance impact for semantic format

### **Developers**
- Adapter updates required gradually
- New WSU extraction patterns to learn
- Enhanced debugging with evidence inspection

### **Documentation**
- Update API docs for semantic format
- Create adapter migration guide
- Document performance characteristics

## Conclusion

The semantic reduction project is **well-planned and ready for implementation**. We have:

1. ✅ Complete design documentation
2. ✅ Detailed implementation roadmap  
3. ✅ Architecture gap analysis
4. ✅ Step-by-step migration plan
5. ✅ Risk mitigation strategies
6. ✅ Success criteria defined

**Recommendation**: Begin Phase 0 (Schema Enhancement) immediately, as it enables all future work without breaking existing functionality.

---

*This summary provides a complete overview of the semantic reduction project planning. Refer to individual documents for detailed specifications.*

## Document Relationships

```
Project Summary (this document)
    ├── Roadmap (5-phase implementation)
    ├── Adapter Requirements (WSU extraction)  
    ├── Similarity Spec (algorithm details)
    ├── Gap Analysis (architecture issues)
    └── Migration Plan (step-by-step strategy)
```

**Next Step**: Move planning documents from `todo/` to `active/` when implementation begins.