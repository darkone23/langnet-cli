from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import duckdb
from query_spec import ExecutedPlan, ToolResponseRef

from langnet.clients.base import RawResponseEffect
from langnet.execution.effects import ClaimEffect, DerivationEffect, ExtractionEffect
from langnet.storage.claim_index import ClaimIndex
from langnet.storage.db import connect_duckdb
from langnet.storage.derivation_index import DerivationIndex
from langnet.storage.effects_index import RawResponseIndex, apply_schema
from langnet.storage.extraction_index import ExtractionIndex
from langnet.storage.plan_index import PlanResponseIndex


@contextmanager
def _locked_rw_connection(path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_duckdb(path, read_only=False, lock=True) as conn:
        apply_schema(conn)
        yield conn


@dataclass(frozen=True, slots=True)
class PathRawResponseIndex:
    """Path-backed raw response index with per-operation DuckDB lock scope."""

    path: Path

    def get(self, response_id: str) -> RawResponseEffect | None:
        if not self.path.exists():
            return None
        with _locked_rw_connection(self.path) as conn:
            return RawResponseIndex(conn).get(response_id)

    def store(self, effect: RawResponseEffect) -> ToolResponseRef:
        with _locked_rw_connection(self.path) as conn:
            return RawResponseIndex(conn).store(effect)


@dataclass(frozen=True, slots=True)
class PathExtractionIndex:
    """Path-backed extraction index with per-operation DuckDB lock scope."""

    path: Path

    def store_effect(self, effect: ExtractionEffect) -> str:
        with _locked_rw_connection(self.path) as conn:
            return ExtractionIndex(conn).store_effect(effect)


@dataclass(frozen=True, slots=True)
class PathDerivationIndex:
    """Path-backed derivation index with per-operation DuckDB lock scope."""

    path: Path

    def store_effect(self, effect: DerivationEffect) -> str:
        with _locked_rw_connection(self.path) as conn:
            return DerivationIndex(conn).store_effect(effect)


@dataclass(frozen=True, slots=True)
class PathClaimIndex:
    """Path-backed claim index with per-operation DuckDB lock scope."""

    path: Path

    def store_effect(self, effect: ClaimEffect) -> str:
        with _locked_rw_connection(self.path) as conn:
            return ClaimIndex(conn).store_effect(effect)


@dataclass(frozen=True, slots=True)
class PathPlanResponseIndex:
    """Path-backed plan response index with per-operation DuckDB lock scope."""

    path: Path

    def get(self, plan_hash: str) -> ExecutedPlan | None:
        if not self.path.exists():
            return None
        with _locked_rw_connection(self.path) as conn:
            return PlanResponseIndex(conn).get(plan_hash)

    def upsert(
        self, plan_hash: str, plan_id: str, response_refs: Sequence[ToolResponseRef]
    ) -> None:
        with _locked_rw_connection(self.path) as conn:
            PlanResponseIndex(conn).upsert(
                plan_hash=plan_hash,
                plan_id=plan_id,
                response_refs=response_refs,
            )
