# Semantic Reduction Project - Complete Documentation

## 📋 Project Status
**Planning Complete ✅** | **Ready for Implementation** | **Last Updated**: 2026-02-15

## 🎯 Goal
Implement semantic reduction pipeline to convert raw lexical evidence into structured semantic output with:
- Stable concept identifiers (semantic constants)
- Witness traceability (source references)
- Epistemic mode support (open vs skeptic)
- Deterministic clustering

## 🔍 Critical Discovery
**Design vs Reality Gap**: Current schema doesn't match design assumptions. Need schema evolution first.

### **Required Schema Changes**
```python
# Add to DictionaryDefinition in src/langnet/schema.py
source_ref: str | None = None  # "mw:217497"
domains: list[str] = field(default_factory=list)
register: list[str] = field(default_factory=list)
confidence: float | None = None
```

## 📁 Documentation Structure

### **Start Here** (Read in Order)
1. **[Getting Started](semantic-reduction-getting-started.md)** - First 30 minutes guide
2. **[Project Summary](semantic-reduction-project-summary.md)** - Complete overview
3. **[Current Status](semantic-reduction-current-status.md)** - Implementation readiness

### **Planning Documents**
4. **[Migration Plan](../todo/semantic-reduction-migration-plan.md)** - 5-phase step-by-step
5. **[Roadmap](../todo/semantic-reduction-roadmap.md)** - Detailed implementation phases
6. **[Gap Analysis](../todo/semantic-reduction-gap-analysis.md)** - Architecture issues
7. **[Adapter Requirements](../todo/semantic-reduction-adapter-requirements.md)** - WSU extraction specs
8. **[Similarity Spec](../todo/semantic-reduction-similarity-spec.md)** - Algorithm details

### **Handoff Support**
9. **[Handoff Checklist](semantic-reduction-handoff-checklist.md)** - Completeness verification

## 🚀 Quick Start Implementation

### **Phase 0: Schema Enhancement** (Week 1-2)
1. **Update schema** (`src/langnet/schema.py`)
2. **Enhance CDSL adapter** to populate `source_ref`
3. **Create tests** for new functionality
4. **Verify** no breaking changes

### **Command to Test**
```bash
devenv shell langnet-cli -- langnet-cli semantic san agni --output json
```

## 📊 Success Metrics

### **Phase 0 Complete When**
- [ ] Schema updated with new fields
- [ ] CDSL adapter populates source_ref
- [ ] Sanskrit tests pass with MW IDs
- [ ] No breaking changes to existing API

### **Project Complete When**
- [ ] Semantic format uses actual reduction
- [ ] Performance < 500ms for typical queries
- [ ] Deterministic outputs
- [ ] All languages supported
- [ ] Evidence inspection available
- [ ] Mode switching operational

## ⏱️ Timeline
**Total**: 9-12 weeks
- Phase 0: 1-2 weeks (schema + CDSL)
- Phase 1: 1-2 weeks (WSU extraction)
- Phase 2: 2 weeks (similarity engine)
- Phase 3: 2 weeks (clustering)
- Phase 4: 2 weeks (constants)
- Phase 5: 1-2 weeks (integration)

## ⚠️ Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance degradation | Profile early, add caching, legacy fallback |
| Non-deterministic outputs | Strict sorting rules, extensive testing |
| Adapter compatibility | Optional fields, gradual updates |
| Constant registry bloat | Automatic merging, size limits |

## 🤝 Handoff Ready
✅ **Yes** - Another developer can pick this up with:
- Complete planning documentation
- Clear implementation path
- Risk mitigation strategies
- Getting started guide
- Testable success criteria

## 📞 Next Steps
1. **Review** `getting-started.md` for immediate tasks
2. **Execute** Phase 0 schema changes
3. **Follow** migration plan for subsequent phases
4. **Update** documentation as implementation progresses

---

*All planning complete. Ready for implementation starting with Phase 0.*