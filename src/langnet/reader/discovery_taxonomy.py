from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryTaxonomyEntry:
    id: str
    label: str
    description: str


def _entry(taxonomy_id: str, label: str, description: str) -> DiscoveryTaxonomyEntry:
    return DiscoveryTaxonomyEntry(
        id=taxonomy_id,
        label=label,
        description=description,
    )


DISCOVERY_GROUPS: dict[str, DiscoveryTaxonomyEntry] = {
    entry.id: entry
    for entry in (
        _entry("epic", "Epic", "Epic and large-scale heroic narrative traditions."),
        _entry("drama", "Drama", "Performed or performable dramatic works."),
        _entry("poetry", "Poetry", "Verse works not better grouped as epic, drama, or hymn."),
        _entry("hymn", "Hymn", "Hymnic, praise, devotional, or liturgical verse."),
        _entry("narrative", "Narrative", "Prose or mixed narrative works and story collections."),
        _entry(
            "history", "History", "Historical narrative, chronography, and antiquarian history."
        ),
        _entry("biography", "Biography", "Lives, hagiography, and biographical collections."),
        _entry("rhetoric", "Rhetoric", "Speeches, oratory, rhetorical handbooks, and declamation."),
        _entry(
            "grammar",
            "Grammar",
            "Grammar, linguistic analysis, philology, and language instruction.",
        ),
        _entry(
            "lexicography",
            "Lexicography",
            "Dictionaries, glossaries, word lists, and lexical reference works.",
        ),
        _entry(
            "philosophy",
            "Philosophy",
            "Philosophical argument, logic, metaphysics, and system-building.",
        ),
        _entry("ethics", "Ethics", "Conduct, duty, virtue, discipline, and moral instruction."),
        _entry(
            "law", "Law", "Courts, codes, legal procedure, jurisprudence, and legal interpretation."
        ),
        _entry("medicine", "Medicine", "Medical, surgical, diagnostic, and health-related works."),
        _entry("religion", "Religion", "Theology, scripture, exegesis, and religious instruction."),
        _entry("ritual", "Ritual", "Ritual procedure, liturgy, sacrifice, rite, and ceremony."),
        _entry(
            "poetics", "Poetics", "Literary theory, metrics, aesthetics, dramaturgy, and criticism."
        ),
        _entry(
            "astronomy",
            "Astronomy",
            "Astronomy, calendrics, celestial computation, and astronomical theory.",
        ),
        _entry("astrology", "Astrology", "Astrology, horoscopy, and astral divination."),
        _entry(
            "mathematics",
            "Mathematics",
            "Mathematics, geometry, arithmetic, and mathematical exposition.",
        ),
        _entry(
            "science",
            "Science",
            "Natural history, mechanics, geography, agriculture, and technical science.",
        ),
        _entry(
            "technical",
            "Technical",
            "Manuals and technical treatises outside the more specific groups.",
        ),
        _entry(
            "commentary", "Commentary", "Commentaries and scholia grouped by explanatory function."
        ),
        _entry("letter", "Letter", "Letters and epistolary collections."),
        _entry("inscription", "Inscription", "Inscriptions and epigraphic texts."),
        _entry(
            "fragmentary",
            "Fragmentary",
            "Fragmentary or excerpted works with no clearer peer group.",
        ),
        _entry("anthology", "Anthology", "Anthologies, miscellanies, collections, and compendia."),
        _entry("other", "Other", "Works with no clearer controlled group."),
        _entry("uncertain", "Uncertain", "Works with insufficient evidence for a reliable group."),
    )
}


DISCOVERY_TAGS: dict[str, DiscoveryTaxonomyEntry] = {
    entry.id: entry
    for entry in (
        _entry("ayurveda", "Ayurveda", "Sanskrit medical tradition."),
        _entry(
            "dharmashastra",
            "Dharmashastra",
            "Sanskrit dharma, conduct, duty, penance, and social order.",
        ),
        _entry("dharmasutra", "Dharmasutra", "Dharmasutra literature."),
        _entry(
            "arthashastra",
            "Arthashastra",
            "Statecraft, polity, administration, economics, and political power.",
        ),
        _entry("kamashastra", "Kamashastra", "Erotics, pleasure, and the science of kama."),
        _entry(
            "rasashastra",
            "Rasashastra",
            "Alchemy, iatrochemistry, mineral and metallurgical medicine.",
        ),
        _entry("ratnashastra", "Ratnashastra", "Gemological and jewel-science literature."),
        _entry("vyakarana", "Vyakarana", "Sanskrit grammatical tradition."),
        _entry("paniniya", "Paniniya", "Paninian grammatical tradition."),
        _entry("nirukta", "Nirukta", "Vedic etymology and semantic explanation."),
        _entry("kosha", "Kosha", "Sanskrit lexicon, thesaurus, glossary, or word-list tradition."),
        _entry("nighantu", "Nighantu", "Nighantu lexical or medicinal glossary tradition."),
        _entry("kavya", "Kavya", "Sanskrit ornate or literary poetry and prose."),
        _entry("katha", "Katha", "Sanskrit story, tale, and narrative-prose tradition."),
        _entry("natya", "Natya", "Sanskrit drama, dramaturgy, and performance theory."),
        _entry(
            "alamkarashastra",
            "Alamkarashastra",
            "Sanskrit poetics and figures-of-speech tradition.",
        ),
        _entry("sahityashastra", "Sahityashastra", "Sanskrit literary theory tradition."),
        _entry("itihasa", "Itihasa", "Sanskrit epic or historical narrative tradition."),
        _entry("mahabharata", "Mahabharata", "Mahabharata or directly related works."),
        _entry("ramayana", "Ramayana", "Ramayana or directly related works."),
        _entry("purana", "Purana", "Puranic literature."),
        _entry("vedic", "Vedic", "Vedic period or Vedic-tradition material."),
        _entry("veda", "Veda", "Vedic texts and Vedic textual traditions."),
        _entry("rgveda", "Rgveda", "Rigvedic texts and directly related materials."),
        _entry("yajurveda", "Yajurveda", "Yajurvedic texts and directly related materials."),
        _entry("samaveda", "Samaveda", "Samavedic texts and directly related materials."),
        _entry(
            "atharvaveda",
            "Atharvaveda",
            "Atharvavedic texts and directly related materials.",
        ),
        _entry("brahmana", "Brahmana", "Brahmana literature."),
        _entry("aranyaka", "Aranyaka", "Aranyaka literature."),
        _entry("upanishad", "Upanishad", "Upanishadic literature."),
        _entry("kalpa", "Kalpa", "Vedic ritual and procedural literature."),
        _entry("grhyasutra", "Grhyasutra", "Domestic ritual sutra literature."),
        _entry(
            "shrautasutra",
            "Shrautasutra",
            "Public sacrificial ritual sutra literature.",
        ),
        _entry("samhita", "Samhita", "Samhita textual collections."),
        _entry("smriti", "Smriti", "Remembered tradition and smriti literature."),
        _entry("sutra", "Sutra", "Sutra-form technical or scholastic literature."),
        _entry("bhashya", "Bhashya", "Bhashya commentary literature."),
        _entry("vedanta", "Vedanta", "Vedanta tradition."),
        _entry("nyaya", "Nyaya", "Nyaya logic and epistemology tradition."),
        _entry("samkhya", "Samkhya", "Samkhya tradition."),
        _entry("yoga", "Yoga", "Yoga tradition."),
        _entry("mimamsa", "Mimamsa", "Mimamsa tradition."),
        _entry("vaisheshika", "Vaisheshika", "Vaisheshika tradition."),
        _entry("buddhist", "Buddhist", "Buddhist literature or tradition."),
        _entry("buddhist_sutra", "Buddhist Sutra", "Buddhist sutra or scriptural literature."),
        _entry(
            "buddhist_abhidharma",
            "Buddhist Abhidharma",
            "Abhidharma and related scholastic Buddhist literature.",
        ),
        _entry("buddhist_tantra", "Buddhist Tantra", "Buddhist tantric literature."),
        _entry("jain", "Jain", "Jain literature or tradition."),
        _entry("tantra", "Tantra", "Tantric literature broadly."),
        _entry("shaiva", "Shaiva", "Shaiva literature or tradition."),
        _entry("bhakti", "Bhakti", "Devotional literature and bhakti traditions."),
        _entry("stotra", "Stotra", "Praise hymns and devotional stotra literature."),
        _entry("patristics", "Patristics", "Christian patristic literature."),
        _entry("roman_law", "Roman Law", "Roman legal tradition."),
        _entry(
            "hippocratic_galenic_medicine",
            "Hippocratic/Galenic Medicine",
            "Hippocratic, Galenic, or related Greek/Roman medicine.",
        ),
        _entry("epic", "Epic", "Epic and large-scale heroic narrative traditions."),
        _entry("drama", "Drama", "Performed or performable dramatic works."),
        _entry("poetry", "Poetry", "Verse works not better grouped as epic, drama, or hymn."),
        _entry("hymn", "Hymn", "Hymnic, praise, devotional, or liturgical verse."),
        _entry("narrative", "Narrative", "Prose or mixed narrative works and story collections."),
        _entry("oratory", "Oratory", "Oratory and speech performance."),
        _entry("speech", "Speech", "Individual speeches or speech collections."),
        _entry("tragedy", "Tragedy", "Tragic drama."),
        _entry("comedy", "Comedy", "Comic drama."),
        _entry("satire", "Satire", "Satire as a recurring literary discovery bucket."),
        _entry("elegy", "Elegy", "Elegiac poetry."),
        _entry("lyric", "Lyric", "Lyric poetry."),
        _entry("epigram", "Epigram", "Epigrammatic poetry."),
        _entry("didactic", "Didactic", "Didactic or instructional poetry."),
        _entry("pastoral", "Pastoral", "Pastoral or bucolic poetry."),
        _entry("hagiography", "Hagiography", "Saints' lives and holy biographies."),
        _entry("homily", "Homily", "Homilies and sermons."),
        _entry("apology", "Apology", "Apologetic works."),
        _entry("commentary", "Commentary", "Commentary, explanation, or exegetical works."),
        _entry("scholia", "Scholia", "Scholia and scholastic notes."),
        _entry(
            "fragmentary", "Fragmentary", "Fragmentary, excerpted, or unrecoverably partial texts."
        ),
        _entry("inscription", "Inscription", "Epigraphic material."),
        _entry("technical", "Technical", "Technical or manual-like works."),
        _entry("ethics", "Ethics", "Conduct, duty, virtue, discipline, and moral instruction."),
        _entry(
            "law", "Law", "Legal procedure, codes, courts, jurisprudence, or legal interpretation."
        ),
        _entry("medicine", "Medicine", "Medical and health-related material."),
        _entry("grammar", "Grammar", "Grammar and linguistic analysis."),
        _entry("lexicography", "Lexicography", "Lexical reference material."),
        _entry("rhetoric", "Rhetoric", "Rhetoric and rhetorical education."),
        _entry("philosophy", "Philosophy", "Philosophical argument or tradition."),
        _entry("religion", "Religion", "Religious doctrine, theology, or scripture."),
        _entry("ritual", "Ritual", "Ritual practice or ceremonial procedure."),
        _entry("poetics", "Poetics", "Poetics, metrics, aesthetics, or criticism."),
        _entry("astronomy", "Astronomy", "Astronomy and calendrics."),
        _entry("astrology", "Astrology", "Astrology, horoscopy, and astral divination."),
        _entry(
            "jyotisha",
            "Jyotisha",
            "Sanskrit astral science, astronomy, astrology, and calendrics.",
        ),
        _entry("mathematics", "Mathematics", "Mathematics and geometry."),
        _entry("science", "Science", "Natural or technical science outside more specific groups."),
        _entry("history", "History", "Historical narrative or chronography."),
        _entry("biography", "Biography", "Biography and lives."),
        _entry("letter", "Letter", "Epistolary works."),
        _entry("anthology", "Anthology", "Anthologies and miscellanies."),
    )
}


def discovery_group_label(group_id: str) -> str:
    group = DISCOVERY_GROUPS.get(group_id)
    return group.label if group else ""


def discovery_group_allowed_values() -> list[dict[str, str]]:
    return _allowed_values(DISCOVERY_GROUPS)


def discovery_tag_allowed_values() -> list[dict[str, str]]:
    return _allowed_values(DISCOVERY_TAGS)


def normalize_discovery_tags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_values: Sequence[object] = value.split("|")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        raw_values = value
    elif isinstance(value, set):
        raw_values = sorted(value)
    else:
        raw_values = (str(value),)
    tags: list[str] = []
    for raw_value in raw_values:
        tag = str(raw_value).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tuple(tags)


def discovery_tags_to_csv(value: object) -> str:
    return "|".join(normalize_discovery_tags(value))


def validate_discovery_group_id(value: str) -> str:
    group_id = value.strip()
    if group_id and group_id in DISCOVERY_GROUPS:
        return group_id
    msg = f"unknown discovery group {value!r}"
    raise ValueError(msg)


def validate_discovery_tags(values: Iterable[str]) -> tuple[str, ...]:
    tags: list[str] = []
    for tag in values:
        clean_tag = tag.strip()
        if not clean_tag:
            continue
        if clean_tag not in DISCOVERY_TAGS:
            msg = f"unknown discovery tag {tag!r}"
            raise ValueError(msg)
        if clean_tag not in tags:
            tags.append(clean_tag)
    return tuple(tags)


def validate_discovery_tag_csv(value: object) -> str:
    return "|".join(validate_discovery_tags(normalize_discovery_tags(value)))


def _allowed_values(
    entries: Mapping[str, DiscoveryTaxonomyEntry],
) -> list[dict[str, str]]:
    return [
        {"id": entry.id, "label": entry.label, "description": entry.description}
        for entry in entries.values()
    ]
