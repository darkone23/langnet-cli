from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import orjson


class LanguageHint(Enum):
    LANGUAGE_HINT_UNSPECIFIED = 0
    LANGUAGE_HINT_LAT = 1
    LANGUAGE_HINT_GRC = 2
    LANGUAGE_HINT_SAN = 3
    LAT = LANGUAGE_HINT_LAT
    GRC = LANGUAGE_HINT_GRC
    SAN = LANGUAGE_HINT_SAN

    @classmethod
    def from_value(cls, value: Any) -> LanguageHint:
        result = cls.LANGUAGE_HINT_UNSPECIFIED
        if isinstance(value, LanguageHint):
            result = value
        elif isinstance(value, str):
            key = value.strip().upper()
            if key:
                if not key.startswith("LANGUAGE_HINT_"):
                    key = f"LANGUAGE_HINT_{key}"
                with suppress(KeyError):
                    result = cls[key]
        elif isinstance(value, int):
            with suppress(ValueError):
                result = cls(value)
        return result

    def json_value(self) -> str:
        return self.name.removeprefix("LANGUAGE_HINT_")


def _dump(data: Any) -> str:
    return orjson.dumps(data, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def _load(data: str | bytes | bytearray) -> Any:
    return orjson.loads(data)


@dataclass(slots=True)
class CanonicalCandidate:
    lemma: str = ""
    encodings: dict[str, str] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lemma": self.lemma,
            "encodings": dict(self.encodings),
            "sources": list(self.sources),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CanonicalCandidate:
        data = data or {}
        return cls(
            lemma=data.get("lemma", "") or "",
            encodings=dict(data.get("encodings") or {}),
            sources=list(data.get("sources") or []),
        )


@dataclass(slots=True)
class NormalizationStep:
    operation: str = ""
    input: str = ""
    output: str = ""
    tool: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "input": self.input,
            "output": self.output,
            "tool": self.tool,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NormalizationStep:
        data = data or {}
        return cls(
            operation=data.get("operation", "") or "",
            input=data.get("input", "") or "",
            output=data.get("output", "") or "",
            tool=data.get("tool", "") or "",
        )


@dataclass(slots=True)
class NormalizedQuery:
    original: str = ""
    language: LanguageHint = LanguageHint.LANGUAGE_HINT_UNSPECIFIED
    candidates: list[CanonicalCandidate] = field(default_factory=list)
    normalizations: list[NormalizationStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "language": self.language.json_value(),
            "candidates": [c.to_dict() for c in self.candidates],
            "normalizations": [n.to_dict() for n in self.normalizations],
        }

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NormalizedQuery:
        data = data or {}
        language = LanguageHint.from_value(data.get("language"))
        return cls(
            original=data.get("original", "") or "",
            language=language,
            candidates=[CanonicalCandidate.from_dict(c) for c in data.get("candidates") or []],
            normalizations=[
                NormalizationStep.from_dict(n) for n in data.get("normalizations") or []
            ],
        )

    @classmethod
    def from_json(cls, data: str | bytes | bytearray) -> NormalizedQuery:
        return cls.from_dict(_load(data))


@dataclass(slots=True)
class ToolCallSpec:
    tool: str = ""
    call_id: str = ""
    endpoint: str = ""
    params: dict[str, str] | None = None
    expected_response_type: str = ""
    priority: int = 0
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "call_id": self.call_id,
            "endpoint": self.endpoint,
            "params": dict(self.params or {}),
            "expected_response_type": self.expected_response_type,
            "priority": int(self.priority),
            "optional": bool(self.optional),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ToolCallSpec:
        data = data or {}
        return cls(
            tool=data.get("tool", "") or "",
            call_id=data.get("call_id", "") or "",
            endpoint=data.get("endpoint", "") or "",
            params=dict(data.get("params") or {}),
            expected_response_type=data.get("expected_response_type", "") or "",
            priority=int(data.get("priority") or 0),
            optional=bool(data.get("optional") or False),
        )


@dataclass(slots=True)
class PlanDependency:
    from_call_id: str = ""
    to_call_id: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_call_id": self.from_call_id,
            "to_call_id": self.to_call_id,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PlanDependency:
        data = data or {}
        return cls(
            from_call_id=data.get("from_call_id", "") or "",
            to_call_id=data.get("to_call_id", "") or "",
            rationale=data.get("rationale", "") or "",
        )


@dataclass(slots=True)
class ToolPlan:
    plan_id: str = ""
    plan_hash: str = ""
    query: NormalizedQuery | None = None
    tool_calls: list[ToolCallSpec] = field(default_factory=list)
    dependencies: list[PlanDependency] = field(default_factory=list)
    created_at_unix_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "query": self.query.to_dict() if self.query else None,
            "tool_calls": [c.to_dict() for c in self.tool_calls],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "created_at_unix_ms": int(self.created_at_unix_ms),
        }

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ToolPlan:
        data = data or {}
        return cls(
            plan_id=data.get("plan_id", "") or "",
            plan_hash=data.get("plan_hash", "") or "",
            query=NormalizedQuery.from_dict(data.get("query")) if data.get("query") else None,
            tool_calls=[ToolCallSpec.from_dict(c) for c in data.get("tool_calls") or []],
            dependencies=[PlanDependency.from_dict(d) for d in data.get("dependencies") or []],
            created_at_unix_ms=int(data.get("created_at_unix_ms") or 0),
        )

    @classmethod
    def from_json(cls, data: str | bytes | bytearray) -> ToolPlan:
        return cls.from_dict(_load(data))


@dataclass(slots=True)
class ToolResponseRef:
    tool: str = ""
    call_id: str = ""
    response_id: str = ""
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "call_id": self.call_id,
            "response_id": self.response_id,
            "cached": bool(self.cached),
        }

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ToolResponseRef:
        data = data or {}
        return cls(
            tool=data.get("tool", "") or "",
            call_id=data.get("call_id", "") or "",
            response_id=data.get("response_id", "") or "",
            cached=bool(data.get("cached") or False),
        )

    @classmethod
    def from_json(cls, data: str | bytes | bytearray) -> ToolResponseRef:
        return cls.from_dict(_load(data))


@dataclass(slots=True)
class ExecutedPlan:
    plan_id: str = ""
    plan_hash: str = ""
    responses: list[ToolResponseRef] = field(default_factory=list)
    execution_time_ms: int = 0
    from_cache: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "responses": [r.to_dict() for r in self.responses],
            "execution_time_ms": int(self.execution_time_ms),
            "from_cache": bool(self.from_cache),
        }

    def to_json(self) -> str:
        return _dump(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ExecutedPlan:
        data = data or {}
        return cls(
            plan_id=data.get("plan_id", "") or "",
            plan_hash=data.get("plan_hash", "") or "",
            responses=[ToolResponseRef.from_dict(r) for r in data.get("responses") or []],
            execution_time_ms=int(data.get("execution_time_ms") or 0),
            from_cache=bool(data.get("from_cache") or False),
        )

    @classmethod
    def from_json(cls, data: str | bytes | bytearray) -> ExecutedPlan:
        return cls.from_dict(_load(data))


__all__: list[str] = [
    "CanonicalCandidate",
    "ExecutedPlan",
    "LanguageHint",
    "NormalizationStep",
    "NormalizedQuery",
    "PlanDependency",
    "ToolCallSpec",
    "ToolPlan",
    "ToolResponseRef",
]
