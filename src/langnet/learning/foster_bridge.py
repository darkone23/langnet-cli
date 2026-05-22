from __future__ import annotations

from dataclasses import asdict, dataclass, field

from langnet.foster_ossa.essentials import FosterEssential, default_foster_essentials
from langnet.learning.grammar_concepts import get_grammar_concept

FOSTER_BRIDGE_SCHEMA_VERSION = "langnet.foster_bridge.v1"


@dataclass(frozen=True)
class FosterBridge:
    id: str
    foster_terms: list[str]
    status: str
    concept_ids: list[str]
    related_concept_ids: list[str] = field(default_factory=list)
    plain_english: str = ""
    rationale: str = ""
    source_refs: list[str] = field(default_factory=list)
    summary_refs: list[str] = field(default_factory=list)
    learner_action: str = ""
    product_use: str = ""
    morphology_predicates: list[str] = field(default_factory=list)
    reader_example_queries: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    review_docs: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


def load_foster_bridges() -> dict[str, FosterBridge]:
    return {bridge.id: bridge for bridge in _BRIDGES}


def foster_bridges_for_concept(
    concept_id: str,
    *,
    include_related: bool = True,
) -> list[FosterBridge]:
    bridges = [
        bridge
        for bridge in _BRIDGES
        if concept_id in bridge.concept_ids
        or (include_related and concept_id in bridge.related_concept_ids)
    ]
    return sorted(bridges, key=lambda item: (item.status != "promoted_match", item.id))


def get_foster_bridge(query: str) -> FosterBridge:
    normalized = _normalize_bridge_query(query)
    bridges = load_foster_bridges()
    if normalized in bridges:
        return bridges[normalized]
    for bridge in bridges.values():
        if normalized in {_normalize_bridge_query(term) for term in bridge.foster_terms}:
            return bridge
    raise KeyError(f"unknown Foster bridge: {query}")


def foster_bridge_payload(bridge: FosterBridge) -> dict[str, object]:
    payload = asdict(bridge)
    payload["concepts"] = [
        _concept_summary(concept_id)
        for concept_id in [*bridge.concept_ids, *bridge.related_concept_ids]
    ]
    return payload


def foster_bridge_summary_payload(bridge: FosterBridge) -> dict[str, object]:
    return asdict(bridge)


def foster_bridge_learning_payload(bridge: FosterBridge) -> dict[str, object]:
    return {
        "id": bridge.id,
        "status": bridge.status,
        "foster_terms": list(bridge.foster_terms),
        "concept_ids": list(bridge.concept_ids),
        "related_concept_ids": list(bridge.related_concept_ids),
        "plain_english": bridge.plain_english,
        "source_refs": list(bridge.source_refs),
    }


def _concept_summary(concept_id: str) -> dict[str, object]:
    concept = get_grammar_concept(concept_id)
    return {
        "id": concept.id,
        "kind": concept.kind,
        "foster_gateway": concept.foster_gateway,
        "plain_english": concept.plain_english,
        "traditional": dict(concept.traditional),
    }


def _normalize_bridge_query(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


_REVIEW_DOCS = [
    "docs/reference/foster-ossa/CORE_FUNCTION_BRIDGE.md",
    "docs/reference/foster-ossa/TAXONOMY_AUDIT.md",
    "docs/reference/foster-ossa/DIDACTIC_SYNTHESIS.md",
    "docs/reference/foster-ossa/FOSTER_ESSENTIALS.md",
]

_PLAIN_ENGLISH = {
    "of-possession": "Foster/Ossa possession or relation maps to the genitive concept.",
    "to-for-from": "Foster/Ossa recipient, benefit, and reference functions map to dative.",
    "object-form": "Foster/Ossa object form maps to the receiving/object case function.",
    "function-of-address": "Foster/Ossa address function maps to direct address or vocative.",
    "location-function": "Foster/Ossa location function maps to the location/setting concept.",
    "subject-form": "Foster/Ossa subject form maps to naming or subject function.",
    "by-with-from-in": (
        "A Foster/Ossa learner bundle for by, with, from, and in relationships; "
        "not a single universal case concept."
    ),
}

_RATIONALE = {
    "of-possession": (
        "The Foster/Ossa essentials pack codifies of-possession for the same "
        "learner function LangNet exposes as Possessing Function."
    ),
    "to-for-from": (
        "The existing dative concept already teaches To-For Function and carries "
        "traditional Greek, Latin, and Sanskrit terms."
    ),
    "object-form": (
        "The essentials pack uses object form as the learner-facing gateway for "
        "what LangNet calls Receiving Function."
    ),
    "function-of-address": (
        "The registry defines vocative as Calling Function, matching the "
        "Foster/Ossa address label without treating it as subject or object."
    ),
    "location-function": (
        "The existing locative concept teaches In-At Function while preserving "
        "language-specific expression differences."
    ),
    "subject-form": (
        "The bridge is intentionally limited to subject form phrases, not every "
        "bare mention of subject."
    ),
    "by-with-from-in": (
        "The essentials pack warns that this bundle overlaps ablative, "
        "instrumental, and locative. Collapsing it into only ablative would "
        "hide useful cross-language distinctions."
    ),
}

_NEXT_ACTIONS = {
    "of-possession": [
        "Attach reader examples for possession and broader relation uses.",
        "Keep genitive subtypes such as partitive/objective as later refinements.",
    ],
    "to-for-from": [
        "Add examples distinguishing recipient, benefit, reference, and possession-like dative.",
    ],
    "object-form": [
        "Keep ordinary object, motion-goal, and accusative-infinitive uses distinguishable.",
    ],
    "function-of-address": [
        "Attach reader examples where the addressed noun is separate from the clause.",
    ],
    "location-function": [
        "Pair true locative evidence with Latin and Greek prepositional/location expressions.",
    ],
    "subject-form": [
        "Keep syntactic subject and nominative morphology separate in later sentence annotation.",
    ],
    "by-with-from-in": [
        "Design a Foster aggregate concept that links to ablative, instrumental, and locative.",
        "Attach Latin prepositional and no-preposition examples before product display.",
    ],
}

_EXTRA_ALIASES = {
    "of-possession": ["form of-possession"],
    "location-function": ["place where"],
}


def _bridge_from_essential(essential: FosterEssential) -> FosterBridge:
    concept_ids = list(essential.concept_ids)
    related_concept_ids: list[str] = []
    status = "promoted_match" if essential.status == "codified" else essential.status
    if essential.status == "aggregate_candidate":
        related_concept_ids = concept_ids
        concept_ids = []
    return FosterBridge(
        id=essential.id,
        foster_terms=_foster_terms_for_essential(essential),
        status=status,
        concept_ids=concept_ids,
        related_concept_ids=related_concept_ids,
        plain_english=_PLAIN_ENGLISH[essential.id],
        rationale=_RATIONALE[essential.id],
        source_refs=list(essential.source_refs),
        summary_refs=list(essential.summary_refs),
        learner_action=essential.learner_action,
        product_use=essential.product_use,
        morphology_predicates=list(essential.morphology_predicates),
        reader_example_queries=list(essential.reader_example_queries),
        caveats=list(essential.caveats),
        review_docs=_REVIEW_DOCS,
        next_actions=_NEXT_ACTIONS[essential.id],
    )


def _foster_terms_for_essential(essential: FosterEssential) -> list[str]:
    aliases = [essential.id, *essential.foster_terms, *_EXTRA_ALIASES.get(essential.id, [])]
    seen: set[str] = set()
    terms: list[str] = []
    for alias in aliases:
        key = _normalize_bridge_query(alias)
        if key not in seen:
            seen.add(key)
            terms.append(alias)
    return terms


_BRIDGES = [_bridge_from_essential(essential) for essential in default_foster_essentials()]
