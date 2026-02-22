from __future__ import annotations

from collections import defaultdict

from langnet.execution.executor import ToolRegistry
from langnet.execution.handlers import diogenes as diogenes_handlers
from langnet.execution.handlers import cltk as cltk_handlers
from langnet.execution.handlers import whitakers as whitakers_handlers
from langnet.execution import handlers_stub


def default_registry(use_stubs: bool = False) -> ToolRegistry:
    """
    Build a ToolRegistry with real handlers where available and stubs elsewhere.

    Currently wires diogenes handlers for extract/derive/claim and falls back to
    stubs for everything else.
    """
    extract = {}
    derive = {}
    claim = {}

    # Real diogenes handlers
    extract["extract.diogenes.html"] = diogenes_handlers.extract_html
    derive["derive.diogenes.morph"] = diogenes_handlers.derive_morph
    claim["claim.diogenes.morph"] = diogenes_handlers.claim_morph
    # Real Whitaker handlers
    extract["extract.whitakers.lines"] = whitakers_handlers.extract_lines
    derive["derive.whitakers.facts"] = whitakers_handlers.derive_facts
    claim["claim.whitakers"] = whitakers_handlers.claim_whitakers
    # CLTK handlers (Lewis/IPA)
    extract["extract.cltk.lexicon"] = cltk_handlers.extract_cltk
    derive["derive.cltk.ipa"] = cltk_handlers.derive_cltk
    claim["claim.cltk.ipa"] = cltk_handlers.claim_cltk

    if use_stubs:
        # Fallback to stub handlers for any tool not registered above.
        extract = defaultdict(lambda: handlers_stub.stub_extract, extract)
        derive = defaultdict(lambda: handlers_stub.stub_derive, derive)
        claim = defaultdict(lambda: handlers_stub.stub_claim, claim)

    return ToolRegistry(
        extract_handlers=extract,
        derive_handlers=derive,
        claim_handlers=claim,
    )
