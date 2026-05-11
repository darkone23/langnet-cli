"""Paradigm resolution and generation support."""

from langnet.paradigm.grammar import (
    FunctionalAnalysis,
    NativeAnalysis,
    ParadigmRequest,
    ParadigmResolutionCandidate,
    ParadigmResolutionPayload,
)
from langnet.paradigm.models import ParadigmBlock, ParadigmForm, ParadigmPayload, ParadigmSlot

__all__ = [
    "FunctionalAnalysis",
    "NativeAnalysis",
    "ParadigmBlock",
    "ParadigmForm",
    "ParadigmPayload",
    "ParadigmRequest",
    "ParadigmResolutionCandidate",
    "ParadigmResolutionPayload",
    "ParadigmSlot",
]
