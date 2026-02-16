from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import cast

from langnet.clients import HttpToolClient
from langnet.cltk.ipa_adapter import CLTKIPAAdapter
from langnet.diogenes.adapter import DiogenesWordListAdapter
from langnet.diogenes.parse_adapter import DiogenesParseAdapter
from langnet.heritage.client import HeritageHTTPClient
from langnet.normalizer.sanskrit import (
    ENC_ASCII,
    ENC_DEVANAGARI,
    ENC_HK,
    ENC_IAST,
    ENC_SLP1,
    ENC_VELTHUIS,
    SanscriptModule,
)
from langnet.normalizer.service import NormalizationService
from langnet.normalizer.utils import strip_accents, unique
from langnet.storage.effects_index import RawResponseIndex
from langnet.storage.extraction_index import ExtractionIndex
from langnet.whitakers.adapter import WhitakerAdapter
from query_spec import CanonicalCandidate, LanguageHint

DEVANAGARI_UNICODE_START = 0x0900
DEVANAGARI_UNICODE_END = 0x097F


@dataclass
class CanonicalLookupResult:
    normalized_forms: list[str]
    candidates: list[CanonicalCandidate] = field(default_factory=list)
    selected: CanonicalCandidate | None = None
    responses: list[str] = field(default_factory=list)
    extractions: list[str] = field(default_factory=list)


@dataclass
class LookupState:
    matches: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    responses: list[str] = field(default_factory=list)
    extractions: list[str] = field(default_factory=list)
    ipa_value: str | None = None


class CanonicalPipeline:
    """
    Minimal pipeline: normalize → hit tool(s) → collect canonical candidates and store effects.
    """

    def __init__(
        self,
        norm_service: NormalizationService,
        raw_index: RawResponseIndex,
        extraction_index: ExtractionIndex,
        diogenes_base: str = "http://localhost:8888/Diogenes.cgi",
        heritage_base: str = "http://localhost:48080/cgi-bin/skt/sktreader",
    ) -> None:
        self.norm_service = norm_service
        self.raw_index = raw_index
        self.extraction_index = extraction_index
        self.dio_client = HttpToolClient(tool="diogenes")
        self.dio_wordlist = DiogenesWordListAdapter(
            client=self.dio_client,
            raw_index=raw_index,
            extraction_index=extraction_index,
            endpoint=diogenes_base,
        )
        self.dio_parse = DiogenesParseAdapter(
            client=self.dio_client,
            raw_index=raw_index,
            extraction_index=extraction_index,
            endpoint=diogenes_base,
        )
        self.heritage_client = HeritageHTTPClient()
        self.heritage_endpoint = heritage_base
        self.whitaker = WhitakerAdapter(raw_index, extraction_index)
        self.cltk_ipa = CLTKIPAAdapter(
            service=None, raw_index=raw_index, extraction_index=extraction_index
        )

    def lookup(self, raw_query: str, language: LanguageHint) -> CanonicalLookupResult:
        norm = self.norm_service.normalize(raw_query, language)
        canonical_targets = [c.lemma for c in norm.normalized.candidates]

        state = LookupState(candidates=list(canonical_targets))

        if language == LanguageHint.GRC:
            self._handle_greek_lookup(raw_query, canonical_targets, state)
        elif language == LanguageHint.LAT:
            self._handle_latin_lookup(raw_query, canonical_targets, state)
        elif language == LanguageHint.SAN:
            self._handle_sanskrit_raw(raw_query, state)

        if language in (LanguageHint.LAT, LanguageHint.GRC):
            state.ipa_value = self.cltk_ipa.lookup(language.name.lower(), raw_query)

        candidate_values = unique(state.candidates)
        structured = (
            self._sanskrit_candidates(candidate_values)
            if language == LanguageHint.SAN
            else self._structure_candidates(candidate_values, language, state.ipa_value)
        )
        selected = structured[0] if structured else None

        return CanonicalLookupResult(
            normalized_forms=list(canonical_targets),
            candidates=structured,
            selected=selected,
            responses=state.responses,
            extractions=state.extractions,
        )

    def _handle_greek_lookup(
        self, raw_query: str, canonical_targets: list[str], state: LookupState
    ) -> None:
        result = self.dio_wordlist.fetch(
            call_id=f"dio-wordlist-{raw_query}",
            query=raw_query,
            canonical_targets=canonical_targets,
        )
        state.responses.append(result.response_id)
        if result.extraction_id:
            state.extractions.append(result.extraction_id)
        if result.matches:
            state.matches.extend(result.matches)
        state.candidates.extend(result.all_candidates or result.lemmas)

    def _handle_latin_lookup(
        self, raw_query: str, canonical_targets: list[str], state: LookupState
    ) -> None:
        result = self.dio_parse.fetch(
            call_id=f"dio-parse-{raw_query}",
            query=raw_query,
            canonical_targets=canonical_targets,
        )
        state.responses.append(result.response_id)
        if result.extraction_id:
            state.extractions.append(result.extraction_id)
        if result.matches:
            state.matches.extend(result.matches)
        state.candidates.extend(result.lemmas)

        if self.whitaker.available():
            wres = self.whitaker.fetch(call_id=f"whitaker-{raw_query}", query=raw_query)
            if wres.response_id:
                state.responses.append(wres.response_id)
            if wres.extraction_id:
                state.extractions.append(wres.extraction_id)
            state.candidates.extend(wres.lemmas)

    def _handle_sanskrit_raw(self, raw_query: str, state: LookupState) -> None:
        heritage_params = f"text={raw_query};t=VH;max=3"
        effect = self.dio_client.execute(
            call_id=f"heritage-{raw_query}",
            endpoint=f"{self.heritage_endpoint}?{heritage_params}",
            params=None,
        )
        ref = self.raw_index.store(effect)
        state.responses.append(ref.response_id)

    def _structure_candidates(
        self, values: list[str], language: LanguageHint, ipa_value: str | None
    ) -> list[CanonicalCandidate]:
        structured: list[CanonicalCandidate] = []
        for candidate in values:
            encodings: dict[str, str] = {"lemma": candidate}
            if language == LanguageHint.GRC:
                encodings["accentless"] = strip_accents(candidate)
            if language == LanguageHint.LAT and ipa_value:
                encodings["ipa"] = ipa_value
            structured.append(
                CanonicalCandidate(lemma=candidate, encodings=encodings, sources=["diogenes"])
            )
        return structured

    def _sanskrit_candidates(self, forms: list[str]) -> list[CanonicalCandidate]:
        """
        Build structured candidates for Sanskrit with explicit encodings.
        """
        out: list[CanonicalCandidate] = []
        for form in forms:
            enc = self._classify_sanskrit_encoding(form)
            encs = {"lemma": form}
            encs[enc] = form
            # Add transliterations for known encodings
            sanscript = self._load_sanscript_module()
            if sanscript is not None:
                try:
                    scheme_map = {
                        ENC_DEVANAGARI: sanscript.DEVANAGARI,
                        ENC_IAST: sanscript.IAST,
                        ENC_SLP1: sanscript.SLP1,
                        ENC_VELTHUIS: sanscript.VELTHUIS,
                        ENC_HK: sanscript.HK,
                        ENC_ASCII: sanscript.HK,
                    }
                    src = scheme_map.get(enc, sanscript.HK)
                    encs["iast"] = sanscript.transliterate(form, src, sanscript.IAST)
                    encs["slp1"] = sanscript.transliterate(form, src, sanscript.SLP1)
                    encs["velthuis"] = sanscript.transliterate(form, src, sanscript.VELTHUIS)
                    encs["devanagari"] = sanscript.transliterate(form, src, sanscript.DEVANAGARI)
                except Exception:
                    pass
            out.append(CanonicalCandidate(lemma=form, encodings=encs, sources=["heritage"]))
        return out

    def _classify_sanskrit_encoding(self, text: str) -> str:
        if any(DEVANAGARI_UNICODE_START <= ord(c) <= DEVANAGARI_UNICODE_END for c in text):
            return "devanagari"
        if any(c in "āīūṛṝḷḹṃṅñṇṟṣśṭḍḥṁ" for c in text):
            return "iast"
        if "." in text or "~" in text:
            return "velthuis"
        if text.isascii() and text.lower() != text:
            return "slp1"
        return "hk"

    def _load_sanscript_module(self) -> SanscriptModule | None:
        try:
            module = importlib.import_module("indic_transliteration.sanscript")
            return cast(SanscriptModule, module)
        except Exception:
            return None
