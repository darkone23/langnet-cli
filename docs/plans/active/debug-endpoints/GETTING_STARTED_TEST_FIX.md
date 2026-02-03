# Getting Started: Fixing 27 Failing Tests

## Quick Start

**Goal:** Fix 27 failing tests due to Universal Schema implementation.

### Step 1: Understand the Problem
1. Read the comprehensive fix plan: `/home/nixos/langnet-tools/langnet-cli/docs/plans/active/debug-endpoints/TEST_FIX_PLAN.md`
2. Run the failing tests to see the current state:
   ```bash
   python -m nose2 -s tests --config tests/nose2.cfg
   ```

### Step 2: Start Fixing (Pick One File)

**Option A: Fix universal schema tests (easiest)**
```bash
# Focus on test_universal_schema_integration.py
python -m nose2 -s tests --config tests/nose2.cfg test_universal_schema_integration
# Then open the file and fix the 2 simple issues:
# 1. Remove config.enable_universal_schema references
# 2. Add BackendAdapterRegistry import
```

**Option B: Fix API integration tests**
```bash
# Focus on test_api_integration.py
python -m nose2 -s tests --config tests/nose2.cfg test_api_integration
# Then fix dict → List[DictionaryEntry] conversion
```

### Step 3: Use This Prompt

Copy-paste this prompt to continue the work:

```
I need to fix the 27 failing tests in langnet-cli. I've read TEST_FIX_PLAN.md and understand the issues:
1. Config attribute missing (enable_universal_schema)
2. Return type changed from dict to List[DictionaryEntry]

Start by fixing test_universal_schema_integration.py:
1. Remove all references to langnet_config.enable_universal_schema
2. Add missing BackendAdapterRegistry import
3. Run just this test file to verify

Then show me the diff so I can review the changes.
```

### Step 4: Run After Each Change
```bash
# Run specific test file
python -m nose2 -s tests --config tests/nose2.cfg test_universal_schema_integration

# Run all tests to track progress
python -m nose2 -s tests --config tests/nose2.cfg
```

### Step 5: Expected Fix Pattern

**For each file**, you'll need to:
1. Add helper functions to find entries by source
2. Convert `result["source"]` to `find_entries_by_source(entries, "source")`
3. Update assertions accordingly

**Example Pattern:**
```python
# BEFORE (broken):
result = self.engine.handle_query("lat", "lupus")
self.assertIn("diogenes", result)
data = result["diogenes"]

# AFTER (fixed):
entries = self.engine.handle_query("lat", "lupus")
diogenes_entries = [e for e in entries if e.source == "diogenes"]
self.assertTrue(len(diogenes_entries) > 0)
data = diogenes_entries[0]
```

### Step 6: Verify Fixes
```bash
# When all tests pass:
python -m nose2 -s tests --config tests/nose2.cfg
# Should show: OK (all tests pass)
```

## Files to Fix (in recommended order):
1. `test_universal_schema_integration.py` - 9 errors (config issues)
2. `test_api_integration.py` - 4 failures (return type)
3. `test_sanskrit_features.py` - 7 failures (return type)
4. `test_heritage_engine_integration.py` - 7 failures (return type + mocks)

## Key Files to Reference:
- `/home/nixos/langnet-tools/langnet-cli/src/langnet/schema.py` - DictionaryEntry structure
- `/home/nixos/langnet-tools/langnet-cli/src/langnet/engine/core.py` - handle_query() method
- `/home/nixos/langnet-tools/langnet-cli/docs/plans/active/debug-endpoints/TEST_FIX_PLAN.md` - Detailed instructions

## Common Commands:
- `just test` - Run all tests
- `just lint` - Check code style
- `just format` - Format code
- `git status` - Check changes
- `git diff` - Review modifications

## Success Criteria:
✅ All 27 tests pass
✅ No breaking changes to production code
✅ Helper functions added for reuse
✅ Tests use proper unittest patterns (not pytest)
