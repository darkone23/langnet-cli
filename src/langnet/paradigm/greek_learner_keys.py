from __future__ import annotations

import re
from dataclasses import dataclass

from langnet.normalizer.utils import normalize_greekish_token


@dataclass(frozen=True)
class GreekLearnerParadigmHint:
    learner_key: str
    lemma: str
    source_key: str
    part_of_speech: str
    source: str = "langnet:greek_learner_paradigm_hints"


_HINTS: dict[str, GreekLearnerParadigmHint] = {
    "logos": GreekLearnerParadigmHint("logos", "λόγος", "lo/gos", "noun"),
    "sophos": GreekLearnerParadigmHint("sophos", "σοφός", "sofo/s", "adjective"),
    "nomos": GreekLearnerParadigmHint("nomos", "νόμος", "no/mos", "noun"),
    "didaskalos": GreekLearnerParadigmHint("didaskalos", "διδάσκαλος", "dida/skalos", "noun"),
    "dike": GreekLearnerParadigmHint("dike", "δίκη", "di/kh", "noun"),
    "psyche": GreekLearnerParadigmHint("psyche", "ψυχή", "yuxh/", "noun"),
    "mikros": GreekLearnerParadigmHint("mikros", "μικρός", "mikro/s", "adjective"),
    "selene": GreekLearnerParadigmHint("selene", "σελήνη", "selh/nh", "noun"),
    "thalassa": GreekLearnerParadigmHint("thalassa", "θάλασσα", "qa/lassa", "noun"),
    "mathetes": GreekLearnerParadigmHint("mathetes", "μαθητής", "maqhth/s", "noun"),
    "chara": GreekLearnerParadigmHint("chara", "χαρά", "xara/", "noun"),
    "haima": GreekLearnerParadigmHint("haima", "αἷμα", "ai(=ma", "noun"),
    "ge": GreekLearnerParadigmHint("ge", "γῆ", "gh=", "noun"),
    "neos": GreekLearnerParadigmHint("neos", "νέος", "ne/os", "adjective"),
    "pais": GreekLearnerParadigmHint("pais", "παῖς", "pai=s", "noun"),
    "kardia": GreekLearnerParadigmHint("kardia", "καρδία", "kardi/a", "noun"),
    "pneuma": GreekLearnerParadigmHint("pneuma", "πνεῦμα", "pneu=ma", "noun"),
    "oikos": GreekLearnerParadigmHint("oikos", "οἶκος", "oi)=kos", "noun"),
    "adelphos": GreekLearnerParadigmHint("adelphos", "ἀδελφός", "a)delfo/s", "noun"),
    "boule": GreekLearnerParadigmHint("boule", "βουλή", "boulh/", "noun"),
    "boulē": GreekLearnerParadigmHint("boule", "βουλή", "boulh/", "noun"),
    "gyne": GreekLearnerParadigmHint("gyne", "γυνή", "gunh/", "noun"),
    "hippos": GreekLearnerParadigmHint("hippos", "ἵππος", "i(/ppos", "noun"),
    "gramma": GreekLearnerParadigmHint("gramma", "γράμμα", "gra/mma", "noun"),
    "kleos": GreekLearnerParadigmHint("kleos", "κλέος", "kle/os", "noun"),
    "paideia": GreekLearnerParadigmHint("paideia", "παιδεία", "paidei/a", "noun"),
    "soma": GreekLearnerParadigmHint("soma", "σῶμα", "sw=ma", "noun"),
    "naus": GreekLearnerParadigmHint("naus", "ναῦς", "nau=s", "noun"),
    "bios": GreekLearnerParadigmHint("bios", "βίος", "bi/os", "noun"),
    "thugater": GreekLearnerParadigmHint("thugater", "θυγάτηρ", "quga/thr", "noun"),
    "thugatēr": GreekLearnerParadigmHint("thugater", "θυγάτηρ", "quga/thr", "noun"),
}

_CORE_MOTD_KEYS = frozenset(
    {
        "logos",
        "sophos",
        "nomos",
        "didaskalos",
        "dike",
        "psyche",
        "mikros",
        "thalassa",
        "mathetes",
        "chara",
        "kardia",
        "pneuma",
        "oikos",
        "adelphos",
        "boule",
        "gyne",
        "hippos",
        "gramma",
        "kleos",
        "paideia",
        "soma",
        "naus",
        "bios",
        "thugater",
        "thugatēr",
    }
)


def greek_learner_paradigm_hint(text: str) -> GreekLearnerParadigmHint | None:
    key = _hint_key(text)
    if not key:
        return None
    return _HINTS.get(key)


def greek_learner_paradigm_record(text: str) -> dict[str, object] | None:
    hint = greek_learner_paradigm_hint(text)
    if hint is None:
        return None
    return {
        "language": "grc",
        "normalized_form": hint.learner_key,
        "lemma": hint.lemma,
        "source_key": hint.source_key,
        "part_of_speech": hint.part_of_speech,
        "source": hint.source,
    }


def is_unresolved_greek_learner_key(text: str) -> bool:
    key = _hint_key(text)
    return bool(key and key.isascii() and greek_learner_paradigm_hint(key) is None)


def greek_learner_paradigm_priority(text: str) -> int:
    key = _hint_key(text)
    if not key:
        return 2
    if key in _CORE_MOTD_KEYS:
        return 0
    if key in _HINTS:
        return 1
    return 2


def _hint_key(text: str) -> str:
    cleaned = text.strip().casefold()
    if not cleaned:
        return ""
    greekish = normalize_greekish_token(cleaned)
    key = greekish or cleaned
    key = key.replace("ē", "e").replace("ê", "e").replace("ō", "o").replace("ô", "o")
    return re.sub(r"[^a-z]+", "", key)
