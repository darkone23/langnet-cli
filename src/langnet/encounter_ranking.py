from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, field

from langnet.execution.handlers import cdsl as cdsl_handlers
from langnet.normalizer.utils import strip_accents

RANKING_MISSING = 10**12
BucketGlossFn = Callable[[object], str]


@dataclass(frozen=True, slots=True)
class BucketRankingExplanation:
    bucket_id: str
    display_gloss: str
    sort_key: tuple[int, int, int, int, int, int, tuple[int, ...], int, str]
    preferred_lemma_rank: int
    effective_preferred_lemma_rank: int
    learner_quality_order: int
    has_english_translation: bool
    has_bilingual_source: bool
    cdsl_dictionary_order: int
    source_order: int
    diogenes_source_order: tuple[int, ...]
    witness_count: int
    source_tools: tuple[str, ...] = field(default_factory=tuple)
    bucket_lemmas: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)


def reduction_lemma_values(reduction: object) -> list[str]:
    values = [anchor.removeprefix("lex:") for anchor in _reduction_lexeme_anchors(reduction)]
    for bucket in _reduction_buckets(reduction):
        values.extend(bucket_lemma_values(bucket))
    return _dedupe_preserve_order(values)


def preferred_lemmas_from_reduction(reduction: object) -> list[str]:
    values: list[str] = []
    for value in reduction_lemma_values(reduction):
        normalized = value.casefold()
        if normalized == "que" or normalized.endswith("#tackon"):
            continue
        values.append(value)
    return _dedupe_preserve_order(values)


def bucket_lemma_values(bucket: object) -> list[str]:
    values: list[str] = []
    for witness in _bucket_witnesses(bucket):
        lexeme_anchor = _string_value(getattr(witness, "lexeme_anchor", ""))
        if lexeme_anchor:
            values.append(lexeme_anchor.removeprefix("lex:"))
        evidence = _witness_evidence(witness)
        display_iast = evidence.get("display_iast")
        display_slp1 = evidence.get("display_slp1")
        if isinstance(display_iast, str):
            values.append(display_iast)
        if isinstance(display_slp1, str):
            values.append(cdsl_handlers._slp1_to_iast(display_slp1))  # type: ignore[attr-defined]
    return _dedupe_preserve_order(values)


def normalize_lemma(value: str) -> str:
    return value.removeprefix("lex:").casefold()


def lemma_compare_keys(value: str) -> set[str]:
    raw = normalize_lemma(value)
    base = raw.split("#", 1)[0]
    asciiish = strip_accents(raw)
    base_asciiish = strip_accents(base)
    compact = re.sub(r"[^a-z0-9]+", "", asciiish)
    base_compact = re.sub(r"[^a-z0-9]+", "", base_asciiish)
    simplified = compact.replace("aa", "a").replace("ii", "i").replace("uu", "u").replace("z", "s")
    base_simplified = (
        base_compact.replace("aa", "a").replace("ii", "i").replace("uu", "u").replace("z", "s")
    )
    return {key for key in {raw, base, compact, base_compact, simplified, base_simplified} if key}


def preferred_lemmas_from_morphology(
    morphology_rows: Sequence[Mapping[str, str]],
) -> list[str]:
    lemmas: list[str] = []
    ordered_rows = sorted(
        enumerate(morphology_rows),
        key=lambda item: morphology_lemma_preference_key(item[1], item[0]),
    )
    for _idx, row in ordered_rows:
        lemma = row.get("lemma")
        if lemma:
            lemmas.append(lemma)
    return _dedupe_preserve_order(lemmas)


def preferred_lemmas_for_sorting(
    reduction: object,
    morphology_rows: Sequence[Mapping[str, str]],
    fallback_terms: Sequence[str] = (),
) -> list[str]:
    return _dedupe_preserve_order(
        [
            *fallback_terms,
            *preferred_lemmas_from_morphology(morphology_rows),
            *preferred_lemmas_from_reduction(reduction),
        ]
    )


def morphology_lemma_preference_key(
    row: Mapping[str, str],
    idx: int,
) -> tuple[int, int]:
    analysis = row.get("analysis", "").casefold()
    if "tackon" in analysis:
        return (2, idx)
    form = row.get("form", "").strip().casefold()
    lemma = row.get("lemma", "").strip().casefold()
    if (
        form
        and form == lemma
        and ("noun" in analysis or "adjective" in analysis or "verb" in analysis)
    ):
        return (1, idx)
    return (0, idx)


def preferred_lemma_rank(
    bucket: object,
    preferred_lemmas: Sequence[str],
) -> int:
    if not preferred_lemmas:
        return RANKING_MISSING
    preferred: dict[str, int] = {}
    for idx, value in enumerate(preferred_lemmas):
        if not value:
            continue
        for key in lemma_compare_keys(value):
            preferred.setdefault(key, idx)
    bucket_lemmas = set().union(
        *(lemma_compare_keys(value) for value in bucket_lemma_values(bucket))
    )
    ranks = [preferred[lemma] for lemma in bucket_lemmas if lemma in preferred]
    return min(ranks) if ranks else RANKING_MISSING


def effective_preferred_lemma_rank(
    bucket: object,
    preferred_lemmas: Sequence[str],
    learner_quality_order: int,
) -> int:
    rank = preferred_lemma_rank(bucket, preferred_lemmas)
    if rank >= RANKING_MISSING:
        return rank
    return rank * 100 + learner_quality_order


def bucket_sort_key(
    bucket: object,
    preferred_lemmas: Sequence[str] = (),
    *,
    bucket_gloss: BucketGlossFn | None = None,
) -> tuple[int, int, int, int, int, int, tuple[int, ...], int, str]:
    gloss = _bucket_gloss(bucket, bucket_gloss)
    witnesses = _bucket_witnesses(bucket)
    has_english_translation = _has_english_translation(witnesses)
    has_bilingual_source = _has_bilingual_source(witnesses)
    cdsl_order = cdsl_source_order(bucket)
    source_order = min(
        cdsl_order,
        gaffiot_source_order(bucket),
        generic_source_order(bucket, "whitaker"),
    )
    learner_quality_order = bucket_learner_quality_order(bucket, bucket_gloss=bucket_gloss)
    return (
        effective_preferred_lemma_rank(bucket, preferred_lemmas, learner_quality_order),
        0 if has_english_translation else 1,
        learner_quality_order,
        0 if has_bilingual_source else 1,
        cdsl_dictionary_order(bucket),
        source_order,
        diogenes_source_order(bucket),
        -len(witnesses),
        gloss.lower(),
    )


def bucket_ranking_explanation(
    bucket: object,
    preferred_lemmas: Sequence[str] = (),
    *,
    bucket_gloss: BucketGlossFn | None = None,
) -> BucketRankingExplanation:
    gloss = _bucket_gloss(bucket, bucket_gloss)
    witnesses = _bucket_witnesses(bucket)
    learner_quality_order = bucket_learner_quality_order(bucket, bucket_gloss=bucket_gloss)
    lemma_rank = preferred_lemma_rank(bucket, preferred_lemmas)
    effective_lemma_rank = effective_preferred_lemma_rank(
        bucket,
        preferred_lemmas,
        learner_quality_order,
    )
    source_order = min(
        cdsl_source_order(bucket),
        gaffiot_source_order(bucket),
        generic_source_order(bucket, "whitaker"),
    )
    source_tools = tuple(sorted(bucket_source_tools(bucket)))
    english_translation = _has_english_translation(witnesses)
    bilingual_source = _has_bilingual_source(witnesses)
    reasons: list[str] = []
    if lemma_rank < RANKING_MISSING:
        reasons.append("matches preferred morphology/reduction lemma")
    if english_translation:
        reasons.append("has English translation evidence")
    if learner_quality_order < 0:
        reasons.append("promoted by learner-quality heuristic")
    elif learner_quality_order > 0:
        reasons.append("demoted by learner-quality heuristic")
    if bilingual_source:
        reasons.append("has DICO/Gaffiot bilingual source evidence")
    if source_order < RANKING_MISSING:
        reasons.append("ordered by source entry position")
    if source_tools:
        reasons.append(f"sources: {', '.join(source_tools)}")
    return BucketRankingExplanation(
        bucket_id=_string_value(getattr(bucket, "bucket_id", "")),
        display_gloss=gloss,
        sort_key=bucket_sort_key(bucket, preferred_lemmas, bucket_gloss=bucket_gloss),
        preferred_lemma_rank=lemma_rank,
        effective_preferred_lemma_rank=effective_lemma_rank,
        learner_quality_order=learner_quality_order,
        has_english_translation=english_translation,
        has_bilingual_source=bilingual_source,
        cdsl_dictionary_order=cdsl_dictionary_order(bucket),
        source_order=source_order,
        diogenes_source_order=diogenes_source_order(bucket),
        witness_count=len(witnesses),
        source_tools=source_tools,
        bucket_lemmas=tuple(bucket_lemma_values(bucket)),
        reasons=tuple(reasons),
    )


def cdsl_source_order(bucket: object) -> int:
    orders: list[int] = []
    for witness in _bucket_witnesses(bucket):
        if (
            _witness_source_tool(witness) != "cdsl"
            and _witness_evidence(witness).get("source_tool") != "cdsl"
        ):
            continue
        source_ref = _witness_evidence(witness).get("source_ref")
        if not isinstance(source_ref, str):
            continue
        match = re.search(r":(\d+)(?:\.\d+)?$", source_ref)
        if match:
            orders.append(int(match.group(1)))
    return min(orders) if orders else RANKING_MISSING


def cdsl_dictionary_order(bucket: object) -> int:
    priority = {"mw": 0, "ap90": 1}
    orders: list[int] = []
    for witness in _bucket_witnesses(bucket):
        if (
            _witness_source_tool(witness) != "cdsl"
            and _witness_evidence(witness).get("source_tool") != "cdsl"
        ):
            continue
        source_ref = _witness_evidence(witness).get("source_ref")
        if not isinstance(source_ref, str):
            continue
        dict_id = source_ref.split(":", 1)[0].lower()
        orders.append(priority.get(dict_id, 100))
    return min(orders) if orders else RANKING_MISSING


def bucket_learner_quality_order(
    bucket: object,
    *,
    bucket_gloss: BucketGlossFn | None = None,
) -> int:
    text = bucket_quality_text(bucket, bucket_gloss=bucket_gloss)
    source_tools = bucket_source_tools(bucket)
    score = 0

    if "also considered by native grammarians" in text or "base of the cases" in text:
        score += 80
    if "as used in comp" in text and not any(term in text for term in ("you", "thou")):
        score += 30

    if any(term in text for term in ("2nd personal pron", "second personal pron")) and any(
        term in text for term in ("you", "thou", "acc. tv", "accusative")
    ):
        score -= 30

    if (
        ("dico" in source_tools or "cdsl" in source_tools)
        and any(term in text for term in ("part.", "particle", "ind."))
        and any(
            term in text
            for term in (
                "blessing",
                "welfare",
                "happiness",
                "bonheur",
                "bien-être",
                "prosperity",
                "prospérité",
            )
        )
    ):
        score -= 30

    if "dico" in source_tools and any(term in text for term in ("[agt.", " ifc.")):
        score += 20
    if "cdsl" in source_tools and re.search(r"\bcl\.\s*\d", text) and " to " in text:
        score -= 15
    if any(term in text for term in ("sing of", " to sing", " chant", "celebrate")):
        score -= 250

    if "diogenes" in source_tools and re.match(r"^[ivxlcdm]+\.\s+", text) and "(cf." in text:
        score += 30

    return score


def bucket_quality_text(
    bucket: object,
    *,
    bucket_gloss: BucketGlossFn | None = None,
) -> str:
    values = [
        _bucket_gloss(bucket, bucket_gloss),
        _string_value(getattr(bucket, "display_gloss", "")),
    ]
    for witness in _bucket_witnesses(bucket):
        evidence = _witness_evidence(witness)
        for key in ("display_gloss", "learner_gloss", "normalized_gloss"):
            value = evidence.get(key)
            if isinstance(value, str):
                values.append(value)
    return " ".join(" ".join(value.casefold().split()) for value in values if value)


def bucket_source_tools(bucket: object) -> set[str]:
    tools: set[str] = set()
    for witness in _bucket_witnesses(bucket):
        source_tool = _witness_source_tool(witness)
        if source_tool:
            tools.add(source_tool)
        evidence_source_tool = _witness_evidence(witness).get("source_tool")
        if isinstance(evidence_source_tool, str) and evidence_source_tool:
            tools.add(evidence_source_tool)
    return tools


def _has_english_translation(witnesses: Sequence[object]) -> bool:
    return any(
        _witness_source_tool(witness) == "translation"
        or _witness_evidence(witness).get("source_tool") == "translation"
        or _witness_evidence(witness).get("source_lang") == "en"
        for witness in witnesses
    )


def _has_bilingual_source(witnesses: Sequence[object]) -> bool:
    return any(
        _witness_source_tool(witness) in {"dico", "gaffiot"}
        or _witness_evidence(witness).get("source_tool") in {"dico", "gaffiot"}
        or _witness_evidence(witness).get("derived_from_tool") in {"dico", "gaffiot"}
        for witness in witnesses
    )


def gaffiot_source_order(bucket: object) -> int:
    orders: list[int] = []
    for witness in _bucket_witnesses(bucket):
        if (
            _witness_source_tool(witness) != "gaffiot"
            and _witness_evidence(witness).get("source_tool") != "gaffiot"
        ):
            continue
        source_ref = _witness_evidence(witness).get("source_ref")
        if not isinstance(source_ref, str):
            continue
        match = re.search(r"gaffiot_(\d+)$", source_ref)
        if match:
            orders.append(int(match.group(1)))
    return min(orders) if orders else RANKING_MISSING


def generic_source_order(bucket: object, source_tool: str) -> int:
    orders: list[int] = []
    for witness in _bucket_witnesses(bucket):
        if (
            _witness_source_tool(witness) != source_tool
            and _witness_evidence(witness).get("source_tool") != source_tool
        ):
            continue
        source_order = _witness_evidence(witness).get("source_order")
        if isinstance(source_order, int):
            orders.append(source_order)
            continue
        if isinstance(source_order, str):
            with suppress(ValueError):
                orders.append(int(source_order))
    return min(orders) if orders else RANKING_MISSING


def diogenes_source_order(bucket: object) -> tuple[int, ...]:
    orders: list[tuple[int, ...]] = []
    for witness in _bucket_witnesses(bucket):
        if (
            _witness_source_tool(witness) != "diogenes"
            and _witness_evidence(witness).get("source_tool") != "diogenes"
        ):
            continue
        source_ref = _witness_evidence(witness).get("source_ref")
        if not isinstance(source_ref, str) or not source_ref.startswith("diogenes:"):
            continue
        parts = source_ref.removeprefix("diogenes:").split(":")
        numeric_parts: list[int] = []
        for part in parts:
            if not part.isdigit():
                numeric_parts = []
                break
            numeric_parts.append(int(part))
        if not numeric_parts:
            continue
        if len(numeric_parts) == 1:
            orders.append((10**9, *numeric_parts))
        else:
            orders.append(tuple(numeric_parts))
    return min(orders) if orders else (RANKING_MISSING,)


def _reduction_lexeme_anchors(reduction: object) -> Sequence[str]:
    anchors = getattr(reduction, "lexeme_anchors", ())
    if not isinstance(anchors, Sequence) or isinstance(anchors, (str, bytes)):
        return ()
    return [anchor for anchor in anchors if isinstance(anchor, str)]


def _reduction_buckets(reduction: object) -> Sequence[object]:
    buckets = getattr(reduction, "buckets", ())
    if not isinstance(buckets, Sequence) or isinstance(buckets, (str, bytes)):
        return ()
    return buckets


def _bucket_witnesses(bucket: object) -> Sequence[object]:
    witnesses = getattr(bucket, "witnesses", ())
    if not isinstance(witnesses, Sequence) or isinstance(witnesses, (str, bytes)):
        return ()
    return witnesses


def _witness_evidence(witness: object) -> Mapping[str, object]:
    evidence = getattr(witness, "evidence", {})
    return evidence if isinstance(evidence, Mapping) else {}


def _witness_source_tool(witness: object) -> str:
    return _string_value(getattr(witness, "source_tool", ""))


def _bucket_gloss(bucket: object, bucket_gloss: BucketGlossFn | None) -> str:
    if bucket_gloss is not None:
        return bucket_gloss(bucket)
    return _string_value(getattr(bucket, "display_gloss", ""))


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dedupe_preserve_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
