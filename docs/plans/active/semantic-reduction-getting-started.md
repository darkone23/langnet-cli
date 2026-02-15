# Semantic Reduction: Getting Started Guide

**Date**: 2026-02-15  
**Audience**: Next developer implementing semantic reduction pipeline

## 🚀 Quick Start

### **Prerequisites**
```bash
# 1. Clone and setup environment
git clone <repository>
cd langnet-cli
devenv shell langnet-cli

# 2. Verify current functionality
langnet-cli semantic san agni --output json
```

### **First 30 Minutes**
1. **Read**: `docs/plans/active/semantic-reduction-project-summary.md` (5 min)
2. **Understand**: Current schema gap (`src/langnet/schema.py:84-93`) (5 min)
3. **Test**: Run CDSL example (5 min)
4. **Plan**: Review Phase 0 tasks below (5 min)
5. **Start**: Make first code change (10 min)

## 📝 Phase 0: First Code Changes

### **Step 1: Update Schema**
```python
# File: src/langnet/schema.py
# Line ~84: DictionaryDefinition class
# ADD THESE FIELDS:
source_ref: str | None = None  # "mw:217497"
domains: list[str] = field(default_factory=list)
register: list[str] = field(default_factory=list)
confidence: float | None = None
```

### **Step 2: Update CDSL Adapter**
```python
# File: src/langnet/adapters/cdsl.py
# Modify sense_line parsing to populate source_ref
# Example: "217497: auspicious; benign; favorable"
# Should create DictionaryDefinition with:
#   definition: "auspicious; benign; favorable"
#   source_ref: "mw:217497"
#   domains: []  # Extract from metadata if available
#   register: []  # Extract from metadata if available
```

### **Step 3: Create Test**
```python
# File: tests/test_semantic_reduction_phase0.py
def test_cdsl_source_ref():
    """Verify CDSL adapter populates source_ref."""
    adapter = CdslAdapter()
    result = adapter.query("san", "agni")
    
    for entry in result:
        for definition in entry.definitions:
            assert definition.source_ref is not None
            assert definition.source_ref.startswith("mw:") or definition.source_ref.startswith("ap90:")
```

## 🔧 Development Commands

### **Essential Just Commands**
```bash
# Run tests
just test

# Type checking
just typecheck

# Linting
just ruff-format
just ruff-check

# Regenerate semantic schema (if needed)
just codegen
```

### **Debugging Commands**
```bash
# Test CDSL adapter directly
python -c "
from langnet.adapters.cdsl import CdslAdapter
a = CdslAdapter()
result = a.query('san', 'agni')
for entry in result:
    for d in entry.definitions:
        print(f'{d.source_ref}: {d.definition[:50]}...')
"

# Test current semantic converter
python -c "
from langnet.semantic_converter import convert_multiple_entries
from langnet.adapters.cdsl import CdslAdapter
a = CdslAdapter()
result = a.query('san', 'agni')
converted = convert_multiple_entries(result)
print(converted.to_json(indent=2))
"
```

## 🎯 Success Verification

### **Phase 0 Complete When**
```bash
# 1. Schema updates applied
grep "source_ref" src/langnet/schema.py

# 2. CDSL adapter updated
python -c "from langnet.adapters.cdsl import CdslAdapter; a=CdslAdapter(); r=a.query('san','agni'); print(r[0].definitions[0].source_ref)"

# 3. Tests passing
just test test_semantic_reduction*

# 4. No regression
langnet-cli query san agni --output json  # Should still work
```

## ❓ Common Questions

### **Q: Where should I put new code?**
**A**: Start with:
- Schema changes: `src/langnet/schema.py`
- CDSL adapter: `src/langnet/adapters/cdsl.py`
- Tests: `tests/test_semantic_reduction_*.py`
- New modules later: `src/langnet/semantic_reducer/`

### **Q: How to handle other adapters?**
**A**: Focus on CDSL first (has clearest structure). Update others in later phases.

### **Q: What about performance?**
**A**: Profile after Phase 0. Current target: < 50ms per entry for WSU extraction.

### **Q: How to test without breaking things?**
**A**: All Phase 0 changes are optional/non-breaking. Old code paths remain.

## 📚 Reference Documents

### **Read First (In Order)**
1. `docs/plans/active/semantic-reduction-project-summary.md` - Overview
2. `docs/plans/todo/semantic-reduction-gap-analysis.md` - Problem statement
3. `docs/plans/todo/semantic-reduction-migration-plan.md` - Solution path

### **Read as Needed**
4. `docs/plans/todo/semantic-reduction-roadmap.md` - Detailed phases
5. `docs/plans/todo/semantic-reduction-adapter-requirements.md` - Adapter specs
6. `docs/plans/todo/semantic-reduction-similarity-spec.md` - Algorithm details

## 🆘 Troubleshooting

### **Issue: CDSL adapter not returning data**
```bash
# Check if CDSL data is available
ls ~/cdsl_data/
# If not, run a query to trigger download
langnet-cli query san agni
```

### **Issue: Tests failing after schema changes**
```bash
# Run specific test to see error
python -m pytest tests/test_schema.py -v

# Check if cattrs serialization issues
python -c "
from langnet.schema import DictionaryDefinition
from cattrs import structure, unstructure
d = DictionaryDefinition(definition='test', pos='noun', source_ref='mw:123')
print(unstructure(d))
"
```

### **Issue: Type checking errors**
```bash
# Run typecheck
just typecheck

# If new fields cause issues, check imports
grep -r "DictionaryDefinition" src/langnet/
```

## 🎉 Next Steps After Phase 0

1. **Create WSU extraction module** (`src/langnet/semantic_reducer/wsu_extractor.py`)
2. **Extract WSUs from enhanced CDSL data**
3. **Build normalization pipeline**
4. **Proceed to Phase 1** (see migration plan)

## 📞 Help Available

### **Code Patterns to Follow**
- Look at `src/langnet/semantic_converter.py` for mapping patterns
- Check `src/langnet/adapters/base.py` for adapter interface
- Review `tests/` for testing patterns

### **When Stuck**
1. Check existing adapter implementations
2. Run examples to understand data flow
3. Update tests to verify expectations
4. Document decisions made

---

*This guide should get you started in < 1 hour. Update it as you make progress.*