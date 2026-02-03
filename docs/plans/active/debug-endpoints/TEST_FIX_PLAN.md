# Test Fix Plan: Fixing 27 Failing Tests

## Executive Summary

**Current State**: 27 tests are failing across 4 test files due to architectural changes in the codebase.

**Root Causes**:
1. **Config Attribute Missing** (9 errors): Tests reference `langnet_config.enable_universal_schema` which doesn't exist - universal schema is now always enabled
2. **Return Type Changed** (18 failures): `handle_query()` now returns `List[DictionaryEntry]` instead of `dict` with source keys

**Goal**: Fix all failing tests by updating test code to match new architecture without modifying production code.

---

## Prerequisites for Junior Engineer

### Testing Framework
- **Unit Test Framework**: Python's built-in `unittest` module
- **Test Runner**: `nose2` (NOT pytest)
- **Run Command**: 
  ```bash
  python -m nose2 -s tests --config tests/nose2.cfg
  ```

### Project Structure
```
langnet-cli/
├── src/langnet/
│   ├── config.py          # Configuration (no enable_universal_schema)
│   ├── schema.py          # DictionaryEntry dataclass
│   ├── core.py            # LanguageEngine
│   └── backend_adapter.py # BackendAdapterRegistry
├── tests/
│   ├── test_universal_schema_integration.py  (9 failures)
│   ├── test_api_integration.py               (4 failures)
│   ├── test_sanskrit_features.py             (7 failures)
│   └── test_heritage_engine_integration.py   (7 failures)
└── docs/plans/active/debug-endpoints/
    └── TEST_FIX_PLAN.md
```

### Key Concepts
- **Universal Schema**: Always active now, no config toggle
- **DictionaryEntry**: Dataclass with fields including `source`, `entries`, `metadata`
- **Old Format**: `{"diogenes": {...}, "heritage": {...}}`
- **New Format**: `[DictionaryEntry(source="diogenes", ...), DictionaryEntry(source="heritage", ...)]`

---

## Root Cause Analysis

### The Change: Dict → List[DictionaryEntry]

**BEFORE (Old Architecture):**
```python
# handle_query() returned a dict keyed by source
result = engine.handle_query("lat", "lupus")
# result = {
#     "diogenes": {...},
#     "cdsl": {...},
#     "heritage": {...}
# }

# Old test code
self.assertIn("diogenes", result)
data = result["diogenes"]
```

**AFTER (New Architecture):**
```python
# handle_query() returns List[DictionaryEntry]
entries = engine.handle_query("lat", "lupus")
# entries = [
#     DictionaryEntry(source="diogenes", ...),
#     DictionaryEntry(source="cdsl", ...),
#     DictionaryEntry(source="heritage", ...)
# ]

# New test code needs to:
# 1. Find entries by source
# 2. Check existence
# 3. Access entry data
```

### DictionaryEntry Structure
```python
@dataclass
class DictionaryEntry:
    source: str          # "diogenes", "cdsl", "heritage", etc.
    entries: List[dict]  # The actual dictionary data
    metadata: dict       # Additional metadata
```

---

## File-by-File Fix Instructions

### File A: tests/test_universal_schema_integration.py (9 errors)

**Location**: `/home/nixos/langnet-tools/langnet-cli/tests/test_universal_schema_integration.py`

**Errors**:
- Line ~35: `AttributeError: 'Config' object has no attribute 'enable_universal_schema'` (9 occurrences)

**Root Cause**: 
- Test sets `langnet_config.enable_universal_schema = True/False`
- This attribute doesn't exist in `src/langnet/config.py`
- Universal schema is now always enabled

**Missing Import**:
```python
from langnet.backend_adapter import BackendAdapterRegistry
```

#### Fixes Required:

**1. Remove config manipulation code** (lines 30-40 approximately)
```python
# REMOVE THIS BLOCK:
langnet_config.enable_universal_schema = True
# OR
langnet_config.enable_universal_schema = False
```

**2. Add missing import**
```python
# Add to imports at top:
from langnet.backend_adapter import BackendAdapterRegistry
```

**3. Update assertions to work with List[DictionaryEntry]**
```python
# OLD:
result = self.engine.handle_query("lat", "lupus")
self.assertIn("diogenes", result)
self.assertIn("cdsl", result)

# NEW:
entries = self.engine.handle_query("lat", "lupus")
diogenes_entries = [e for e in entries if e.source == "diogenes"]
cdsl_entries = [e for e in entries if e.source == "cdsl"]
self.assertTrue(len(diogenes_entries) > 0, "Should have diogenes entries")
self.assertTrue(len(cdsl_entries) > 0, "Should have cdsl entries")
```

---

### File B: tests/test_api_integration.py (4 failures)

**Location**: `/home/nixos/langnet-tools/langnet-cli/tests/test_api_integration.py`

**Errors**:
- `TypeError: list indices must be integers or slices, not str`
- Tests try to access `result["diogenes"]` or `result["source_name"]`

**Affected Lines**:
- Lines that access result with string keys

#### Fixes Required:

**Add helper function** (at top of file or in test class):
```python
def find_entries_by_source(entries, source):
    """Helper to find all entries from a specific source."""
    return [e for e in entries if e.source == source]

def get_first_entry_by_source(entries, source):
    """Helper to get first entry from a specific source."""
    for entry in entries:
        if entry.source == source:
            return entry
    return None
```

**Update test methods**:
```python
# BEFORE:
def test_diogenes_query(self):
    result = self.engine.handle_query("lat", "lupus")
    self.assertIn("diogenes", result)
    self.assertIsInstance(result["diogenes"], dict)

# AFTER:
def test_diogenes_query(self):
    entries = self.engine.handle_query("lat", "lupus")
    diogenes_entries = find_entries_by_source(entries, "diogenes")
    self.assertTrue(len(diogenes_entries) > 0)
    self.assertIsInstance(diogenes_entries[0].entries, list)
```

---

### File C: tests/test_sanskrit_features.py (7 failures)

**Location**: `/home/nixos/langnet-tools/langnet-cli/tests/test_sanskrit_features.py`

**Errors**:
- `TypeError: list indices must be integers or slices, not str`
- Mix of backend tests (good) and engine tests (broken)

**Strategy**:
- Keep backend tests that work directly with backend calls
- Fix engine tests that expect dict format

#### Fixes Required:

**1. Identify test types:**
```python
# BACKEND TESTS (keep as-is - these work):
def test_sanskrit_morphology_query_returns_result(self):
    result = self.sanskrit_backend.query("agni")
    # This works - it's calling backend directly

# ENGINE TESTS (need fixing):
def test_sanskrit_engine_query(self):
    result = self.engine.handle_query("san", "agni")
    # This breaks - handle_query returns List[DictionaryEntry]
```

**2. Update engine tests:**
```python
# BEFORE:
def test_sanskrit_engine_query(self):
    result = self.engine.handle_query("san", "agni")
    self.assertIn("cdsl", result)
    self.assertIn("heritage", result)

# AFTER:
def test_sanskrit_engine_query(self):
    entries = self.engine.handle_query("san", "agni")
    cdsl_entries = [e for e in entries if e.source == "cdsl"]
    heritage_entries = [e for e in entries if e.source == "heritage"]
    
    self.assertTrue(len(cdsl_entries) > 0, "Should have cdsl entries")
    self.assertTrue(len(heritage_entries) > 0, "Should have heritage entries")
```

---

### File D: tests/test_heritage_engine_integration.py (7 failures)

**Location**: `/home/nixos/langnet-tools/langnet-cli/tests/test_heritage_engine_integration.py`

**Errors**:
- `TypeError: list indices must be integers or slices, not str`
- Mock tests expect combined dict format

**Complexity**: These tests use mocks and are more complex

#### Fixes Required:

**Update mock return values**:
```python
# BEFORE:
@patch('langnet.engine.core.LanguageEngine.handle_query')
def test_heritage_integration(self, mock_handle):
    # Mock returns dict format
    mock_handle.return_value = {
        "heritage": {"data": "test"},
        "cdsl": {"data": "test"}
    }
    
    result = self.engine.handle_query("lat", "lupus")
    self.assertIn("heritage", result)

# AFTER:
@patch('langnet.engine.core.LanguageEngine.handle_query')
def test_heritage_integration(self, mock_handle):
    # Mock returns List[DictionaryEntry] format
    from langnet.schema import DictionaryEntry
    mock_handle.return_value = [
        DictionaryEntry(source="heritage", entries=[{"data": "test"}], metadata={}),
        DictionaryEntry(source="cdsl", entries=[{"data": "test"}], metadata={})
    ]
    
    entries = self.engine.handle_query("lat", "lupus")
    heritage_entries = [e for e in entries if e.source == "heritage"]
    self.assertTrue(len(heritage_entries) > 0)
```

---

## Helper Functions to Add

Create a test utilities module or add to each file:

```python
# tests/helpers/test_utils.py (new file)
from typing import List, Optional
from langnet.schema import DictionaryEntry

def find_entries_by_source(entries: List[DictionaryEntry], source: str) -> List[DictionaryEntry]:
    """Find all entries from a specific source."""
    return [e for e in entries if e.source == source]

def get_first_entry_by_source(entries: List[DictionaryEntry], source: str) -> Optional[DictionaryEntry]:
    """Get first entry from a specific source."""
    for entry in entries:
        if entry.source == source:
            return entry
    return None

def has_source(entries: List[DictionaryEntry], source: str) -> bool:
    """Check if entries contain a specific source."""
    return any(e.source == source for e in entries)

def count_sources(entries: List[DictionaryEntry]) -> dict:
    """Count entries by source."""
    from collections import Counter
    return Counter(e.source for e in entries)
```

**Import in test files:**
```python
from tests.helpers.test_utils import (
    find_entries_by_source,
    get_first_entry_by_source,
    has_source
)
```

---

## Code Examples: Before & After

### Example 1: Simple Existence Check

**BEFORE (BROKEN):**
```python
def test_query_returns_diogenes(self):
    result = self.engine.handle_query("lat", "lupus")
    self.assertIn("diogenes", result)  # TypeError!
```

**AFTER (FIXED):**
```python
def test_query_returns_diogenes(self):
    entries = self.engine.handle_query("lat", "lupus")
    diogenes_entries = [e for e in entries if e.source == "diogenes"]
    self.assertTrue(len(diogenes_entries) > 0, "Should have diogenes entries")
```

### Example 2: Checking Multiple Sources

**BEFORE (BROKEN):**
```python
def test_multi_source_query(self):
    result = self.engine.handle_query("san", "agni")
    self.assertIn("cdsl", result)
    self.assertIn("heritage", result)
    self.assertIsInstance(result["cdsl"], dict)
```

**AFTER (FIXED):**
```python
def test_multi_source_query(self):
    entries = self.engine.handle_query("san", "agni")
    
    cdsl_entries = [e for e in entries if e.source == "cdsl"]
    heritage_entries = [e for e in entries if e.source == "heritage"]
    
    self.assertTrue(len(cdsl_entries) > 0)
    self.assertTrue(len(heritage_entries) > 0)
    self.assertIsInstance(cdsl_entries[0].entries, list)
```

### Example 3: Mock Test Update

**BEFORE (BROKEN):**
```python
@patch('langnet.engine.core.LanguageEngine.handle_query')
def test_with_mock(self, mock_handle):
    mock_handle.return_value = {"heritage": {"test": "data"}}
    
    result = self.engine.handle_query("lat", "canis")
    self.assertIn("heritage", result)
    self.assertEqual(result["heritage"]["test"], "data")
```

**AFTER (FIXED):**
```python
@patch('langnet.engine.core.LanguageEngine.handle_query')
def test_with_mock(self, mock_handle):
    from langnet.schema import DictionaryEntry
    mock_handle.return_value = [
        DictionaryEntry(source="heritage", entries=[{"test": "data"}], metadata={})
    ]
    
    entries = self.engine.handle_query("lat", "canis")
    heritage_entries = [e for e in entries if e.source == "heritage"]
    
    self.assertTrue(len(heritage_entries) > 0)
    self.assertEqual(heritage_entries[0].entries[0]["test"], "data")
```

---

## Testing Strategy

### Step-by-Step Approach

**1. Fix File A First** (test_universal_schema_integration.py)
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg test_universal_schema_integration
   ```
   - Remove config manipulation
   - Add missing import
   - Update assertions
   - Goal: 9 → 0 failures

**2. Fix File B** (test_api_integration.py)
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg test_api_integration
   ```
   - Add helper functions
   - Update 4 failing tests
   - Goal: 9 + 4 → 13 failures (4 fixed)

**3. Fix File C** (test_sanskrit_features.py)
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg test_sanskrit_features
   ```
   - Identify which tests are engine vs backend
   - Fix only engine tests
   - Goal: 13 + 7 → 20 failures (7 fixed)

**4. Fix File D** (test_heritage_engine_integration.py)
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg test_heritage_engine_integration
   ```
   - Update mock return values
   - Update assertions
   - Goal: 20 + 7 → 27 failures (7 fixed)

**5. Full Test Suite**
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg
   # OR
   just test
   ```
   - Should show 0 failures
   - Verify all tests pass

### Verification Commands

```bash
# Run specific file
python -m nose2 -s tests --config tests/nose2.cfg test_universal_schema_integration

# Run all tests
python -m nose2 -s tests --config tests/nose2.cfg

# Run with verbose output
python -m nose2 -s tests --config tests/nose2.cfg -v

# Check test count
python -m nose2 -s tests --config tests/nose2.cfg 2>&1 | grep -E "(FAIL|ERROR|OK)"
```

---

## Common Pitfalls to Avoid

### ❌ DON'T:
1. **Use pytest** - We use `unittest` + `nose2`
2. **Modify production code** - Only fix tests
3. **Change test logic** - Keep test intent, just update format
4. **Keep config manipulation** - Remove all `enable_universal_schema` references
5. **Miss mock updates** - Mocks must return `List[DictionaryEntry]`
6. **Delete backend tests** - Direct backend tests should work unchanged
7. **Forget imports** - Add `from langnet.schema import DictionaryEntry` where needed

### ✅ DO:
1. **Use helper functions** - Create reusable entry finder functions
2. **Test one file at a time** - Avoid confusion
3. **Check line numbers** - Errors tell you exactly where to fix
4. **Keep test intent** - If test was checking for diogenes data, still check for it
5. **Use helper functions** - Write once, use many times
6. **Verify after each file** - Ensure no regressions

### 🔍 Debugging Tips

If a test still fails:
```python
# Add debug prints temporarily
def test_debug(self):
    entries = self.engine.handle_query("lat", "lupus")
    print(f"Type: {type(entries)}")
    print(f"Length: {len(entries)}")
    for i, entry in enumerate(entries):
        print(f"  [{i}] source={entry.source}, type={type(entry.entries)}")
    # Then fix based on actual structure
```

---

## Definition of Done

### ✅ Success Criteria:

1. **All 4 test files pass** individually:
   - `test_universal_schema_integration.py`: 0 failures
   - `test_api_integration.py`: 0 failures
   - `test_sanskrit_features.py`: 0 failures
   - `test_heritage_engine_integration.py`: 0 failures

2. **Total failures reduced**: 27 → 0

3. **Full test suite passes**:
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg
   # Output should show: OK (XX tests)
   ```

4. **No production code changes** - Verify with:
   ```bash
   git diff src/  # Should be empty
   ```

5. **Test coverage maintained** - All original test scenarios still work

6. **Code follows patterns** - Uses helper functions, follows existing style

### Verification Checklist:

- [ ] test_universal_schema_integration.py passes (9 fixes)
- [ ] test_api_integration.py passes (4 fixes)
- [ ] test_sanskrit_features.py passes (7 fixes)
- [ ] test_heritage_engine_integration.py passes (7 fixes)
- [ ] Full test suite passes
- [ ] No changes to production code
- [ ] Helper functions added/used
- [ ] Code follows project conventions

---

## Quick Reference Summary

| File | Failures | Main Issue | Fix Approach |
|------|----------|------------|--------------|
| test_universal_schema_integration.py | 9 | Config attribute missing | Remove config code, add import |
| test_api_integration.py | 4 | Dict → List[DictionaryEntry] | Use entry source filtering |
| test_sanskrit_features.py | 7 | Dict → List[DictionaryEntry] | Update engine tests only |
| test_heritage_engine_integration.py | 7 | Mock format wrong | Update mock returns |

### Key Code Patterns

**Find by source:**
```python
filtered = [e for e in entries if e.source == "diogenes"]
```

**Check existence:**
```python
self.assertTrue(any(e.source == "diogenes" for e in entries))
```

**Get first match:**
```python
entry = next((e for e in entries if e.source == "diogenes"), None)
```

**Mock return:**
```python
from langnet.schema import DictionaryEntry
mock_return = [DictionaryEntry(source="heritage", entries=[...], metadata={})]
```

---

## Support & Resources

### Where to Find Help:
1. **Codebase**: Look at `src/langnet/schema.py` for DictionaryEntry
2. **Similar Tests**: Search for existing tests that handle List[DictionaryEntry]
3. **AGENTS.md**: Project conventions and testing patterns
4. **Developer.md**: Development workflow

### Questions to Ask:
- "What does DictionaryEntry contain?"
- "How do I check if entries have a specific source?"
- "Do I need to update the mock or the assertion?"

### Remember:
- **One file at a time**
- **Run tests after each change**
- **Keep test intent, fix format**
- **No production code changes**
- **Use helper functions**

Good luck! You got this! 🚀
