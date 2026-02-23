from __future__ import annotations

from collections import defaultdict

from langnet.execution.executor import ToolRegistry
from langnet.execution.handlers import diogenes as diogenes_handlers
from langnet.execution.handlers import cltk as cltk_handlers
from langnet.execution.handlers import spacy as spacy_handlers
from langnet.execution.handlers import whitakers as whitakers_handlers
from langnet.execution.handlers import heritage as heritage_handlers
from langnet.execution.handlers import cdsl as cdsl_handlers
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
    # spaCy Greek morphology (fallback when available)
    extract["extract.spacy.json"] = spacy_handlers.extract_spacy
    derive["derive.spacy.morph"] = spacy_handlers.derive_spacy
    claim["claim.spacy.morph"] = spacy_handlers.claim_spacy
    # Heritage handlers
    extract["extract.heritage.html"] = heritage_handlers.extract_html
    derive["derive.heritage.morph"] = heritage_handlers.derive_morph
    claim["claim.heritage.morph"] = heritage_handlers.claim_morph
    # CDSL handlers
    extract["extract.cdsl.xml"] = cdsl_handlers.extract_xml
    derive["derive.cdsl.sense"] = cdsl_handlers.derive_sense
    claim["claim.cdsl.sense"] = cdsl_handlers.claim_sense

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
