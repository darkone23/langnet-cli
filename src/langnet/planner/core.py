from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass

import orjson
from google.protobuf.json_format import MessageToDict
from query_spec import (
    CanonicalCandidate,
    LanguageHint,
    NormalizedQuery,
    PlanDependency,
    ToolCallSpec,
    ToolPlan,
    ToolStage,
)

from langnet.heritage.config import heritage_config
from langnet.heritage.velthuis_converter import to_heritage_velthuis


@dataclass(slots=True)
class CallOptions:
    expected: str
    priority: int
    optional: bool
    stage: ToolStage.ValueType


def _opts(
    *, expected: str, priority: int, optional: bool, stage: ToolStage.ValueType
) -> CallOptions:
    return CallOptions(expected=expected, priority=priority, optional=optional, stage=stage)


def _make_call_params(*, params: dict[str, str], stage: ToolStage.ValueType) -> dict[str, str]:
    payload = dict(params)
    # Store stage in params as string (used by some tools)
    payload["stage"] = ToolStage.Name(stage)
    payload.setdefault("source_call_id", payload.get("source_call_id", ""))
    return payload


def _make_call(
    tool: str,
    call_id: str,
    endpoint: str,
    params: dict[str, str],
    *,
    opts: CallOptions,
) -> ToolCallSpec:
    payload = _make_call_params(params=params, stage=opts.stage)
    return ToolCallSpec(
        tool=tool,
        call_id=call_id,
        endpoint=endpoint,
        params=payload,
        expected_response_type=opts.expected,
        priority=opts.priority,
        optional=opts.optional,
        stage=opts.stage,
        source_call_id=payload.get("source_call_id", ""),
    )


@dataclass(slots=True)
class PlannerConfig:
    diogenes_endpoint: str = "http://localhost:8888/Diogenes.cgi"
    diogenes_parse_endpoint: str | None = None
    heritage_base_url: str = heritage_config.base_url
    heritage_cgi_path: str = heritage_config.cgi_path
    heritage_max_results: int = 5
    include_whitakers: bool = True
    include_cltk: bool = True
    include_cdsl: bool = True
    cdsl_dicts: tuple[str, ...] = ("mw",)
    max_candidates: int = 3


class ToolPlanner:
    """
    Build ToolPlans from normalized queries with language-specific tool calls.

    Planning operates on ONE specific canonical lemma that has already been resolved during
    normalization. Do not plan calls that resolve ambiguity. Normalization is complete before
    planning begins.
    """

    def __init__(self, config: PlannerConfig | None = None) -> None:
        self.config = config or PlannerConfig()

    def _select_single_candidate(self, normalized: NormalizedQuery) -> CanonicalCandidate:
        """Select the first non-local candidate, or first if all are local."""
        non_local = [c for c in normalized.candidates if "local" not in c.sources]
        return (non_local or list(normalized.candidates))[0]

    def select_candidate(self, normalized: NormalizedQuery) -> CanonicalCandidate:
        """
        Public helper to pick the canonical candidate we will plan against.

        This lets callers explicitly pass a candidate (e.g., a row from the
        normalization index) instead of relying on the planner to pick one.
        """
        return self._select_single_candidate(normalized)

    def build(
        self, normalized: NormalizedQuery, candidate: CanonicalCandidate | None = None
    ) -> ToolPlan:
        tool_calls: list[ToolCallSpec] = []
        dependencies: list[PlanDependency] = []

        # Select single canonical candidate
        candidate = candidate or self.select_candidate(normalized)

        if normalized.language == LanguageHint.LANGUAGE_HINT_SAN:
            calls, deps = self._build_sanskrit_calls(normalized, candidate)
        elif normalized.language == LanguageHint.LANGUAGE_HINT_LAT:
            calls, deps = self._build_latin_calls(normalized, candidate)
        elif normalized.language == LanguageHint.LANGUAGE_HINT_GRC:
            calls, deps = self._build_greek_calls(normalized, candidate)
        else:
            calls, deps = [], []
        tool_calls.extend(calls)
        dependencies.extend(deps)

        created_ms = int(time.time() * 1000)
        plan = ToolPlan(
            plan_id=f"plan-{uuid.uuid4()}",
            plan_hash="",
            query=normalized,
            tool_calls=tool_calls,
            dependencies=dependencies,
            created_at_unix_ms=created_ms,
        )
        # Compute a stable hash after the plan is assembled (plan_hash omitted from hash material).
        plan.plan_hash = stable_plan_hash(plan)
        return plan

    def _build_sanskrit_calls(
        self, normalized: NormalizedQuery, candidate
    ) -> tuple[list[ToolCallSpec], list[PlanDependency]]:
        endpoint = self._heritage_endpoint()
        calls: list[ToolCallSpec] = []
        deps: list[PlanDependency] = []

        velthuis = candidate.encodings.get("velthuis") or to_heritage_velthuis(candidate.lemma)
        velthuis = velthuis.lower()
        params = {
            "text": velthuis,
            "t": "VH",
            "max": str(self.config.heritage_max_results),
        }
        heritage_fetch_id = "heritage-1"
        calls.append(
            _make_call(
                tool="fetch.heritage",
                call_id=heritage_fetch_id,
                endpoint=endpoint,
                params=params,
                opts=_opts(
                    expected="html", priority=1, optional=False, stage=ToolStage.TOOL_STAGE_FETCH
                ),
            )
        )
        # Parse Heritage HTML → extraction
        parse_id = "heritage-parse-1"
        calls.append(
            _make_call(
                tool="extract.heritage.html",
                call_id=parse_id,
                endpoint="internal://heritage/html_extract",
                params={"source_call_id": heritage_fetch_id},
                opts=_opts(
                    expected="extraction",
                    priority=2,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_EXTRACT,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=heritage_fetch_id,
                to_call_id=parse_id,
                rationale="Parse heritage HTML after fetch",
            )
        )
        derive_id = "heritage-derive-1"
        calls.append(
            _make_call(
                tool="derive.heritage.morph",
                call_id=derive_id,
                endpoint="internal://heritage/morph_derive",
                params={"source_call_id": parse_id},
                opts=_opts(
                    expected="derivation",
                    priority=3,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_DERIVE,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=parse_id,
                to_call_id=derive_id,
                rationale="Derive morphology from parsed heritage",
            )
        )
        claim_id = "claim-heritage-1"
        calls.append(
            _make_call(
                tool="claim.heritage.morph",
                call_id=claim_id,
                endpoint="internal://claim/heritage_morph",
                params={"source_call_id": derive_id},
                opts=_opts(
                    expected="claim", priority=4, optional=True, stage=ToolStage.TOOL_STAGE_CLAIM
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=derive_id,
                to_call_id=claim_id,
                rationale="Produce morph claims from heritage derivation",
            )
        )
        if self.config.include_cdsl:
            slp1 = candidate.encodings.get("slp1") or _velthuis_to_slp1_basic(velthuis)
            for dict_id in self.config.cdsl_dicts:
                cdsl_fetch_id = f"cdsl-1-{dict_id}"
                calls.append(
                    _make_call(
                        tool="fetch.cdsl",
                        call_id=cdsl_fetch_id,
                        endpoint="duckdb",
                        params={"lemma": slp1, "dict": dict_id},
                        opts=_opts(
                            expected="duckdb",
                            priority=2,
                            optional=True,
                            stage=ToolStage.TOOL_STAGE_FETCH,
                        ),
                    )
                )
                parse_id_cdsl = f"cdsl-parse-1-{dict_id}"
                calls.append(
                    _make_call(
                        tool="extract.cdsl.xml",
                        call_id=parse_id_cdsl,
                        endpoint="internal://cdsl/xml_extract",
                        params={"source_call_id": cdsl_fetch_id},
                        opts=_opts(
                            expected="extraction",
                            priority=3,
                            optional=True,
                            stage=ToolStage.TOOL_STAGE_EXTRACT,
                        ),
                    )
                )
                deps.append(
                    PlanDependency(
                        from_call_id=cdsl_fetch_id,
                        to_call_id=parse_id_cdsl,
                        rationale="Parse CDSL XML after fetch",
                    )
                )
                derive_id_cdsl = f"cdsl-derive-1-{dict_id}"
                calls.append(
                    _make_call(
                        tool="derive.cdsl.sense",
                        call_id=derive_id_cdsl,
                        endpoint="internal://cdsl/sense_derive",
                        params={"source_call_id": parse_id_cdsl},
                        opts=_opts(
                            expected="derivation",
                            priority=4,
                            optional=True,
                            stage=ToolStage.TOOL_STAGE_DERIVE,
                        ),
                    )
                )
                deps.append(
                    PlanDependency(
                        from_call_id=parse_id_cdsl,
                        to_call_id=derive_id_cdsl,
                        rationale="Derive senses from parsed CDSL XML",
                    )
                )
                claim_id_cdsl = f"claim-cdsl-1-{dict_id}"
                calls.append(
                    _make_call(
                        tool="claim.cdsl.sense",
                        call_id=claim_id_cdsl,
                        endpoint="internal://claim/cdsl_sense",
                        params={"source_call_id": derive_id_cdsl},
                        opts=_opts(
                            expected="claim",
                            priority=5,
                            optional=True,
                            stage=ToolStage.TOOL_STAGE_CLAIM,
                        ),
                    )
                )
                deps.append(
                    PlanDependency(
                        from_call_id=derive_id_cdsl,
                        to_call_id=claim_id_cdsl,
                        rationale="Produce claim from CDSL sense derivation",
                    )
                )
        return calls, deps

    def _heritage_endpoint(self) -> str:
        base = self.config.heritage_base_url.rstrip("/")
        cgi = self.config.heritage_cgi_path.strip("/")
        return f"{base}/{cgi}/sktreader"

    def _parse_endpoint(self) -> str:
        if self.config.diogenes_parse_endpoint:
            return self.config.diogenes_parse_endpoint
        base = self.config.diogenes_endpoint
        if base.endswith("Diogenes.cgi"):
            return base.replace("Diogenes.cgi", "Perseus.cgi")
        return base

    def _diogenes_lang(self, normalized: NormalizedQuery) -> str:
        if normalized.language == LanguageHint.LANGUAGE_HINT_GRC:
            return "grk"
        if normalized.language == LanguageHint.LANGUAGE_HINT_LAT:
            return "lat"
        return "lat"

    def _build_latin_calls(
        self, normalized: NormalizedQuery, candidate
    ) -> tuple[list[ToolCallSpec], list[PlanDependency]]:
        calls: list[ToolCallSpec] = []
        deps: list[PlanDependency] = []
        base = self._parse_endpoint()

        # Use canonical lemma from the single candidate
        query_value = candidate.lemma.lower()
        lang_param = self._diogenes_lang(normalized)

        # Parse → extract → derive → claim pipeline for dictionary and morphological analysis
        parse_params = {
            "do": "parse",
            "lang": lang_param,
            "q": query_value,
        }
        dio_fetch_id = "diogenes-parse-1"
        calls.append(
            _make_call(
                tool="fetch.diogenes",
                call_id=dio_fetch_id,
                endpoint=base,
                params=parse_params,
                opts=_opts(
                    expected="html", priority=1, optional=False, stage=ToolStage.TOOL_STAGE_FETCH
                ),
            )
        )
        dio_parse_id = "diogenes-parse-extract-1"
        calls.append(
            _make_call(
                tool="extract.diogenes.html",
                call_id=dio_parse_id,
                endpoint="internal://diogenes/html_extract",
                params={"source_call_id": dio_fetch_id},
                opts=_opts(
                    expected="extraction",
                    priority=2,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_EXTRACT,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=dio_fetch_id,
                to_call_id=dio_parse_id,
                rationale="Parse diogenes HTML after fetch",
            )
        )
        dio_derive_id = "diogenes-derive-1"
        calls.append(
            _make_call(
                tool="derive.diogenes.morph",
                call_id=dio_derive_id,
                endpoint="internal://diogenes/morph_derive",
                params={"source_call_id": dio_parse_id},
                opts=_opts(
                    expected="derivation",
                    priority=3,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_DERIVE,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=dio_parse_id,
                to_call_id=dio_derive_id,
                rationale="Derive morphology from diogenes parse extraction",
            )
        )
        dio_claim_id = "claim-diogenes-1"
        calls.append(
            _make_call(
                tool="claim.diogenes.morph",
                call_id=dio_claim_id,
                endpoint="internal://claim/diogenes_morph",
                params={"source_call_id": dio_derive_id},
                opts=_opts(
                    expected="claim", priority=4, optional=True, stage=ToolStage.TOOL_STAGE_CLAIM
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=dio_derive_id,
                to_call_id=dio_claim_id,
                rationale="Produce morph claims from diogenes derivation",
            )
        )
        # Include whitakers calls as before
        if self.config.include_whitakers:
            ww_fetch_id = "whitakers-1"
            calls.append(
                _make_call(
                    tool="fetch.whitakers",
                    call_id=ww_fetch_id,
                    endpoint="whitakers-words",
                    params={"word": query_value},
                    opts=_opts(
                        expected="text", priority=2, optional=True, stage=ToolStage.TOOL_STAGE_FETCH
                    ),
                )
            )
            ww_parse_id = "whitakers-extract-1"
            calls.append(
                _make_call(
                    tool="extract.whitakers.lines",
                    call_id=ww_parse_id,
                    endpoint="internal://whitakers/line_extract",
                    params={"source_call_id": ww_fetch_id},
                    opts=_opts(
                        expected="extraction",
                        priority=3,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_EXTRACT,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=ww_fetch_id,
                    to_call_id=ww_parse_id,
                    rationale="Parse Whitaker lines after fetch",
                )
            )
            ww_derive_id = "whitakers-derive-1"
            calls.append(
                _make_call(
                    tool="derive.whitakers.facts",
                    call_id=ww_derive_id,
                    endpoint="internal://whitakers/fact_derive",
                    params={"source_call_id": ww_parse_id},
                    opts=_opts(
                        expected="derivation",
                        priority=4,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_DERIVE,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=ww_parse_id,
                    to_call_id=ww_derive_id,
                    rationale="Derive Whitaker facts after line extraction",
                )
            )
            claim_ww_id = "claim-whitakers-1"
            calls.append(
                _make_call(
                    tool="claim.whitakers",
                    call_id=claim_ww_id,
                    endpoint="internal://claim/whitakers",
                    params={"source_call_id": ww_derive_id},
                    opts=_opts(
                        expected="claim",
                        priority=5,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_CLAIM,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=ww_derive_id,
                    to_call_id=claim_ww_id,
                    rationale="Produce claims from Whitaker derivation",
                )
            )
        # Include CLTK calls as before
        if self.config.include_cltk:
            cltk_fetch_id = "cltk-ipa-1"
            calls.append(
                _make_call(
                    tool="fetch.cltk",
                    call_id=cltk_fetch_id,
                    endpoint="cltk://ipa/lat",
                    params={"word": query_value, "language": "lat"},
                    opts=_opts(
                        expected="json", priority=3, optional=True, stage=ToolStage.TOOL_STAGE_FETCH
                    ),
                )
            )
            cltk_derive_id = "cltk-derive-1"
            calls.append(
                _make_call(
                    tool="derive.cltk.ipa",
                    call_id=cltk_derive_id,
                    endpoint="internal://cltk/ipa_derive",
                    params={"source_call_id": cltk_fetch_id},
                    opts=_opts(
                        expected="derivation",
                        priority=4,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_DERIVE,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=cltk_fetch_id,
                    to_call_id=cltk_derive_id,
                    rationale="Derive IPA from CLTK fetch",
                )
            )
            claim_cltk_id = "claim-cltk-1"
            calls.append(
                _make_call(
                    tool="claim.cltk.ipa",
                    call_id=claim_cltk_id,
                    endpoint="internal://claim/cltk_ipa",
                    params={"source_call_id": cltk_derive_id},
                    opts=_opts(
                        expected="claim",
                        priority=5,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_CLAIM,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=cltk_derive_id,
                    to_call_id=claim_cltk_id,
                    rationale="Produce claims from CLTK IPA derivation",
                )
            )
        return calls, deps

    def _build_greek_calls(
        self, normalized: NormalizedQuery, candidate
    ) -> tuple[list[ToolCallSpec], list[PlanDependency]]:
        calls: list[ToolCallSpec] = []
        deps: list[PlanDependency] = []

        # ONLY use the Diogenes parse endpoint (NO word_list)
        base = self._parse_endpoint()

        # Use the pre-resolved canonical form (accentless or betacode)
        query_value = candidate.encodings.get("accentless") or candidate.lemma
        if not query_value:
            query_value = normalized.original.lower()
        query_value = query_value.lower()
        lang_param = self._diogenes_lang(normalized)

        # Include parse → extract → derive → claim pipeline
        parse_params = {
            "do": "parse",
            "lang": lang_param,
            "q": query_value,
        }
        fetch_parse_id = "diogenes-parse-1"
        calls.append(
            _make_call(
                tool="fetch.diogenes",
                call_id=fetch_parse_id,
                endpoint=base,
                params=parse_params,
                opts=_opts(
                    expected="html", priority=1, optional=False, stage=ToolStage.TOOL_STAGE_FETCH
                ),
            )
        )
        parse_extract_id = "diogenes-parse-extract-1"
        calls.append(
            _make_call(
                tool="extract.diogenes.html",
                call_id=parse_extract_id,
                endpoint="internal://diogenes/html_extract",
                params={"source_call_id": fetch_parse_id},
                opts=_opts(
                    expected="extraction",
                    priority=2,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_EXTRACT,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=fetch_parse_id,
                to_call_id=parse_extract_id,
                rationale="Parse diogenes parse HTML",
            )
        )
        derive_morph_id = "diogenes-morph-derive-1"
        calls.append(
            _make_call(
                tool="derive.diogenes.morph",
                call_id=derive_morph_id,
                endpoint="internal://diogenes/morph_derive",
                params={"source_call_id": parse_extract_id},
                opts=_opts(
                    expected="derivation",
                    priority=3,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_DERIVE,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=parse_extract_id,
                to_call_id=derive_morph_id,
                rationale="Derive morph facts from diogenes parse extraction",
            )
        )
        derive_cite_id = "diogenes-citation-derive-1"
        calls.append(
            _make_call(
                tool="derive.diogenes.citation",
                call_id=derive_cite_id,
                endpoint="internal://diogenes/citation_derive",
                params={"source_call_id": parse_extract_id},
                opts=_opts(
                    expected="derivation",
                    priority=4,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_DERIVE,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=parse_extract_id,
                to_call_id=derive_cite_id,
                rationale="Extract citation refs from diogenes parse",
            )
        )
        claim_morph_id = "claim-diogenes-morph-1"
        calls.append(
            _make_call(
                tool="claim.diogenes.morph",
                call_id=claim_morph_id,
                endpoint="internal://claim/diogenes_morph",
                params={"source_call_id": derive_morph_id},
                opts=_opts(
                    expected="claim", priority=5, optional=True, stage=ToolStage.TOOL_STAGE_CLAIM
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=derive_morph_id,
                to_call_id=claim_morph_id,
                rationale="Produce morph claims from diogenes derivation",
            )
        )
        claim_cite_id = "claim-diogenes-citation-1"
        calls.append(
            _make_call(
                tool="claim.diogenes.citation",
                call_id=claim_cite_id,
                endpoint="internal://claim/diogenes_citation",
                params={"source_call_id": derive_cite_id},
                opts=_opts(
                    expected="claim", priority=6, optional=True, stage=ToolStage.TOOL_STAGE_CLAIM
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=derive_cite_id,
                to_call_id=claim_cite_id,
                rationale="Produce citation claims from diogenes derivation",
            )
        )

        # Include CTS hydration
        cts_fetch_id = "cts-fetch-1"
        calls.append(
            _make_call(
                tool="fetch.cts_index",
                call_id=cts_fetch_id,
                endpoint="duckdb://cts_index",
                params={"source_call_id": derive_cite_id},
                opts=_opts(
                    expected="json", priority=7, optional=True, stage=ToolStage.TOOL_STAGE_FETCH
                ),
            )
        )
        cts_extract_id = "cts-extract-1"
        calls.append(
            _make_call(
                tool="extract.cts_index.json",
                call_id=cts_extract_id,
                endpoint="internal://cts_index/json_extract",
                params={"source_call_id": cts_fetch_id},
                opts=_opts(
                    expected="extraction",
                    priority=8,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_EXTRACT,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=cts_fetch_id,
                to_call_id=cts_extract_id,
                rationale="Extract CTS payload after fetch",
            )
        )
        cts_derive_id = "cts-derive-1"
        calls.append(
            _make_call(
                tool="derive.cts_index.citation",
                call_id=cts_derive_id,
                endpoint="internal://cts_index/citation_derive",
                params={"source_call_id": cts_extract_id},
                opts=_opts(
                    expected="derivation",
                    priority=9,
                    optional=True,
                    stage=ToolStage.TOOL_STAGE_DERIVE,
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=cts_extract_id,
                to_call_id=cts_derive_id,
                rationale="Derive citation data after CTS extract",
            )
        )
        claim_cts_id = "claim-cts-1"
        calls.append(
            _make_call(
                tool="claim.cts_index",
                call_id=claim_cts_id,
                endpoint="internal://claim/cts_index",
                params={"source_call_id": cts_derive_id},
                opts=_opts(
                    expected="claim", priority=10, optional=True, stage=ToolStage.TOOL_STAGE_CLAIM
                ),
            )
        )
        deps.append(
            PlanDependency(
                from_call_id=cts_derive_id,
                to_call_id=claim_cts_id,
                rationale="Produce claims from CTS derivation",
            )
        )

        # Include CLTK as before
        if self.config.include_cltk:
            cltk_fetch_id = "cltk-ipa-1"
            calls.append(
                _make_call(
                    tool="fetch.cltk",
                    call_id=cltk_fetch_id,
                    endpoint="cltk://ipa/grc",
                    params={"word": query_value, "language": "grc"},
                    opts=_opts(
                        expected="json", priority=3, optional=True, stage=ToolStage.TOOL_STAGE_FETCH
                    ),
                )
            )
            cltk_derive_id = "cltk-derive-1"
            calls.append(
                _make_call(
                    tool="derive.cltk.ipa",
                    call_id=cltk_derive_id,
                    endpoint="internal://cltk/ipa_derive",
                    params={"source_call_id": cltk_fetch_id},
                    opts=_opts(
                        expected="derivation",
                        priority=4,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_DERIVE,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=cltk_fetch_id,
                    to_call_id=cltk_derive_id,
                    rationale="Derive IPA from CLTK fetch",
                )
            )
            claim_cltk_id = "claim-cltk-1"
            calls.append(
                _make_call(
                    tool="claim.cltk.ipa",
                    call_id=claim_cltk_id,
                    endpoint="internal://claim/cltk_ipa",
                    params={"source_call_id": cltk_derive_id},
                    opts=_opts(
                        expected="claim",
                        priority=5,
                        optional=True,
                        stage=ToolStage.TOOL_STAGE_CLAIM,
                    ),
                )
            )
            deps.append(
                PlanDependency(
                    from_call_id=cltk_derive_id,
                    to_call_id=claim_cltk_id,
                    rationale="Produce claims from CLTK IPA derivation",
                )
            )
        return calls, deps


def _velthuis_to_slp1_basic(text: str) -> str:
    """
    Minimal Velthuis → SLP1 map for Sanskrit lookups; mirrors the normalizer fallback.
    """
    replacements = [
        ("aa", "A"),
        ("ii", "I"),
        ("uu", "U"),
        ("~n", "Y"),
        (".rr", "F"),
        (".r", "f"),
        (".ll", "X"),
        (".l", "x"),
        (".n", "R"),
        (".t", "w"),
        (".d", "q"),
        (".s", "z"),
        ("'s", "S"),
    ]
    out = text
    for old, new in replacements:
        out = out.replace(old, new)
    return out


def stable_plan_hash(plan: ToolPlan) -> str:
    """
    Compute a stable hash for a ToolPlan by omitting volatile fields
    (plan_id, plan_hash, created_at_unix_ms).
    """
    data = MessageToDict(plan)
    data["plan_id"] = ""
    data["plan_hash"] = ""
    data["created_at_unix_ms"] = 0
    # Sort tool_calls/dependencies for stability
    data["tool_calls"] = sorted(
        [
            {
                **c,
                "params": dict(c.get("params") or {}),
            }
            for c in data.get("tool_calls", [])
        ],
        key=lambda c: str(c.get("call_id", "")),
    )
    data["dependencies"] = sorted(
        data.get("dependencies", []),
        key=lambda d: (str(d.get("from_call_id", "")), str(d.get("to_call_id", ""))),
    )
    material = orjson.dumps(data, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(material).hexdigest()[:16]
