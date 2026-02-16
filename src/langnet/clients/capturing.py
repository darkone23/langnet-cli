"""
Client wrapper for automatic raw response capture.

This module provides a transparent wrapper that intercepts RawResponseEffect
objects and automatically indexes them without changing the client interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langnet.clients.base import RawResponseEffect

if TYPE_CHECKING:
    from collections.abc import Mapping


class CapturingToolClient:
    """
    Wraps a ToolClient and automatically indexes RawResponseEffect objects.

    This makes the normalizer "just do the right thing" by capturing raw
    responses without changing how clients are used.

    Example:
        # Before: client returns RawResponseEffect
        effect = http_client.execute(call_id, endpoint, params)

        # After: wrapped client indexes automatically
        wrapped = CapturingToolClient(http_client, effects_index)
        effect = wrapped.execute(call_id, endpoint, params)  # Auto-indexed!
    """

    def __init__(
        self,
        inner_client,
        effects_index,
    ) -> None:
        self._client = inner_client
        self._index = effects_index
        self.tool = getattr(inner_client, "tool", "unknown")

    def execute(
        self,
        call_id: str,
        endpoint: str,
        params: Mapping[str, str] | None = None,
    ) -> RawResponseEffect:
        """Execute the call and automatically index the response."""
        effect = self._client.execute(call_id, endpoint, params)

        if self._index is not None:
            self._index.store(effect)

        return effect


def wrap_client_if_index(inner_client, effects_index):
    """
    Helper to optionally wrap a client with capturing behavior.

    Returns the wrapped client if an index is provided, otherwise returns
    the original client unchanged.
    """
    if effects_index is None:
        return inner_client
    return CapturingToolClient(inner_client, effects_index)
