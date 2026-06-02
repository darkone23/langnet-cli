from __future__ import annotations

import importlib
import random
import re
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from langnet.execution.source_text import compact_source_gloss
from langnet.normalizer.greek_transliterator import transliterate_variants
from langnet.normalizer.utils import contains_greek
from langnet.paradigm.greek_learner_keys import (
    greek_learner_paradigm_hint,
    greek_learner_paradigm_priority,
)

WORD_OF_DAY_SCHEMA_VERSION = "langnet.word_of_day.v1"
WORD_OF_DAY_GENERATOR_VERSION = "0.2.0"
WORD_OF_DAY_SUMMARY_MAX_CHARS = 48
SUPPORTED_LANGUAGES = ("san", "grc", "lat")


@dataclass(frozen=True)
class WordCandidate:
    language: str
    query: str
    difficulty: str = "beginner"
    mnemonic: str = ""
    summary_hint: str = ""
    didactic_score: int = 50
    didactic_rationale: str = ""


@dataclass(frozen=True)
class WordOfDayOptions:
    count: int
    level: str
    dictionary: str
    reader_lang: str
    translation_mode: str
    max_source_chars: int
    include_ambiguous: bool
    require_clean_primary: bool
    timeout_ms: int
    seed: str | None = None
    fresh: bool = False
    avoid: tuple[str, ...] = ()
    nonce: str | None = None
    rotation_key: str | None = None
    candidate_source: str = "auto"


ProbeEncounter = Callable[[str, str], Any]
BucketGloss = Callable[[Any], str]
BucketLearnerGloss = Callable[[Any], str]


def _candidate_block(
    language: str,
    difficulty: str,
    queries: Sequence[str],
) -> tuple[WordCandidate, ...]:
    return tuple(
        WordCandidate(
            language=language,
            query=query,
            difficulty=difficulty,
            summary_hint=_SUMMARY_HINTS.get((language, query), ""),
        )
        for query in queries
    )


_SUMMARY_HINTS = {
    ("grc", "logos"): "word; speech; account; reason",
    ("grc", "homo"): "same; common; shared",
    ("grc", "polis"): "city; civic community",
    ("grc", "chronos"): "time",
    ("grc", "sophia"): "wisdom; skill",
    ("grc", "kratos"): "strength; power; rule",
    ("grc", "physis"): "nature; growth",
    ("grc", "theos"): "god; divine being",
    ("grc", "psyche"): "life; soul; breath",
    ("grc", "bios"): "life; livelihood",
    ("grc", "dike"): "justice; lawsuit",
    ("grc", "ergon"): "work; deed",
    ("grc", "oikos"): "house; household",
    ("grc", "philos"): "friend; beloved",
    ("grc", "phos"): "light",
    ("grc", "aner"): "man; husband",
    ("grc", "gyne"): "woman; wife",
    ("grc", "cheir"): "hand",
    ("grc", "paideia"): "education; culture",
    ("grc", "arete"): "excellence; virtue",
    ("grc", "arche"): "beginning; rule",
    ("grc", "thalassa"): "sea",
    ("grc", "ge"): "earth; land",
    ("grc", "ouranos"): "heaven; sky",
    ("grc", "helios"): "sun",
    ("grc", "selene"): "moon",
    ("grc", "nyx"): "night",
    ("grc", "hemera"): "day",
    ("grc", "pyr"): "fire",
    ("grc", "hydor"): "water",
    ("grc", "pneuma"): "breath; spirit",
    ("grc", "soma"): "body",
    ("grc", "haima"): "blood",
    ("grc", "kephale"): "head",
    ("grc", "ophthalmos"): "eye",
    ("grc", "glossa"): "tongue; language",
    ("grc", "kardia"): "heart",
    ("grc", "nous"): "mind",
    ("grc", "patēr"): "father",
    ("grc", "mētēr"): "mother",
    ("grc", "huios"): "son",
    ("grc", "thugatēr"): "daughter",
    ("grc", "adelphos"): "brother",
    ("grc", "pais"): "child; servant",
    ("grc", "doulos"): "slave; servant",
    ("grc", "basileus"): "king",
    ("grc", "stratos"): "army",
    ("grc", "naus"): "ship",
    ("grc", "hippos"): "horse",
    ("grc", "kuon"): "dog",
    ("grc", "leon"): "lion",
    ("grc", "ornis"): "bird",
    ("grc", "ichthys"): "fish",
    ("grc", "dendron"): "tree",
    ("grc", "anthos"): "flower",
    ("grc", "karpos"): "fruit",
    ("grc", "sitos"): "grain; food",
    ("grc", "oinos"): "wine",
    ("grc", "artos"): "bread",
    ("grc", "hodos"): "road; way",
    ("grc", "agora"): "marketplace; assembly",
    ("grc", "nomos"): "law; custom",
    ("grc", "boulē"): "counsel; plan",
    ("grc", "phobos"): "horror; fear",
    ("grc", "chara"): "joy",
    ("grc", "elpis"): "hope",
    ("grc", "kleos"): "fame; glory",
    ("grc", "techne"): "art; craft",
    ("grc", "mousa"): "muse; song",
    ("grc", "mythos"): "story; speech",
    ("grc", "epos"): "word; epic utterance",
    ("grc", "gramma"): "letter; writing",
    ("grc", "biblos"): "book",
    ("grc", "didaskalos"): "teacher",
    ("grc", "mathetes"): "learner; disciple",
    ("grc", "sophos"): "wise; skilled",
    ("grc", "kalos"): "beautiful; noble",
    ("grc", "kakos"): "bad; base",
    ("grc", "megas"): "great; large",
    ("grc", "mikros"): "small",
    ("grc", "neos"): "new; young",
    ("grc", "xenos"): "stranger; guest",
    ("grc", "ploutos"): "wealth",
    ("grc", "ponos"): "toil; labor",
    ("grc", "potamos"): "river",
}


_GRC_BEGINNER_QUERIES = (
    "logos",
    "homo",
    "polis",
    "chronos",
    "sophia",
    "kratos",
    "physis",
    "theos",
    "psyche",
    "bios",
    "dike",
    "oikos",
    "phos",
    "aner",
    "gyne",
    "cheir",
    "paideia",
    "arete",
    "arche",
    "thalassa",
    "ge",
    "ouranos",
    "selene",
    "nyx",
    "hemera",
    "pyr",
    "hydor",
    "pneuma",
    "soma",
    "haima",
    "kephale",
    "ophthalmos",
    "ous",
    "glossa",
    "kardia",
    "nous",
    "patēr",
    "mētēr",
    "huios",
    "thugatēr",
    "adelphos",
    "pais",
    "doulos",
    "despotes",
    "basileus",
    "stratos",
    "naus",
    "hippos",
    "kuon",
    "leon",
    "ornis",
    "ichthys",
    "dendron",
    "anthos",
    "karpos",
    "sitos",
    "oinos",
    "artos",
    "hodos",
    "agora",
    "nomos",
    "boulē",
    "phobos",
    "chara",
    "elpis",
    "kleos",
    "ergon",
    "techne",
    "mousa",
    "mythos",
    "epos",
    "gramma",
    "biblos",
    "didaskalos",
    "mathetes",
    "sophos",
    "kalos",
    "kakos",
    "megas",
    "mikros",
    "neos",
)

_GRC_INTERMEDIATE_QUERIES = (
    "hen",
    "mênis",
    "anthropos",
    "ananke",
    "aitia",
    "alētheia",
    "aporia",
    "askesis",
    "atē",
    "charis",
    "daimon",
    "demos",
    "dialogos",
    "dikaiosyne",
    "doxa",
    "dynamis",
    "eirene",
    "eleos",
    "eleutheria",
    "episteme",
    "eros",
    "ethos",
    "eudaimonia",
    "genos",
    "gnome",
    "hamartia",
    "hexis",
    "hēdonē",
    "historia",
    "hybris",
    "hypothesis",
    "idea",
    "katharsis",
    "kinesis",
    "kosmos",
    "krisis",
    "ktema",
    "kyrios",
    "lepsis",
    "machē",
    "mania",
    "martys",
    "mimesis",
    "moira",
    "morphe",
    "neikos",
    "nikē",
    "noesis",
    "nomisma",
    "nostos",
    "oikonomia",
    "olbos",
    "oneiros",
    "orgē",
    "paideusis",
    "paradeigma",
    "pathos",
    "peira",
    "peitho",
    "pharmakon",
    "philia",
    "phronesis",
    "plethos",
    "poiesis",
    "politēs",
    "praxis",
    "presbys",
    "prohairesis",
    "psychē",
    "rhētor",
    "sēmeion",
    "skēnē",
    "sophistēs",
    "sōphrosynē",
    "stasis",
    "stochos",
    "syllogismos",
    "symmachia",
    "synodos",
    "taxis",
    "telos",
    "timē",
    "tragōidia",
    "tropos",
    "tychē",
    "zētēsis",
    "zōē",
    "akropolis",
    "amphora",
    "archon",
    "aspis",
    "aulē",
    "bomos",
    "chiton",
    "choros",
    "chreia",
    "deipnon",
    "dikaios",
    "dromos",
    "eidolon",
    "eikon",
    "ekklēsia",
    "emporion",
    "enthymema",
    "epainos",
    "epigramma",
    "epikouros",
    "epistolē",
    "erēmos",
    "etymon",
    "euchē",
    "gamos",
    "geōrgos",
    "geras",
    "gymnasion",
    "hagnos",
    "halieus",
    "harmonia",
    "hērōs",
    "himation",
    "hoplon",
    "horkos",
    "hormē",
    "humnos",
    "iatros",
    "kallos",
    "kanon",
    "kapnos",
    "kēpos",
    "kēryx",
    "kithara",
    "kleis",
    "klēsis",
    "koinon",
    "kolpos",
    "komē",
    "korē",
    "koryphē",
    "krater",
    "kryptos",
    "kyklos",
    "limēn",
    "lyra",
    "magos",
    "mantis",
    "metron",
    "mnēmē",
    "molybdos",
    "morphē",
    "naos",
    "nekros",
    "nēsos",
    "nōtos",
    "odē",
    "oinochoē",
    "oligos",
    "omma",
    "oplon",
    "oros",
    "paidion",
    "palaistra",
    "panēgyris",
    "parodos",
    "pedion",
    "pelekys",
    "penthos",
    "peras",
    "petra",
    "phialē",
    "phōnē",
    "phylē",
    "pinax",
    "ploutos",
    "pnoē",
    "polemios",
    "ponos",
    "potamos",
    "pous",
    "prōra",
    "ptōma",
    "pylai",
    "rhiza",
    "sarkos",
    "skia",
    "skopos",
    "spondē",
    "stadion",
    "stathmos",
    "stēlē",
    "stratēgos",
    "sukon",
    "sumbolon",
    "syrinx",
    "taphos",
    "teknon",
    "temenos",
    "therapōn",
    "thronos",
    "thymos",
    "tithēnē",
    "trapeza",
    "tyrannos",
    "xenos",
    "xiphos",
    "zōon",
)

_GRC_DEEP_QUERIES = (
    "abaton",
    "adikia",
    "aergia",
    "aisthesis",
    "akrasia",
    "alazoneia",
    "amartia",
    "amphibolia",
    "anagnorisis",
    "anamnēsis",
    "aneleutheria",
    "antilogia",
    "antistrophē",
    "apathēs",
    "apodeixis",
    "apokatastasis",
    "apophasis",
    "aretē",
    "arktos",
    "asphaleia",
    "ataraxia",
    "autarkeia",
    "axioma",
    "barbaros",
    "bathos",
    "biotē",
    "bouleusis",
    "chōra",
    "chrēma",
    "chrēsis",
    "deixis",
    "demiourgos",
    "diakrisis",
    "dialektikē",
    "diathesis",
    "diēgēsis",
    "dikaiōma",
    "diorismos",
    "dysdaimonia",
    "ekbasis",
    "ekphrasis",
    "elaiōn",
    "elenchos",
    "empeiria",
    "enargeia",
    "energeia",
    "enthousiasmos",
    "epagōgē",
    "epanodos",
    "epieikeia",
    "epiphaneia",
    "epitaphios",
    "epithymia",
    "eucharistia",
    "eugeneia",
    "eunoia",
    "euphemia",
    "eusebeia",
    "exēgēsis",
    "gnōsis",
    "graphe",
    "hairesis",
    "hekousion",
    "henotēs",
    "hermēneia",
    "hēsychia",
    "homologia",
    "homonoia",
    "horismos",
    "hupokrisis",
    "hypomnēma",
    "isonomia",
    "kakia",
    "kalokagathia",
    "katabasis",
    "katēgoria",
    "koinōnia",
    "krasis",
    "kriterion",
    "kyrieia",
    "lēthē",
    "lexis",
    "makaria",
    "martyria",
    "mathēsis",
    "megalopsychia",
    "metabolē",
    "metanoia",
    "methodos",
    "metochē",
    "muthologia",
    "oikeiōsis",
    "onomia",
    "ontōs",
    "paideuma",
    "palingenesia",
    "parabasis",
    "paradosis",
    "parainesis",
    "paraklēsis",
    "parataxis",
    "parousia",
    "pathei",
    "periegesis",
    "peripeteia",
    "phantasia",
    "philautia",
    "philologia",
    "philosophia",
    "phronimos",
    "pistis",
    "politeia",
    "proairesis",
    "prologos",
    "prooimion",
    "prosōpon",
    "rhapsōidia",
    "schēma",
    "sēmantikos",
    "skepsis",
    "sophisma",
    "soteria",
    "spoudē",
    "stochasmos",
    "sugkatathesis",
    "sumbebēkos",
    "suneidēsis",
    "sunesis",
    "sunthesis",
    "systasis",
    "technē",
    "theōria",
    "thesis",
    "tropē",
    "zōion",
)


_CANDIDATE_POOLS: dict[str, tuple[WordCandidate, ...]] = {
    "san": (
        WordCandidate(
            "san",
            "agni",
            "beginner",
            "Agni is a frequent doorway into Vedic diction.",
            summary_hint="fire; sacrificial fire",
        ),
        WordCandidate(
            "san",
            "dharma",
            "beginner",
            "Dharma is worth revisiting because its range is broad.",
            summary_hint="law; duty; righteousness",
        ),
        WordCandidate(
            "san",
            "deva",
            "beginner",
            "Connect deva with divine or bright beings in context.",
            summary_hint="god; divine being",
        ),
        WordCandidate(
            "san",
            "yoga",
            "beginner",
            "Yoga is a compact form with a wide semantic history.",
            summary_hint="union; discipline; method",
        ),
        WordCandidate(
            "san",
            "manas",
            "intermediate",
            "Manas points learners toward mind and thought vocabulary.",
        ),
        WordCandidate(
            "san",
            "karman",
            "intermediate",
            "Karman helps connect action, result, and ritual language.",
        ),
        WordCandidate(
            "san", "atman", "deep", "Atman is useful when a learner is ready for semantic range."
        ),
    ),
    "grc": (
        _candidate_block("grc", "beginner", _GRC_BEGINNER_QUERIES)
        + _candidate_block("grc", "intermediate", _GRC_INTERMEDIATE_QUERIES)
        + _candidate_block("grc", "deep", _GRC_DEEP_QUERIES)
    ),
    "lat": (
        WordCandidate("lat", "nox", "beginner", "Nox is short, memorable, and rich in examples."),
        WordCandidate(
            "lat", "lupus", "beginner", "Lupus is a concrete noun with clean dictionary evidence."
        ),
        WordCandidate(
            "lat", "arma", "beginner", "Arma is a learner-friendly plural with epic resonance."
        ),
        WordCandidate(
            "lat", "amo", "beginner", "Amo is a classic first verb for morphology practice."
        ),
        WordCandidate(
            "lat", "rex", "beginner", "Rex makes case endings visible in a compact noun."
        ),
        WordCandidate(
            "lat", "corpus", "intermediate", "Corpus is a useful neuter noun with broad range."
        ),
        WordCandidate(
            "lat", "virtus", "intermediate", "Virtus rewards attention to cultural semantic range."
        ),
    ),
}


def resolve_word_of_day_languages(language: str) -> list[str]:
    normalized = language.strip().lower()
    if normalized == "all":
        return list(SUPPORTED_LANGUAGES)
    if normalized not in SUPPORTED_LANGUAGES:
        supported = "|".join((*SUPPORTED_LANGUAGES, "all"))
        raise ValueError(f"Unsupported word-of-day language '{language}'. Use {supported}.")
    return [normalized]


def generate_word_of_day_payload(  # noqa: PLR0913
    *,
    languages: Sequence[str],
    options: WordOfDayOptions,
    probe_encounter: ProbeEncounter,
    bucket_gloss: BucketGloss,
    bucket_learner_gloss: BucketLearnerGloss,
    exclude_terms: Iterable[str] = (),
    candidate_pools: Mapping[str, Sequence[WordCandidate]] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    avoided = _normalize_avoid_keys((*options.avoid, *tuple(exclude_terms)))
    warnings: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    freshness_repeats = 0
    diagnostics: dict[str, Any] = {
        "candidate_source": options.candidate_source,
        "languages": {},
    }

    def run_language(
        language: str,
    ) -> tuple[str, list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
        language_diagnostics: dict[str, Any] = {}
        language_warnings: list[dict[str, str]] = []
        language_items = _generate_language_items(
            language=language,
            options=options,
            rng=_language_rng(options, language, len(languages)),
            started=started,
            avoided=avoided,
            probe_encounter=probe_encounter,
            bucket_gloss=bucket_gloss,
            bucket_learner_gloss=bucket_learner_gloss,
            candidate_pools=candidate_pools,
            warnings=language_warnings,
            diagnostics=language_diagnostics,
        )
        return language, language_items, language_warnings, language_diagnostics

    with ThreadPoolExecutor(max_workers=min(len(languages), len(SUPPORTED_LANGUAGES))) as pool:
        results = list(pool.map(run_language, languages))

    for language, language_items, language_warnings, language_diagnostics in results:
        warnings.extend(language_warnings)
        diagnostics["languages"][language] = language_diagnostics
        freshness_repeats += sum(
            1
            for item in language_items
            if isinstance(item.get("novelty"), Mapping) and item["novelty"].get("is_repeat")
        )
        items.extend(language_items)
    fresh_satisfied = not options.fresh or freshness_repeats == 0

    return {
        "schema_version": WORD_OF_DAY_SCHEMA_VERSION,
        "generated_at": generated_at,
        "suggested_ttl_seconds": 86400,
        "generator": {
            "name": "langnet-word-of-day",
            "version": WORD_OF_DAY_GENERATOR_VERSION,
            "seed": options.seed,
            "mode": _generator_mode(options),
            "fresh": options.fresh,
            "nonce": options.nonce,
            "rotation_key": options.rotation_key,
            "candidate_source": options.candidate_source,
        },
        "request": {
            "languages": list(languages),
            "count": options.count,
            "level": options.level,
            "dictionary": options.dictionary,
            "reader_lang": options.reader_lang,
            "translation_mode": options.translation_mode,
            "include_ambiguous": options.include_ambiguous,
            "require_clean_primary": options.require_clean_primary,
            "max_source_chars": options.max_source_chars,
            "avoid": sorted(avoided),
        },
        "items": items,
        "warnings": warnings,
        "exhaustion": {
            "fresh_requested": options.fresh,
            "fresh_satisfied": fresh_satisfied,
            "reason": None
            if fresh_satisfied
            else "fresh alternatives were unavailable for one or more languages",
        },
        "diagnostics": diagnostics,
    }


def _language_rng(options: WordOfDayOptions, language: str, language_count: int) -> random.Random:
    seed = _rng_seed(options)
    if seed is None:
        return random.Random()
    if language_count == 1:
        return random.Random(seed)
    return random.Random(f"{seed}:{language}")


def _generate_language_items(  # noqa: C901, PLR0913
    *,
    language: str,
    options: WordOfDayOptions,
    rng: random.Random,
    started: float,
    avoided: set[str],
    probe_encounter: ProbeEncounter,
    bucket_gloss: BucketGloss,
    bucket_learner_gloss: BucketLearnerGloss,
    candidate_pools: Mapping[str, Sequence[WordCandidate]] | None,
    warnings: list[dict[str, str]],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    pool = list(_candidate_pool(language, candidate_pools))
    level_candidates = [
        candidate for candidate in pool if _candidate_matches_level(candidate, options.level)
    ]
    candidates = [
        candidate
        for candidate in level_candidates
        if (options.fresh or _candidate_key(candidate) not in avoided)
        and (options.fresh or candidate.query.lower() not in avoided)
    ]
    rng.shuffle(candidates)
    candidates.sort(
        key=lambda candidate: (
            _candidate_repeat_key(candidate, avoided) if options.fresh else 0,
            _candidate_paradigm_priority(candidate),
        )
    )
    accepted: list[dict[str, Any]] = []
    deferred_ambiguous: list[dict[str, Any]] = []
    deferred_repeats: list[dict[str, Any]] = []
    rejections: list[dict[str, str]] = []
    probed_count = 0

    for candidate in candidates:
        if options.timeout_ms > 0 and (time.monotonic() - started) * 1000 > options.timeout_ms:
            warnings.append(
                {
                    "language": language,
                    "query": candidate.query,
                    "message": (
                        "word-of-day generation timeout reached before probing all candidates"
                    ),
                }
            )
            rejections.append({"query": candidate.query, "reason": "timeout"})
            break
        try:
            probed_count += 1
            reduction = probe_encounter(language, candidate.query)
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                {
                    "language": language,
                    "query": candidate.query,
                    "message": f"encounter probe failed: {exc}",
                }
            )
            rejections.append({"query": candidate.query, "reason": "probe_failed"})
            continue

        item = build_word_of_day_item(
            candidate=candidate,
            reduction=reduction,
            options=options,
            bucket_gloss=bucket_gloss,
            bucket_learner_gloss=bucket_learner_gloss,
        )
        if item is None:
            warnings.append(
                {
                    "language": language,
                    "query": candidate.query,
                    "message": "encounter returned no usable source-backed buckets",
                }
            )
            rejections.append({"query": candidate.query, "reason": "no_usable_buckets"})
            continue
        _add_novelty_metadata(
            item,
            avoided=avoided,
            fresh=options.fresh,
            reason="selected outside caller avoid list",
        )
        if options.fresh and item["novelty"]["is_repeat"]:
            item["novelty"]["reason"] = "returned only because fresh alternatives were exhausted"
            deferred_repeats.append(item)
            continue
        if item["ambiguity"]["has_multiple_lexemes"] and not options.include_ambiguous:
            if options.require_clean_primary:
                rejections.append({"query": candidate.query, "reason": "ambiguous"})
                continue
            deferred_ambiguous.append(item)
            continue
        accepted.append(item)
        if len(accepted) >= options.count:
            break

    if len(accepted) < options.count and not options.require_clean_primary:
        needed = options.count - len(accepted)
        accepted.extend(deferred_ambiguous[:needed])
    if len(accepted) < options.count:
        needed = options.count - len(accepted)
        accepted.extend(deferred_repeats[:needed])
    if len(accepted) < options.count:
        warnings.append(
            {
                "language": language,
                "query": "",
                "message": f"only generated {len(accepted)} of {options.count} requested item(s)",
            }
        )
    diagnostics.update(
        {
            "pool_size": len(pool),
            "level_eligible_count": len(level_candidates),
            "eligible_count": len(candidates),
            "probed_count": probed_count,
            "accepted_count": len(accepted),
            "deferred_ambiguous_count": len(deferred_ambiguous),
            "deferred_repeat_count": len(deferred_repeats),
            "rejected_count": len(rejections),
            "rejections": rejections[:20],
            "accepted_keys": [str(item.get("key") or "") for item in accepted],
        }
    )
    return accepted


def _candidate_pool(
    language: str,
    candidate_pools: Mapping[str, Sequence[WordCandidate]] | None,
) -> Sequence[WordCandidate]:
    if candidate_pools is not None:
        return candidate_pools.get(language, ())
    return _CANDIDATE_POOLS.get(language, ())


def build_word_of_day_item(
    *,
    candidate: WordCandidate,
    reduction: Any,
    options: WordOfDayOptions,
    bucket_gloss: BucketGloss,
    bucket_learner_gloss: BucketLearnerGloss,
) -> dict[str, Any] | None:
    buckets = list(getattr(reduction, "buckets", []) or [])
    if not buckets:
        return None
    bucket = _best_bucket_for_candidate(
        buckets,
        candidate=candidate,
        bucket_gloss=bucket_gloss,
        max_source_chars=options.max_source_chars,
    )
    witnesses = list(getattr(bucket, "witnesses", []) or [])
    if not witnesses:
        return None

    source_basis = _source_basis(witnesses, bucket_gloss, options.max_source_chars)
    summary_hint = candidate.summary_hint
    if summary_hint and not _summary_hint_supported(summary_hint, source_basis):
        summary_hint = ""
    summary = _summary_for_bucket(
        bucket,
        bucket_learner_gloss,
        summary_hint=summary_hint if source_basis else "",
    )
    if not summary:
        return None
    lexeme_anchors = list(getattr(reduction, "lexeme_anchors", []) or [])
    primary_lexeme = _primary_lexeme(lexeme_anchors, witnesses)
    display = _display_label(candidate.query, primary_lexeme, witnesses)
    canonical = _canonical_term_payload(
        candidate.language, candidate.query, primary_lexeme, witnesses
    )
    if candidate.language == "san":
        display = canonical["transliteration"] or candidate.query or display
    lexeme_family_count = _lexeme_family_count(candidate.language, lexeme_anchors)
    has_multiple_lexemes = lexeme_family_count > 1
    confidence = _confidence_label(
        has_multiple_lexemes, source_basis, getattr(bucket, "confidence_label", "")
    )

    return {
        "language": candidate.language,
        "query": candidate.query,
        "key": _candidate_key(candidate),
        "display": display,
        "canonical_name": canonical["name"],
        "canonical": canonical,
        "primary_lexeme": primary_lexeme,
        "lexeme_anchors": lexeme_anchors,
        "summary": summary,
        "learner_note": _learner_note(
            candidate.query, canonical["name"], primary_lexeme, has_multiple_lexemes
        ),
        "mnemonic": candidate.mnemonic,
        "difficulty": candidate.difficulty,
        "confidence": confidence,
        "ambiguity": {
            "has_multiple_lexemes": has_multiple_lexemes,
            "lexeme_count": lexeme_family_count,
            "note": _ambiguity_note(lexeme_anchors) if has_multiple_lexemes else "",
        },
        "recommended_request": {
            "language": candidate.language,
            "q": candidate.query,
            "dictionary": options.dictionary,
            "translation": "auto",
            "backend": "cli",
        },
        "source_basis": source_basis,
        "ui": {
            "href_query": urlencode(
                {
                    "lang": candidate.language,
                    "q": candidate.query,
                    "dictionary": options.dictionary,
                    "translation": "auto",
                    "load": "yes",
                }
            ),
            "badge": _language_badge(candidate.language),
            "short_gloss": _short_gloss(summary),
        },
    }


def _rng_seed(options: WordOfDayOptions) -> str | None:
    if options.seed is not None:
        return options.seed
    if options.rotation_key or options.nonce:
        return "\x1f".join(
            part
            for part in (
                options.rotation_key or "",
                options.nonce or "",
                str(options.fresh),
            )
            if part
        )
    return None


def _generator_mode(options: WordOfDayOptions) -> str:
    if options.seed is not None:
        return "seeded"
    if options.rotation_key:
        return "rotation"
    return "nondeterministic"


def _candidate_key(candidate: WordCandidate) -> str:
    return f"{candidate.language}:{candidate.query}".lower()


def _candidate_repeat_key(candidate: WordCandidate, avoided: set[str]) -> int:
    return 1 if _candidate_key(candidate) in avoided or candidate.query.lower() in avoided else 0


def _lexeme_family_count(language: str, lexeme_anchors: Sequence[str]) -> int:
    family_keys = {
        _lexeme_family_key(language, anchor)
        for anchor in lexeme_anchors
        if _lexeme_family_key(language, anchor)
    }
    return len(family_keys)


def _lexeme_family_key(language: str, lexeme_anchor: str) -> str:
    key = str(lexeme_anchor).removeprefix("lex:").split("#", 1)[0].lower().strip()
    if language == "san":
        key = key.removesuffix("ḥ").removesuffix("h")
    return key


def _candidate_paradigm_priority(candidate: WordCandidate) -> int:
    if candidate.language == "grc":
        return greek_learner_paradigm_priority(candidate.query)
    return 0


def _normalize_avoid_keys(values: Iterable[str]) -> set[str]:
    keys: set[str] = set()
    for value in values:
        for part in str(value).split(","):
            cleaned = part.strip().lower()
            if not cleaned:
                continue
            keys.add(cleaned)
            if ":" in cleaned:
                keys.add(cleaned.rsplit(":", 1)[-1])
    return keys


def _add_novelty_metadata(
    item: dict[str, Any],
    *,
    avoided: set[str],
    fresh: bool,
    reason: str,
) -> None:
    key = str(item.get("key") or "").lower()
    query = str(item.get("query") or "").lower()
    is_repeat = key in avoided or query in avoided
    item["novelty"] = {
        "is_repeat": is_repeat,
        "avoided_recent_count": len(avoided),
        "fresh_requested": fresh,
        "reason": reason if not is_repeat else "matched caller avoid list",
    }


def _candidate_matches_level(candidate: WordCandidate, level: str) -> bool:
    if level == "deep":
        return True
    if level == "intermediate":
        return candidate.difficulty in {"beginner", "intermediate"}
    return candidate.difficulty == "beginner"


def _best_bucket(buckets: Sequence[Any]) -> Any:
    return min(buckets, key=_bucket_recommendation_sort_key)


def _best_bucket_for_candidate(
    buckets: Sequence[Any],
    *,
    candidate: WordCandidate,
    bucket_gloss: BucketGloss,
    max_source_chars: int,
) -> Any:
    sorted_buckets = sorted(buckets, key=_bucket_recommendation_sort_key)
    if candidate.summary_hint:
        for bucket in sorted_buckets:
            witnesses = list(getattr(bucket, "witnesses", []) or [])
            source_basis = _source_basis(witnesses, bucket_gloss, max_source_chars)
            if _summary_hint_supported(candidate.summary_hint, source_basis):
                return bucket
    return sorted_buckets[0]


def _bucket_recommendation_sort_key(bucket: Any) -> tuple[int, int, int, int, int, str]:
    witnesses = list(getattr(bucket, "witnesses", []) or [])
    source_tools = [_witness_source_tool(witness) for witness in witnesses]
    source_langs = [_witness_source_lang(witness) for witness in witnesses]
    return (
        1 if "fr" in source_langs else 0,
        min((_source_tool_preference(tool) for tool in source_tools), default=50),
        _bucket_gloss_quality_order(bucket),
        min((_witness_source_order(witness) for witness in witnesses), default=1_000_000),
        -len(witnesses),
        str(getattr(bucket, "display_gloss", "") or ""),
    )


def _bucket_gloss_quality_order(bucket: Any) -> int:
    gloss = compact_source_gloss(str(getattr(bucket, "display_gloss", "") or ""), max_chars=80)
    normalized = gloss.strip().lower()
    if not normalized:
        return 3
    if normalized.startswith(("=", "(also) =", "also) =", "cf.", "see ")):
        return 3
    if re.match(
        r"^(?:(?:[ivxlcdm]+|\d+)\.\s*)?"
        r"(?:in\s+)?(?:concrete|abstract|proper|figurative|metaphorical)\s+sense\b",
        normalized,
    ):
        return 2
    if len(_support_tokens(normalized)) <= 1 and any(char in normalized for char in "=;:,"):
        return 2
    return 0


def _source_tool_preference(tool: str) -> int:
    return {
        "whitaker": 0,
        "diogenes": 1,
        "cdsl": 1,
        "heritage": 2,
        "gaffiot": 4,
        "dico": 4,
    }.get(tool, 3)


def _witness_source_tool(witness: Any) -> str:
    evidence = getattr(witness, "evidence", {}) or {}
    if isinstance(evidence, Mapping):
        return str(evidence.get("source_tool") or getattr(witness, "source_tool", "") or "")
    return str(getattr(witness, "source_tool", "") or "")


def _witness_source_lang(witness: Any) -> str:
    evidence = getattr(witness, "evidence", {}) or {}
    if isinstance(evidence, Mapping):
        return str(evidence.get("source_lang") or "")
    return ""


def _witness_source_order(witness: Any) -> int:
    evidence = getattr(witness, "evidence", {}) or {}
    if not isinstance(evidence, Mapping):
        return 1_000_000
    try:
        return int(evidence.get("source_order", 1_000_000))
    except (TypeError, ValueError):
        return 1_000_000


def _summary_for_bucket(
    bucket: Any,
    bucket_learner_gloss: BucketLearnerGloss,
    *,
    summary_hint: str = "",
) -> str:
    if summary_hint.strip():
        return _terse_summary(summary_hint)
    summary = bucket_learner_gloss(bucket).strip()
    if not summary:
        summary = str(getattr(bucket, "display_gloss", "") or "").strip()
    return _terse_summary(summary)


def _terse_summary(summary: str) -> str:
    return _clean_recommendation_summary(
        compact_source_gloss(summary, max_chars=WORD_OF_DAY_SUMMARY_MAX_CHARS)
    )


def _summary_hint_supported(
    summary_hint: str,
    source_basis: Sequence[Mapping[str, Any]],
) -> bool:
    hint_tokens = _support_tokens(summary_hint)
    if not hint_tokens:
        return False
    evidence_text = " ".join(str(item.get("evidence") or "") for item in source_basis)
    evidence_tokens = _support_tokens(evidence_text)
    return bool(hint_tokens & evidence_tokens)


def _support_tokens(text: str) -> set[str]:
    stopwords = {
        "and",
        "the",
        "for",
        "with",
        "from",
        "into",
        "upon",
        "specific",
        "general",
    }
    return {token for token in re.findall(r"[A-Za-z]{3,}", text.lower()) if token not in stopwords}


def _clean_recommendation_summary(summary: str) -> str:
    summary = summary.strip()
    if summary.startswith("("):
        summary = summary[1:].strip()
    summary = _strip_structural_gloss_prefix(summary)
    for prefix in ("pl. ", "sg. "):
        if summary.lower().startswith(prefix):
            summary = summary[len(prefix) :].strip()
    head, sep, _tail = summary.partition(" (")
    if sep and head.strip():
        summary = head.strip()
    summary = _strip_greek_example_tail(summary)
    summary = _strip_reference_tail(summary)
    if _looks_like_reference_fragment(summary):
        return ""
    return summary


def _strip_structural_gloss_prefix(summary: str) -> str:
    return re.sub(
        r"^(?:(?:[ivxlcdm]+|\d+)\.\s*)?"
        r"(?:in\s+)?(?:concrete|abstract|proper|figurative|metaphorical)\s+sense,?\s*",
        "",
        summary,
        flags=re.IGNORECASE,
    ).strip()


def _strip_reference_tail(summary: str) -> str:
    summary = re.sub(r"(?:,\s*)?etc\.?\s*$", "", summary, flags=re.IGNORECASE)
    summary = re.sub(r"(?:,\s*)?(?:etc\.?,?\s*)?cf\.?\s*$", "", summary, flags=re.IGNORECASE)
    return summary.strip(" ,;:")


def _strip_greek_example_tail(summary: str) -> str:
    match = re.search(r"[\u0370-\u03ff]", summary)
    if not match:
        return summary
    prefix = summary[: match.start()].rstrip(" ,;:([{")
    if re.search(r"[A-Za-z]", prefix):
        return prefix
    return summary


def _looks_like_reference_fragment(summary: str) -> bool:
    lowered = summary.lower().strip(" ;,")
    if not lowered:
        return True
    if lowered.startswith(("cf", "see", "cod", "v.l", "ms", "mss", "sch")):
        return True
    if re.fullmatch(
        r"(?:c\.|gen\.?|acc\.?|dat\.?|abl\.?|nom\.?|voc\.?|loc\.?|instr\.?|m\.?|f\.?|n\.?)"
        r"(?:\s+(?:c\.|gen\.?|acc\.?|dat\.?|abl\.?|nom\.?|voc\.?|loc\.?|instr\.?|m\.?|f\.?|n\.?))*",
        lowered,
    ):
        return True
    return bool(re.fullmatch(r"(?:[a-z]{1,8}\.\s*){1,4}", lowered))


def _primary_lexeme(lexeme_anchors: Sequence[str], witnesses: Sequence[Any]) -> str:
    for witness in witnesses:
        anchor = str(getattr(witness, "lexeme_anchor", "") or "")
        if anchor:
            return anchor.removeprefix("lex:").split("#", 1)[0]
    if lexeme_anchors:
        return str(lexeme_anchors[0]).removeprefix("lex:").split("#", 1)[0]
    return ""


def _display_label(query: str, primary_lexeme: str, witnesses: Sequence[Any]) -> str:
    source_term = _first_source_entry_value(witnesses, "term")
    if source_term and source_term != primary_lexeme:
        return source_term
    return primary_lexeme or query


def _canonical_term_payload(
    language: str,
    query: str,
    primary_lexeme: str,
    witnesses: Sequence[Any],
) -> dict[str, str]:
    if language == "san":
        return _sanskrit_canonical_payload(query, primary_lexeme, witnesses)
    if language == "grc":
        return _greek_canonical_payload(query, primary_lexeme, witnesses)
    return _latin_canonical_payload(query, primary_lexeme, witnesses)


def _sanskrit_canonical_payload(
    query: str,
    primary_lexeme: str,
    witnesses: Sequence[Any],
) -> dict[str, str]:
    deva_value, deva_source = _first_matching_choice(
        witnesses,
        source_entry_keys=("headword_deva", "term", "headword", "display_form"),
        evidence_keys=("display_deva", "canonical_deva"),
        predicate=_contains_devanagari,
    )
    transliteration, _translit_source = _first_choice(
        witnesses,
        source_entry_keys=("headword_roma", "key_iast", "key2_iast", "headword_norm"),
        evidence_keys=("display_iast", "canonical_iast"),
    )
    if not deva_value:
        deva_value, deva_source = _sanskrit_devanagari_from_sources(
            query, primary_lexeme, witnesses
        )
    if not transliteration:
        transliteration = _first_non_devanagari(primary_lexeme, query)
    source_key, _source_key_source = _first_choice(
        witnesses,
        source_entry_keys=("key_slp1", "key_iast", "headword_norm", "headword_roma", "term"),
        evidence_keys=("display_slp1", "display_iast"),
    )
    return {
        "name": deva_value or primary_lexeme or query,
        "script": "Devanagari",
        "source": deva_source or "fallback.primary_lexeme",
        "transliteration": transliteration,
        "source_key": source_key or primary_lexeme or query,
        "lexeme": primary_lexeme,
    }


def _greek_canonical_payload(
    query: str,
    primary_lexeme: str,
    witnesses: Sequence[Any],
) -> dict[str, str]:
    paradigm_hint = greek_learner_paradigm_hint(query) or greek_learner_paradigm_hint(
        primary_lexeme
    )
    greek_value, greek_source = _first_matching_choice(
        witnesses,
        source_entry_keys=("term", "headword", "display_form", "headword_norm", "key"),
        evidence_keys=("display_form", "canonical_form", "lemma"),
        predicate=contains_greek,
    )
    if not greek_value and contains_greek(primary_lexeme):
        greek_value = primary_lexeme
        greek_source = "primary_lexeme"
    if not greek_value and contains_greek(query):
        greek_value = query
        greek_source = "query"
    if not greek_value:
        greek_value, greek_source = _greek_unicode_from_transliteration(primary_lexeme or query)
    source_key, _source_key_source = _first_choice(
        witnesses,
        source_entry_keys=("headword_norm", "key", "term"),
        evidence_keys=("display_form",),
    )
    if paradigm_hint is not None:
        source_key = paradigm_hint.source_key
    if contains_greek(source_key):
        source_key = primary_lexeme or query
    return {
        "name": greek_value or primary_lexeme or query,
        "script": "Greek",
        "source": greek_source or "fallback.primary_lexeme",
        "transliteration": "" if contains_greek(query) else query,
        "source_key": source_key or primary_lexeme or query,
        "lexeme": primary_lexeme,
    }


def _latin_canonical_payload(
    query: str,
    primary_lexeme: str,
    witnesses: Sequence[Any],
) -> dict[str, str]:
    name, source = _first_choice(
        witnesses,
        source_entry_keys=("term", "headword", "headword_norm", "key"),
        evidence_keys=("display_form", "lemma"),
    )
    if not name:
        name = primary_lexeme or query
        source = "fallback.primary_lexeme" if primary_lexeme else "query"
    return {
        "name": name,
        "script": "Latin",
        "source": source,
        "transliteration": name,
        "source_key": name,
        "lexeme": primary_lexeme,
    }


def _sanskrit_devanagari_from_sources(
    query: str,
    primary_lexeme: str,
    witnesses: Sequence[Any],
) -> tuple[str, str]:
    for value, source, scheme in _sanskrit_transliteration_choices(
        query, primary_lexeme, witnesses
    ):
        rendered = _transliterate_sanskrit_to_devanagari(value, scheme)
        if rendered:
            return rendered, f"transliteration.{source}"
    return "", ""


def _sanskrit_transliteration_choices(
    query: str,
    primary_lexeme: str,
    witnesses: Sequence[Any],
) -> list[tuple[str, str, str]]:
    choices: list[tuple[str, str, str]] = []
    for value, source in _choices(
        witnesses,
        source_entry_keys=("headword_roma", "key_iast", "key2_iast"),
        evidence_keys=("display_iast", "canonical_iast"),
    ):
        choices.append((value, source, "IAST"))
    for value, source in _choices(
        witnesses,
        source_entry_keys=("key_slp1", "key2_slp1"),
        evidence_keys=("display_slp1",),
    ):
        choices.append((value, source, "SLP1"))
    if query and not _contains_devanagari(query):
        choices.append((query, "query", "IAST"))
    if primary_lexeme and not _contains_devanagari(primary_lexeme):
        scheme = "SLP1" if _looks_like_sanskrit_slp1(primary_lexeme) else "IAST"
        choices.append((primary_lexeme, "primary_lexeme", scheme))
    return choices


def _transliterate_sanskrit_to_devanagari(text: str, scheme_name: str) -> str:
    if not text.strip():
        return ""
    with suppress(Exception):
        sanscript = importlib.import_module("indic_transliteration.sanscript")
        scheme = getattr(sanscript, scheme_name)
        rendered = sanscript.transliterate(text, scheme, sanscript.DEVANAGARI)
        if rendered and rendered != text and _contains_devanagari(rendered):
            return rendered
    return ""


def _greek_unicode_from_transliteration(text: str) -> tuple[str, str]:
    if not text.strip():
        return "", ""
    with suppress(Exception):
        variants = transliterate_variants(text)
        for variant in variants:
            display = variant.display or variant.search_key
            if display and contains_greek(display):
                return display, "transliteration.query"
    return "", ""


def _first_non_devanagari(*values: str) -> str:
    for value in values:
        if value and not _contains_devanagari(value):
            return value
    return ""


def _first_matching_choice(
    witnesses: Sequence[Any],
    *,
    source_entry_keys: Sequence[str],
    evidence_keys: Sequence[str],
    predicate: Callable[[str], bool],
) -> tuple[str, str]:
    for value, source in _choices(
        witnesses,
        source_entry_keys=source_entry_keys,
        evidence_keys=evidence_keys,
    ):
        if predicate(value):
            return value, source
    return "", ""


def _first_choice(
    witnesses: Sequence[Any],
    *,
    source_entry_keys: Sequence[str],
    evidence_keys: Sequence[str],
) -> tuple[str, str]:
    return next(
        iter(
            _choices(
                witnesses,
                source_entry_keys=source_entry_keys,
                evidence_keys=evidence_keys,
            )
        ),
        ("", ""),
    )


def _choices(
    witnesses: Sequence[Any],
    *,
    source_entry_keys: Sequence[str],
    evidence_keys: Sequence[str],
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for witness in witnesses:
        evidence = getattr(witness, "evidence", {}) or {}
        if not isinstance(evidence, Mapping):
            continue
        source_entry = evidence.get("source_entry")
        if isinstance(source_entry, Mapping):
            for key in source_entry_keys:
                value = source_entry.get(key)
                if isinstance(value, str) and value.strip():
                    _append_choice(out, seen, value.strip(), f"source_entry.{key}")
        for key in evidence_keys:
            value = evidence.get(key)
            if isinstance(value, str) and value.strip():
                _append_choice(out, seen, value.strip(), f"evidence.{key}")
    return out


def _append_choice(
    out: list[tuple[str, str]],
    seen: set[tuple[str, str]],
    value: str,
    source: str,
) -> None:
    item = (value, source)
    if item not in seen:
        out.append(item)
        seen.add(item)


def _contains_devanagari(text: str) -> bool:
    return any("\u0900" <= char <= "\u097f" for char in text)


def _looks_like_sanskrit_slp1(text: str) -> bool:
    return any(char in text for char in "ARLIUfFxXeEoOMHKGNJCYwWqQPBDSzS")


def _source_basis(
    witnesses: Sequence[Any],
    bucket_gloss: BucketGloss,
    max_source_chars: int,
) -> list[dict[str, Any]]:
    basis: list[dict[str, Any]] = []
    for witness in _source_basis_witnesses(witnesses):
        evidence = getattr(witness, "evidence", {}) or {}
        if not isinstance(evidence, Mapping):
            evidence = {}
        source_entry = evidence.get("source_entry")
        if not isinstance(source_entry, Mapping):
            source_entry = {}
        source_text = str(
            source_entry.get("source_text")
            or evidence.get("display_gloss")
            or getattr(witness, "gloss", "")
            or ""
        )
        basis.append(
            {
                "tool": str(
                    getattr(witness, "source_tool", "") or evidence.get("source_tool") or ""
                ),
                "source_ref": str(
                    source_entry.get("source_ref") or evidence.get("source_ref") or ""
                ),
                "lexeme_anchor": str(getattr(witness, "lexeme_anchor", "") or ""),
                "evidence": compact_source_gloss(
                    source_text or bucket_gloss_from_witness(bucket_gloss, witness),
                    max_chars=max_source_chars,
                ),
            }
        )
    return basis


def _source_basis_witnesses(witnesses: Sequence[Any]) -> list[Any]:
    ranked = sorted(
        enumerate(witnesses),
        key=lambda item: (not _witness_source_ref(item[1]), item[0]),
    )
    return [witness for _, witness in ranked[:3]]


def _witness_source_ref(witness: Any) -> str:
    evidence = getattr(witness, "evidence", {}) or {}
    if not isinstance(evidence, Mapping):
        return ""
    source_entry = evidence.get("source_entry")
    if isinstance(source_entry, Mapping):
        source_ref = source_entry.get("source_ref")
        if isinstance(source_ref, str) and source_ref.strip():
            return source_ref.strip()
    source_ref = evidence.get("source_ref")
    if isinstance(source_ref, str) and source_ref.strip():
        return source_ref.strip()
    return ""


def bucket_gloss_from_witness(bucket_gloss: BucketGloss, witness: Any) -> str:
    try:
        return bucket_gloss(type("_Bucket", (), {"witnesses": [witness], "display_gloss": ""})())
    except Exception:  # noqa: BLE001
        return str(getattr(witness, "gloss", "") or "")


def _first_source_entry_value(witnesses: Sequence[Any], key: str) -> str:
    for witness in witnesses:
        evidence = getattr(witness, "evidence", {}) or {}
        if not isinstance(evidence, Mapping):
            continue
        source_entry = evidence.get("source_entry")
        if not isinstance(source_entry, Mapping):
            continue
        value = source_entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _confidence_label(
    has_multiple_lexemes: bool,
    source_basis: Sequence[Mapping[str, Any]],
    bucket_confidence: str,
) -> str:
    if not source_basis:
        return "low"
    if has_multiple_lexemes:
        return "medium"
    if bucket_confidence == "multi-witness":
        return "high"
    return "high"


def _learner_note(
    query: str,
    display: str,
    primary_lexeme: str,
    has_multiple_lexemes: bool,
) -> str:
    if has_multiple_lexemes:
        return (
            "Useful for learners because it shows a primary entry while exposing related "
            "lexical neighborhoods."
        )
    if primary_lexeme:
        return (
            f"Useful for learners because `{query}` opens a compact, source-backed entry "
            f"for {display}."
        )
    return "Useful for learners because it opens a source-backed dictionary entry."


def _ambiguity_note(lexeme_anchors: Sequence[str]) -> str:
    if len(lexeme_anchors) <= 1:
        return ""
    return "Returned evidence includes " + ", ".join(lexeme_anchors[:5]) + "."


def _short_gloss(summary: str) -> str:
    return _clean_recommendation_summary(summary.split(";", 1)[0].split(",", 1)[0].strip())


def _language_badge(language: str) -> str:
    return {
        "san": "Sanskrit",
        "grc": "Greek",
        "lat": "Latin",
    }.get(language, language)
