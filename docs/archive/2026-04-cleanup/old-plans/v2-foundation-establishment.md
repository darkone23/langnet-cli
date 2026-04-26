# V2 Foundation Establishment Plan

**Date**: 2026-04-07
**Status**: ACTIVE
**Priority**: CRITICAL (Blocks P0 dictionary parsing work)
**Type**: Infrastructure & Testing
**Owner**: Architecture Team

## Executive Summary

This plan establishes a solid, well-tested foundation for V2 before tackling P0 dictionary parsing work. After completing type cleanup (26 errors → 0), we need to:

1. Make storage persistent and manageable
2. Add comprehensive integration tests
3. Document the execution handler architecture
4. Create developer tooling for the V2 pipeline
5. Validate cache invalidation mechanisms

**Success Criteria**: A stable V2 pipeline with persistent storage, 95%+ test coverage on the execution flow, and clear documentation for adding new handlers.

**Total Estimate**: 20-27 hours (2.5-3.5 days)

---

## Current State Assessment

### What Works ✅

1. **Execution Pipeline**: Complete fetch → extract → derive → claim flow
   - Staged execution with dependency resolution
   - Handler registry with 6 tool implementations (diogenes, whitakers, cltk, spacy, heritage, cdsl)
   - Provenance chain tracking at each stage
   - Handler versioning for cache invalidation

2. **Storage Layer**: DuckDB indexes for all stages
   - Raw response storage
   - Extraction/derivation caching
   - Claim storage with subject/predicate indexes
   - Plan response caching (plan_hash → response_ids)

3. **Query Planning**: Language-specific tool call generation
   - Normalizer integration
   - DAG-based dependency tracking
   - Stable plan hashing for cache keys

4. **CLI Integration**: Working commands
   - `langnet-cli normalize` - query normalization
   - `langnet-cli plan` - plan generation
   - `langnet-cli plan-exec` - plan execution
   - `triples_dump.py` - demonstrates end-to-end flow

5. **Tests**: 41 unit tests covering core components
   - Executor tests with staging
   - Storage index round-trip tests
   - Planner tests for all 3 languages
   - Handler tests for real implementations

### What's Broken/Missing ❌

1. **Storage is Ephemeral**: All databases use `:memory:`
   - No persistent cache across runs
   - No way to inspect cached data
   - No strategy for managing disk space
   - `normalization_db_path()` exists but underutilized

2. **No Index Management**:
   - Can't check cache status
   - Can't clear specific tool caches
   - Can't rebuild indexes
   - No disk usage visibility

3. **Test Coverage Gaps**:
   - No end-to-end integration tests
   - No cache invalidation tests
   - No concurrent access tests
   - No handler version upgrade tests

4. **Documentation Gaps**:
   - No guide for adding new handlers
   - No explanation of handler versioning
   - No architecture diagrams for V2
   - Storage schema not documented

5. **Developer Experience**:
   - Hard to debug execution flow
   - No visibility into what's cached
   - No way to force re-execution
   - No performance benchmarks

---

## Foundation Tasks

### Task 1: Persistent Storage Layer

**Goal**: Make all DuckDB storage persistent and manageable

**Priority**: P0
**Estimate**: 2-3 hours
**Dependencies**: None

**Files to Create/Modify**:
- `src/langnet/storage/paths.py` - Add functions for all DB paths
- `src/langnet/storage/db.py` - Add persistent connection management
- `src/langnet/cli.py` - Add `--db-path` option to commands

**Implementation**:

```python
# src/langnet/storage/paths.py

from pathlib import Path
import os

def _storage_base() -> Path:
    """Base directory for all langnet storage."""
    base = os.environ.get("LANGNET_DATA_DIR")
    if base:
        return Path(base)
    # XDG compliance
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "langnet"
    return Path.home() / ".local" / "share" / "langnet"

def main_db_path() -> Path:
    """Path to the main langnet.duckdb (cross-tool indexes)."""
    return _storage_base() / "langnet.duckdb"

def tool_db_path(tool: str) -> Path:
    """Path to a tool-specific database."""
    return _storage_base() / "tools" / f"{tool}.duckdb"

def all_db_paths() -> dict[str, Path]:
    """Return all database paths."""
    paths = {"main": main_db_path()}
    tools = ["diogenes", "whitakers", "cltk", "spacy", "heritage", "cdsl", "cts_index"]
    for tool in tools:
        paths[f"tool:{tool}"] = tool_db_path(tool)
    return paths
```

**Validation Command**:
```bash
# After implementation
python3 -c "
from langnet.storage.paths import main_db_path, tool_db_path
print('Main DB:', main_db_path())
print('Diogenes DB:', tool_db_path('diogenes'))
assert main_db_path().name == 'langnet.duckdb'
print('✓ Paths working')
"

# Verify storage base can be overridden
LANGNET_DATA_DIR=/tmp/langnet-test python3 -c "
from langnet.storage.paths import main_db_path
assert '/tmp/langnet-test' in str(main_db_path())
print('✓ ENV override working')
"
```

**Testing**:
- Create `tests/test_storage_paths.py`
- Test path resolution with/without ENV vars
- Test XDG compliance
- Test path creation with mkdir

---

### Task 2: Index Management CLI

**Goal**: Add commands to inspect and manage storage indexes

**Priority**: P0
**Estimate**: 3-4 hours
**Dependencies**: Task 1

**Files to Modify**:
- `src/langnet/cli.py` - Add `index` command group

**Implementation**:

```python
# src/langnet/cli.py

@cli.group()
def index():
    """Manage storage indexes."""
    pass

@index.command("status")
@click.option("--tool", help="Show status for specific tool")
def index_status(tool: str | None):
    """Show storage index status."""
    from langnet.storage.paths import all_db_paths
    import humanize  # Add to dependencies

    paths = all_db_paths()
    if tool:
        paths = {k: v for k, v in paths.items() if tool in k}

    for name, path in paths.items():
        if path.exists():
            size = path.stat().st_size
            click.echo(f"{name:20} {humanize.naturalsize(size):>10}  {path}")
            # Show row counts for main tables
            with connect_duckdb(path, read_only=True) as conn:
                tables = ["raw_response_index", "extraction_index",
                         "derivation_index", "claims"]
                for table in tables:
                    try:
                        count = conn.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0]
                        click.echo(f"  {table:30} {count:>6} rows")
                    except:
                        pass
        else:
            click.echo(f"{name:20} {'(not created)':>10}")

@index.command("clear")
@click.option("--tool", help="Clear specific tool cache")
@click.option("--all", is_flag=True, help="Clear all caches")
@click.confirmation_option(prompt="This will delete cached data. Continue?")
def index_clear(tool: str | None, all: bool):
    """Clear storage indexes (safe - will be rebuilt on next query)."""
    from langnet.storage.paths import all_db_paths

    paths = all_db_paths()
    if tool:
        paths = {k: v for k, v in paths.items() if tool in k}
    elif not all:
        raise click.UsageError("Must specify --tool or --all")

    for name, path in paths.items():
        if path.exists():
            path.unlink()
            click.echo(f"✓ Removed {name}")

@index.command("rebuild")
@click.argument("query")
@click.option("--language", required=True)
def index_rebuild(query: str, language: str):
    """Rebuild indexes for a specific query (force re-fetch)."""
    click.echo(f"Rebuilding indexes for '{query}' ({language})...")
    # Implementation: run query with allow_cache=False
```

**Validation Commands**:
```bash
# After implementation
langnet-cli index status
# Expected: Lists all databases with sizes and row counts

langnet-cli index status --tool diogenes
# Expected: Shows only diogenes-related databases

langnet-cli index clear --tool cdsl
# Expected: Removes cdsl.duckdb after confirmation

langnet-cli index rebuild "lupus" --language lat
# Expected: Re-fetches and rebuilds all lupus-related indexes
```

**Testing**:
- Create `tests/test_cli_index.py`
- Test status command with existing/missing DBs
- Test clear with confirmation
- Test rebuild flow

**Dependencies**:
- Add `humanize` to pyproject.toml for size formatting

---

### Task 3: Integration Tests

**Goal**: End-to-end tests covering the full pipeline

**Priority**: P1
**Estimate**: 6-8 hours
**Dependencies**: Tasks 1, 2

**Files to Create**:
- `tests/integration/test_v2_pipeline.py`

**Implementation**:

```python
# tests/integration/test_v2_pipeline.py

import duckdb
import pytest
from query_spec import LanguageHint
from langnet.planner.core import ToolPlanner, PlannerConfig
from langnet.execution.executor import execute_plan_staged
from langnet.execution.registry import default_registry
from langnet.storage.plan_index import apply_schema
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.claim_index import ClaimIndex

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage for testing."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    apply_schema(conn)
    yield conn
    conn.close()

def test_pipeline_latin_query_end_to_end(temp_storage):
    """
    Test complete V2 pipeline: normalize → plan → execute → claims

    This validates:
    - Normalizer produces candidates
    - Planner generates tool calls
    - Executor runs all stages (fetch/extract/derive/claim)
    - Claims are produced and stored
    - Provenance chains are complete
    """
    # Stage 2: Plan (skip normalization for simplicity)
    from query_spec import NormalizedQuery

    query = NormalizedQuery(
        original="lupus",
        language=LanguageHint.LANGUAGE_HINT_LAT,
        candidates=[],
    )

    planner = ToolPlanner(PlannerConfig(
        diogenes_endpoint="http://localhost:8888/Diogenes.cgi",
        include_whitakers=True,
        include_cltk=False,
        max_candidates=3,
    ))

    candidate = planner.select_candidate(query)
    plan = planner.build(query, candidate)

    assert len(plan.tool_calls) > 0
    assert any(c.tool.startswith("fetch.diogenes") for c in plan.tool_calls)

    # Stage 3: Execute
    from langnet.cli import _build_exec_clients

    clients = _build_exec_clients(
        plan,
        "http://localhost:8888/Diogenes.cgi",
        use_stubs=False
    )
    registry = default_registry(use_stubs=False)

    artifacts = execute_plan_staged(
        plan=plan,
        clients=clients,
        registry=registry,
        raw_index=RawResponseIndex(temp_storage),
        extraction_index=ExtractionIndex(temp_storage),
        derivation_index=DerivationIndex(temp_storage),
        claim_index=ClaimIndex(temp_storage),
        plan_response_index=None,
        allow_cache=False,
    )

    # Validate results
    assert artifacts.raw_effects, "Should have fetched raw responses"
    assert artifacts.extractions, "Should have parsed extractions"
    assert artifacts.derivations, "Should have derived facts"
    assert artifacts.claims, "Should have produced claims"

    # Validate provenance
    for claim in artifacts.claims:
        assert claim.provenance_chain, "Claims must have provenance"
        assert len(claim.provenance_chain) > 0

def test_cache_reuse_on_second_run(temp_storage):
    """
    Test that second execution reuses cached responses.

    Validates:
    - Plan hash is stable
    - Second run uses cached raw responses
    - Claims are still produced
    """
    # First run
    # artifacts1 = _run_pipeline(temp_storage, allow_cache=True)

    # Second run (same query)
    # artifacts2 = _run_pipeline(temp_storage, allow_cache=True)

    # Should reuse cache
    # assert artifacts2.from_cache is True
    # assert len(artifacts2.claims) == len(artifacts1.claims)

    # TODO: Implement after storage persistence is complete
    pytest.skip("Requires persistent storage implementation")

def test_handler_version_invalidates_cache(temp_storage):
    """
    Test that changing handler version invalidates cache.

    This is critical for safe handler upgrades.
    """
    # TODO: Implement after handler versioning is fully wired
    pytest.skip("Requires handler version tracking implementation")
```

**Validation Commands**:
```bash
# After implementation
just test tests/integration/test_v2_pipeline.py

# Should run all integration tests and pass
# Expected: 1+ test passing (others may be skipped until dependencies complete)
```

**Testing Strategy**:
- Use `tmp_path` fixture for isolated storage
- Test with real handlers (not stubs) for diogenes/whitakers
- May need to mock external HTTP calls if services unavailable
- Validate all stages produce expected data

---

### Task 4: Handler Development Guide

**Goal**: Document how to add new handlers to V2

**Priority**: P1
**Estimate**: 4-5 hours
**Dependencies**: None

**Files to Create**:
- `docs/technical/HANDLER_DEVELOPMENT.md`

**Content Outline**:

1. **Overview**: Handler stages (extract/derive/claim)
2. **Handler Signature**: Function signatures for each stage
3. **Step-by-Step Guide**: Adding a new tool
4. **Handler Versioning**: Using `@versioned` decorator
5. **Best Practices**: Error handling, logging, provenance
6. **Example**: Full implementation reference

**Validation**:
- Have another developer follow the guide to add a stub handler
- Verify guide completeness and clarity

---

### Task 5: Storage Schema Documentation

**Goal**: Document the storage schema and its purpose

**Priority**: P2
**Estimate**: 3-4 hours
**Dependencies**: Task 1

**Files to Create**:
- `docs/technical/STORAGE_SCHEMA.md`

**Content Outline**:

1. **Overview**: Database architecture (single DB, multiple tables)
2. **Tables**: Schema for each table (raw_response, extraction, derivation, claims)
3. **Cache vs Storage**: What's permanent vs disposable
4. **Cache Invalidation**: Handler versioning mechanism
5. **Indexes**: Performance-critical indexes
6. **Maintenance**: Safe operations for clearing/managing data

**Validation**:
- Review with someone unfamiliar with the schema
- Add diagrams if helpful

---

### Task 6: Performance Benchmarks

**Goal**: Establish baseline performance metrics

**Priority**: P2
**Estimate**: 2-3 hours
**Dependencies**: Tasks 1-3

**Files to Create**:
- `tests/benchmarks/test_v2_performance.py`

**Benchmarks to Implement**:

1. **Cache Hit Performance**: Should be < 10ms
2. **Cache Miss Performance**: Should be < 500ms
3. **Storage Size Growth**: Should be reasonable for 100 queries

**Validation**:
```bash
just test tests/benchmarks/

# Should output performance metrics
# Create baseline for future comparisons
```

---

## Implementation Order & Timeline

| Priority | Task | Estimate | Dependencies | Validation |
|----------|------|----------|--------------|------------|
| P0 | Task 1: Persistent Storage | 2-3h | None | `test_storage_paths.py` passes |
| P0 | Task 2: Index Management CLI | 3-4h | Task 1 | `langnet-cli index status` works |
| P1 | Task 3: Integration Tests | 6-8h | Tasks 1,2 | `test_v2_pipeline.py` passes |
| P1 | Task 4: Handler Dev Guide | 4-5h | None | Review by team |
| P2 | Task 5: Storage Schema Docs | 3-4h | Task 1 | Review by team |
| P2 | Task 6: Performance Benchmarks | 2-3h | Tasks 1-3 | Benchmarks run & baseline established |

**Total Estimate**: 20-27 hours (2.5-3.5 days)

**Suggested Order**:
1. Day 1: Tasks 1-2 (Storage + Index Management)
2. Day 2: Task 3 (Integration Tests)
3. Day 3: Tasks 4-6 (Documentation + Benchmarks)

---

## Success Criteria

### Automated Validation

After completing all tasks, these commands should pass:

```bash
# 1. Storage is persistent
langnet-cli index status
# Expected: Lists databases with sizes

# 2. Cache persists across runs
just triples-dump lat lupus all
just triples-dump lat lupus all  # Second run
# Expected: Second run shows "cache_hit=True" in logs

# 3. Index management works
langnet-cli index clear --tool diogenes
langnet-cli index status --tool diogenes
# Expected: diogenes DB removed, status shows "(not created)"

# 4. Integration tests pass
just test tests/integration/test_v2_pipeline.py
# Expected: All tests pass

# 5. Performance benchmarks establish baseline
just test tests/benchmarks/
# Expected: Benchmarks pass and print metrics

# 6. All existing tests still pass
just test-fast
# Expected: 38+ tests passing
```

### Readiness for P0 Work

Before starting P0 dictionary parsing, we must have:

- [ ] Storage persists across sessions
- [ ] Cache can be inspected and managed
- [ ] Integration tests cover end-to-end flow
- [ ] Handler development is documented
- [ ] Storage schema is documented
- [ ] Performance baselines established
- [ ] All existing tests still pass (38+ tests)
- [ ] Type checking still at 0 errors

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run `just test-fast` after each task |
| Storage migration issues | Keep `:memory:` as fallback option |
| Performance regression | Establish benchmarks before changes |
| Documentation drift | Update docs alongside code changes |
| Handler version conflicts | Test version upgrade path explicitly |

---

## Future Work (Post-Foundation)

After establishing this foundation, the following work can proceed:

1. **P0 Dictionary Parsing**: Lark grammars for entry parsing
   - Reference: `docs/plans/active/dictionary-entry-parsing-handoff.md`

2. **Semantic Reduction**: Clustering pipeline integration
   - Reference: `docs/plans/active/SEMANTIC_REDUCTION_README.md`

3. **CTS Hydration**: Citation expansion handler

4. **Output Formatting**: Pedagogical vs research views

5. **Fuzzy Search**: Universal schema integration

---

## References

- **V2 Master Plan**: `docs/v2-implementation-master-plan.md`
- **Tool Execution Flow**: `docs/plans/active/infra/tool-plan-execution-to-claims.md`
- **Working Example**: `.justscripts/triples_dump.py`
- **Handler Examples**: `src/langnet/execution/handlers/diogenes.py`
- **Storage Code**: `src/langnet/storage/`

---

## Questions & Clarifications

For implementation questions:
1. Review handler examples in `src/langnet/execution/handlers/`
2. Check storage usage in `src/langnet/storage/`
3. See working flow in `.justscripts/triples_dump.py`

For architecture questions:
1. Consult: `docs/plans/active/v2-implementation-master-plan.md`
2. Review: `docs/plans/active/infra/tool-plan-execution-to-claims.md`

---

**Status**: Ready for implementation
**Next Action**: Start with Task 1 (Persistent Storage)
