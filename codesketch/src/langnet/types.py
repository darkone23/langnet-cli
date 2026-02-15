"""Shared typing utilities for JSON-like payloads."""

from __future__ import annotations

from typing import TypeAlias

JSONScalar = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONMapping: TypeAlias = dict[str, JSONValue]
