from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GrammarConceptEvidence:
    evidence_level: str
    source_anchor_id: str
    work_id: str
    canonical_text_id: str
    cts_work_urn: str | None = None
    citation_path: str | None = None
    canonical_address: str | None = None
    label: str = ""


@dataclass(frozen=True)
class GrammarConcept:
    id: str
    kind: str
    foster_gateway: str
    plain_english: str
    traditional: dict[str, str] = field(default_factory=dict)
    applies_to: list[str] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)
    source_basis: list[str] = field(default_factory=list)
    evidence: list[GrammarConceptEvidence] = field(default_factory=list)
    examples: dict[str, str] = field(default_factory=dict)
    skills: dict[str, str] = field(default_factory=dict)


def load_grammar_concepts() -> dict[str, GrammarConcept]:
    return {concept.id: concept for concept in _CONCEPTS}


def get_grammar_concept(concept_id: str) -> GrammarConcept:
    concepts = load_grammar_concepts()
    try:
        return concepts[concept_id]
    except KeyError as exc:
        raise KeyError(f"unknown grammar concept: {concept_id}") from exc


_CASE_SOURCE_BASIS = [
    "Smyth Greek Grammar",
    "Allen and Greenough Latin Grammar",
    "Whitney Sanskrit Grammar",
    "Sanskrit kāraka/vibhakti grammatical tradition",
]

_VARRO_DE_LINGUA_LATINA = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.varro.de_lingua_latina",
    work_id="langnet:reader:phi:lat0684.001",
    cts_work_urn="urn:cts:latinLit:phi0684.phi001",
    canonical_text_id="urn:ctsv2:lat:de-lingua-latina-de-lingva-latina",
    canonical_address="urn:ctsv2:lat:de-lingua-latina-de-lingva-latina",
    label="Varro, De Lingua Latina",
)
_DONATUS_ARS_MINOR = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    label="Aelius Donatus, Ars minor",
)
_DONATUS_ARS_MAIOR = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.donatus.ars_maior",
    work_id="langnet:reader:digiliblt:dlt000156",
    canonical_text_id="urn:ctsv2:lat:ars-maior-de-uoce",
    canonical_address="urn:ctsv2:lat:ars-maior-de-uoce",
    label="Aelius Donatus, Ars maior",
)
_DOSITHEUS_ARS_GRAMMATICA = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.dositheus.ars_grammatica",
    work_id="langnet:reader:digiliblt:dlt000159",
    canonical_text_id="urn:ctsv2:lat:ars-grammatica-ars-grammatica-est",
    canonical_address="urn:ctsv2:lat:ars-grammatica-ars-grammatica-est",
    label="Dositheus, Ars Grammatica",
)
_PRISCIAN_INSTITUTIONES = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.priscian.institutiones",
    work_id="langnet:reader:digiliblt:dlt000425",
    canonical_text_id="urn:ctsv2:lat:institutiones-siue-ars-priscianus-caesariensis-grammaticus",
    canonical_address="urn:ctsv2:lat:institutiones-siue-ars-priscianus-caesariensis-grammaticus",
    label="Priscian, Institutiones siue Ars",
)
_DONATUS_CASE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="76",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=76",
    label=(
        "Aelius Donatus, Ars minor: nominatiuus, genetiuus, datiuus, "
        "accusatiuus, uocatiuus, ablatiuus"
    ),
)
_DONATUS_NUMBER_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="7",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=7",
    label="Aelius Donatus, Ars minor: singularis, ut hic magister; pluralis, ut hi magistri",
)
_DONATUS_GENDER_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="18",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=18",
    label="Aelius Donatus, Ars minor: masculinum, ut quis; femininum, ut quae",
)
_DONATUS_NOUN_GENDER_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="6",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=6",
    label="Aelius Donatus, Ars minor: masculinum, femininum, neutrum",
)
_DONATUS_INDICATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="38",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=38",
    label="Aelius Donatus, Ars minor: indicatiuus, ut lego",
)
_DONATUS_ACTIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="43",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=43",
    label="Aelius Donatus, Ars minor: actiua quae sunt? ... ut lego, legor",
)
_DONATUS_PASSIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_minor",
    work_id="langnet:reader:digiliblt:dlt000157",
    canonical_text_id="urn:ctsv2:lat:ars-minor-de-partibus-orationis",
    citation_path="44",
    canonical_address="urn:ctsv2:lat:ars-minor-de-partibus-orationis?ref=44",
    label="Aelius Donatus, Ars minor: passiua quae sunt? ... ut legor, lego",
)
_DONATUS_FIRST_PERSON_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_maior",
    work_id="langnet:reader:digiliblt:dlt000156",
    canonical_text_id="urn:ctsv2:lat:ars-maior-de-uoce",
    citation_path="112",
    canonical_address="urn:ctsv2:lat:ars-maior-de-uoce?ref=112",
    label="Aelius Donatus, Ars maior: prima est, quae dicit lego",
)
_DONATUS_CASE_LIST_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.donatus.ars_maior",
    work_id="langnet:reader:digiliblt:dlt000156",
    canonical_text_id="urn:ctsv2:lat:ars-maior-de-uoce",
    citation_path="68",
    canonical_address="urn:ctsv2:lat:ars-maior-de-uoce?ref=68",
    label=(
        "Aelius Donatus, Ars maior: casus sunt sex, nominatiuus, genetiuus, "
        "datiuus, accusatiuus, uocatiuus, ablatiuus"
    ),
)
_DOSITHEUS_PRESENT_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dositheus.ars_grammatica",
    work_id="langnet:reader:digiliblt:dlt000159",
    canonical_text_id="urn:ctsv2:lat:ars-grammatica-ars-grammatica-est",
    citation_path="35",
    canonical_address="urn:ctsv2:lat:ars-grammatica-ars-grammatica-est?ref=35",
    label="Dositheus, Ars Grammatica: Tempora uerborum III: praesens, praeteritum, futurum",
)
_PRISCIAN_CONJUGATION_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.priscian.institutiones",
    work_id="langnet:reader:digiliblt:dlt000425",
    canonical_text_id="urn:ctsv2:lat:institutiones-siue-ars-priscianus-caesariensis-grammaticus",
    citation_path="1743",
    canonical_address=(
        "urn:ctsv2:lat:institutiones-siue-ars-priscianus-caesariensis-grammaticus?ref=1743"
    ),
    label="Priscian, Institutiones siue Ars: coniugatio est consequens uerborum declinatio",
)
_DIONYSIUS_ARS_GRAMMATICA = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    label="Dionysius Thrax, Ars grammatica",
)
_DIONYSIUS_GENITIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.31.7",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.31.7",
    label="Dionysius Thrax, Ars grammatica: δὲ γενικὴ κτητική τε καὶ πατρική",
)
_DIONYSIUS_GENDER_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.24.8",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.24.8",
    label="Dionysius Thrax, Ars grammatica: Γένη μὲν οὖν εἰςι τρία· ἀρςενικόν, θηλυκόν, οὐδέτερον",
)
_DIONYSIUS_NOMINATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.31.6",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.31.6",
    label="Dionysius Thrax, Ars grammatica: ἡ μὲν ὀρθὴ ὀνομαςτικὴ καὶ εὐθεῖα",
)
_DIONYSIUS_DATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.31.7",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.31.7",
    label="Dionysius Thrax, Ars grammatica: ἡ δὲ δοτικὴ ἐπιςταλτική",
)
_DIONYSIUS_ACCUSATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.32.1",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.32.1",
    label="Dionysius Thrax, Ars grammatica: ἡ δὲ αἰτιατικὴ κατ' αἰτιατικήν",
)
_DIONYSIUS_VOCATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.32.1",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.32.1",
    label="Dionysius Thrax, Ars grammatica: ἡ δὲ κλητικὴ προσρητική",
)
_DIONYSIUS_SINGULAR_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.30.5",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.30.5",
    label="Dionysius Thrax, Ars grammatica: Ἀριθμοὶ τρεῖς· ἑνικός, δυϊκός, πληθυντικός",
)
_DIONYSIUS_PLURAL_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.31.1",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.31.1",
    label="Dionysius Thrax, Ars grammatica: πληθυντικὸς δὲ <οἱ Ὅμηροι>",
)
_DIONYSIUS_INDICATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.47.3",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.47.3",
    label="Dionysius Thrax, Ars grammatica: Ἐγκλίςεις μὲν οὖν εἰςι πέντε, ὁριςτική",
)
_DIONYSIUS_ACTIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.48.1",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.48.1",
    label="Dionysius Thrax, Ars grammatica: Διαθέςεις εἰςὶ τρεῖς, ἐνέργεια, πάθος, μεςότης",
)
_DIONYSIUS_PASSIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.49.1",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.49.1",
    label="Dionysius Thrax, Ars grammatica: πάθος δὲ οἷον <τύπτομαι>",
)
_DIONYSIUS_FIRST_PERSON_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.51.4",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.51.4",
    label="Dionysius Thrax, Ars grammatica: Πρόςωπα τρία, πρῶτον, δεύτερον, τρίτον",
)
_DIONYSIUS_PRESENT_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.53.1",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.53.1",
    label="Dionysius Thrax, Ars grammatica: Χρόνοι τρεῖς, ἐνεςτώς, παρεληλυθώς, μέλλων",
)
_DIONYSIUS_CONJUGATION_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.dionysius_thrax.ars_grammatica",
    work_id="langnet:reader:tlg:tlg0063.001",
    cts_work_urn="urn:cts:greekLit:tlg0063.tlg001",
    canonical_text_id="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s",
    citation_path="1.1.53.6",
    canonical_address="urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.53.6",
    label="Dionysius Thrax, Ars grammatica: Συζυγία ἐςτὶν ἀκόλουθος ῥημάτων κλίςις",
)
_APOLLONIUS_SYNTAX = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.apollonius_dyscolus.syntax",
    work_id="urn:cts:greekLit:tlg0082.tlg004",
    cts_work_urn="urn:cts:greekLit:tlg0082.tlg004",
    canonical_text_id="urn:ctsv2:grc:peri-suntaxeos-en-tais-proekdotheisais",
    canonical_address="urn:ctsv2:grc:peri-suntaxeos-en-tais-proekdotheisais",
    label="Apollonius Dyscolus, Περὶ συντάξεως",
)
_PANINI_ASTADHYAYI = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    label="Pāṇini, Aṣṭādhyāyī",
)
_PANINI_VRDDHI_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="550728",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550728",
    label="Pāṇini, Aṣṭādhyāyī: vṛddhir ādaic",
)
_PANINI_GUNA_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="550729",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550729",
    label="Pāṇini, Aṣṭādhyāyī: adeṅ guṇaḥ",
)
_PANINI_SAVARNA_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="550736",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550736",
    label="Pāṇini, Aṣṭādhyāyī: tulyāsyaprayatnaṃ savarṇam",
)
_PANINI_GENITIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551238",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551238",
    label="Pāṇini, Aṣṭādhyāyī: ṣaṣṭhī śeṣe",
)
_PANINI_NOMINATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551234",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551234",
    label="Pāṇini, Aṣṭādhyāyī: prātipadikārthaliṅgaparimāṇavacanamātre prathamā",
)
_PANINI_PLURAL_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="550989",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550989",
    label="Pāṇini, Aṣṭādhyāyī: bahuṣu bahuvacanam",
)
_PANINI_SINGULAR_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="550990",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550990",
    label="Pāṇini, Aṣṭādhyāyī: dvyekayor dvivacanaikavacane",
)
_PANINI_DATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551201",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551201",
    label="Pāṇini, Aṣṭādhyāyī: caturthī sampradāne",
)
_PANINI_ACCUSATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551190",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551190",
    label="Pāṇini, Aṣṭādhyāyī: karmaṇi dvitīyā",
)
_PANINI_VOCATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551237",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551237",
    label="Pāṇini, Aṣṭādhyāyī: ekavacanaṃ sambuddhiḥ",
)
_PANINI_ABLATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551216",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551216",
    label="Pāṇini, Aṣṭādhyāyī: apādāne pañcamī",
)
_PANINI_INSTRUMENTAL_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551206",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551206",
    label="Pāṇini, Aṣṭādhyāyī: kartṛkaraṇayos tṛtīyā",
)
_PANINI_LOCATIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551224",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551224",
    label="Pāṇini, Aṣṭādhyāyī: saptamyadhikarane ca",
)
_PANINI_NEUTER_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="550849",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550849",
    label="Pāṇini, Aṣṭādhyāyī: hrasvo napuṃsake prātipadikasya",
)
_PANINI_PASSIVE_SEGMENT = GrammarConceptEvidence(
    evidence_level="reader_segment",
    source_anchor_id="grammar.source.panini.astadhyayi",
    work_id="langnet:reader:sanskrit_dcs:dcs_413",
    canonical_text_id="urn:ctsv2:san:astadhyayi-vrddhir-adaic",
    citation_path="551412",
    canonical_address="urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551412",
    label="Pāṇini, Aṣṭādhyāyī: ciṇ bhāvakarmaṇoḥ",
)
_KASIKAVRTTI = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.kasikavrtti",
    work_id="langnet:reader:sanskrit_dcs:dcs_412",
    canonical_text_id="urn:ctsv2:san:kasikavrtti-vrddhisabdah-samjnatvena-vidhiyate",
    canonical_address="urn:ctsv2:san:kasikavrtti-vrddhisabdah-samjnatvena-vidhiyate",
    label="Kāśikāvṛtti",
)
_HERODIAN_NOUN_INFLECTION = GrammarConceptEvidence(
    evidence_level="reader_work",
    source_anchor_id="grammar.source.herodian.noun_inflection",
    work_id="urn:cts:greekLit:tlg0087.tlg013",
    cts_work_urn="urn:cts:greekLit:tlg0087.tlg013",
    canonical_text_id="urn:ctsv2:grc:peri-kliseos-onomaton-anecd-ox-iv",
    canonical_address="urn:ctsv2:grc:peri-kliseos-onomaton-anecd-ox-iv",
    label="Herodianus, Περὶ κλίσεως ὀνομάτων",
)

_CORE_TERM_EVIDENCE = [
    _DIONYSIUS_ARS_GRAMMATICA,
    _VARRO_DE_LINGUA_LATINA,
    _DONATUS_ARS_MINOR,
    _PANINI_ASTADHYAYI,
]
_CASE_EVIDENCE = [
    _DIONYSIUS_ARS_GRAMMATICA,
    _VARRO_DE_LINGUA_LATINA,
    _DONATUS_ARS_MINOR,
    _PANINI_ASTADHYAYI,
    _KASIKAVRTTI,
]
_GENITIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_GENITIVE_SEGMENT,
    _DIONYSIUS_GENITIVE_SEGMENT,
    _DONATUS_CASE_SEGMENT,
]
_NOMINATIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_NOMINATIVE_SEGMENT,
    _DIONYSIUS_NOMINATIVE_SEGMENT,
    _DONATUS_CASE_SEGMENT,
]
_DATIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_DATIVE_SEGMENT,
    _DIONYSIUS_DATIVE_SEGMENT,
    _DONATUS_CASE_SEGMENT,
]
_ACCUSATIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_ACCUSATIVE_SEGMENT,
    _DIONYSIUS_ACCUSATIVE_SEGMENT,
    _DONATUS_CASE_SEGMENT,
]
_VOCATIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_VOCATIVE_SEGMENT,
    _DIONYSIUS_VOCATIVE_SEGMENT,
    _DONATUS_CASE_SEGMENT,
    _DONATUS_ARS_MAIOR,
    _DONATUS_CASE_LIST_SEGMENT,
]
_ABLATIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_ABLATIVE_SEGMENT,
    _DONATUS_CASE_SEGMENT,
    _DONATUS_ARS_MAIOR,
    _DONATUS_CASE_LIST_SEGMENT,
]
_INSTRUMENTAL_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_INSTRUMENTAL_SEGMENT,
]
_LOCATIVE_EVIDENCE = [
    *_CASE_EVIDENCE,
    _PANINI_LOCATIVE_SEGMENT,
]
_SINGULAR_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _PANINI_SINGULAR_SEGMENT,
    _DIONYSIUS_SINGULAR_SEGMENT,
    _DONATUS_NUMBER_SEGMENT,
]
_PLURAL_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _PANINI_PLURAL_SEGMENT,
    _DIONYSIUS_PLURAL_SEGMENT,
    _DONATUS_NUMBER_SEGMENT,
]
_DUAL_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _PANINI_SINGULAR_SEGMENT,
    _DIONYSIUS_SINGULAR_SEGMENT,
]
_MASCULINE_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _DIONYSIUS_GENDER_SEGMENT,
    _DONATUS_GENDER_SEGMENT,
]
_FEMININE_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _DIONYSIUS_GENDER_SEGMENT,
    _DONATUS_GENDER_SEGMENT,
]
_NEUTER_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _DIONYSIUS_GENDER_SEGMENT,
    _DONATUS_NOUN_GENDER_SEGMENT,
    _PANINI_NEUTER_SEGMENT,
]
_DECLENSION_EVIDENCE = [
    _DIONYSIUS_ARS_GRAMMATICA,
    _VARRO_DE_LINGUA_LATINA,
    _DONATUS_ARS_MINOR,
    _HERODIAN_NOUN_INFLECTION,
    _PANINI_ASTADHYAYI,
    _KASIKAVRTTI,
]
_CONJUGATION_WORK_EVIDENCE = [
    _DIONYSIUS_ARS_GRAMMATICA,
    _VARRO_DE_LINGUA_LATINA,
    _DONATUS_ARS_MINOR,
    _PANINI_ASTADHYAYI,
    _KASIKAVRTTI,
]
_PRESENT_EVIDENCE = [
    *_CONJUGATION_WORK_EVIDENCE,
    _DIONYSIUS_PRESENT_SEGMENT,
    _DOSITHEUS_ARS_GRAMMATICA,
    _DOSITHEUS_PRESENT_SEGMENT,
]
_INDICATIVE_EVIDENCE = [
    *_CONJUGATION_WORK_EVIDENCE,
    _DIONYSIUS_INDICATIVE_SEGMENT,
    _DONATUS_INDICATIVE_SEGMENT,
]
_ACTIVE_EVIDENCE = [
    *_CONJUGATION_WORK_EVIDENCE,
    _DIONYSIUS_ACTIVE_SEGMENT,
    _DONATUS_ACTIVE_SEGMENT,
]
_PASSIVE_EVIDENCE = [
    *_CONJUGATION_WORK_EVIDENCE,
    _DIONYSIUS_PASSIVE_SEGMENT,
    _DONATUS_PASSIVE_SEGMENT,
    _PANINI_PASSIVE_SEGMENT,
]
_FIRST_PERSON_EVIDENCE = [
    *_CORE_TERM_EVIDENCE,
    _DIONYSIUS_FIRST_PERSON_SEGMENT,
    _DONATUS_ARS_MAIOR,
    _DONATUS_FIRST_PERSON_SEGMENT,
]
_CONJUGATION_EVIDENCE = [
    *_CONJUGATION_WORK_EVIDENCE,
    _DIONYSIUS_CONJUGATION_SEGMENT,
    _PRISCIAN_INSTITUTIONES,
    _PRISCIAN_CONJUGATION_SEGMENT,
]
_GUNA_EVIDENCE = [
    _PANINI_ASTADHYAYI,
    _PANINI_GUNA_SEGMENT,
    _KASIKAVRTTI,
]
_VRDDHI_EVIDENCE = [
    _PANINI_ASTADHYAYI,
    _PANINI_VRDDHI_SEGMENT,
    _KASIKAVRTTI,
]
_SAVARNA_EVIDENCE = [
    _PANINI_ASTADHYAYI,
    _PANINI_SAVARNA_SEGMENT,
    _KASIKAVRTTI,
]

_NUMBER_SINGULAR_SKILLS = {
    "read": "Recognize that the form refers to one item, person, or action.",
    "understand": "Connect the singular marker to a single participant or event.",
    "learn": "Map Single to singular terminology across traditions.",
    "write": "Choose singular agreement in controlled noun or verb prompts.",
}
_NUMBER_PLURAL_SKILLS = {
    "read": "Recognize that the form refers to more than one item, person, or action.",
    "understand": "Connect the plural marker to a group participant or repeated action.",
    "learn": "Map Group to plural terminology across traditions.",
    "write": "Choose plural agreement in controlled noun or verb prompts.",
}
_NUMBER_DUAL_SKILLS = {
    "read": "Recognize that the form refers to exactly two items, persons, or actions.",
    "understand": "Connect the dual marker to a pair rather than one item or a group.",
    "learn": "Map Pair to dual terminology where the language tradition uses it.",
    "write": "Choose dual agreement in controlled prompts for paired participants.",
}
_GENDER_MASCULINE_SKILLS = {
    "read": "Recognize masculine agreement on nouns, adjectives, and pronouns.",
    "understand": "Use masculine gender to connect agreeing words.",
    "learn": "Map Male to masculine grammatical terminology.",
    "write": "Choose masculine agreement in controlled prompts.",
}
_GENDER_FEMININE_SKILLS = {
    "read": "Recognize feminine agreement on nouns, adjectives, and pronouns.",
    "understand": "Use feminine gender to connect agreeing words.",
    "learn": "Map Female to feminine grammatical terminology.",
    "write": "Choose feminine agreement in controlled prompts.",
}
_GENDER_NEUTER_SKILLS = {
    "read": "Recognize neuter agreement on nouns, adjectives, and pronouns.",
    "understand": "Use neuter gender to connect agreeing words.",
    "learn": "Map Neither to neuter grammatical terminology.",
    "write": "Choose neuter agreement in controlled prompts.",
}
_TENSE_PRESENT_SKILLS = {
    "read": "Recognize forms presenting action as current, general, or ongoing.",
    "understand": "Connect present tense to the time or aspect of the action.",
    "learn": "Map Time-Now to present-tense terminology.",
    "write": "Choose a present form in controlled verb prompts.",
}
_MOOD_INDICATIVE_SKILLS = {
    "read": "Recognize ordinary statement and question forms.",
    "understand": "Connect indicative mood to assertion or direct inquiry.",
    "learn": "Map Statement to indicative terminology.",
    "write": "Choose indicative forms for controlled assertions.",
}
_VOICE_ACTIVE_SKILLS = {
    "read": "Recognize forms presenting the subject as doing the action.",
    "understand": "Connect active voice to an agent-oriented clause.",
    "learn": "Map Doing to active-voice terminology.",
    "write": "Choose active forms for controlled agent prompts.",
}
_VOICE_PASSIVE_SKILLS = {
    "read": "Recognize forms presenting the subject as undergoing the action.",
    "understand": "Connect passive voice to a patient- or result-oriented clause.",
    "learn": "Map Undergoing to passive-voice terminology.",
    "write": "Choose passive forms for controlled patient prompts.",
}
_PERSON_FIRST_SKILLS = {
    "read": "Recognize forms referring to the speaker or speaker's group.",
    "understand": "Connect first person to who is speaking.",
    "learn": "Map Speaker to first-person terminology.",
    "write": "Choose first-person forms in controlled prompts.",
}

_CONCEPTS = [
    GrammarConcept(
        id="case.nominative",
        kind="case",
        foster_gateway="Naming Function",
        plain_english="Names the subject or main topic of a clause.",
        traditional={
            "en": "nominative",
            "grc": "ὀνομαστική",
            "lat": "nominativus",
            "san": "prathamā vibhakti",
            "san_role": "kartṛ when used for the agent/subject role",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_NOMINATIVE_EVIDENCE,
        examples={"grc": "λόγος", "lat": "puella", "san": "putraḥ"},
        skills={
            "read": "Look for the named subject or topic.",
            "understand": "Connect the form to what the sentence is about.",
            "learn": "Map Naming Function to nominative terminology.",
            "write": "Choose a nominative form for a controlled subject prompt.",
        },
    ),
    GrammarConcept(
        id="case.genitive",
        kind="case",
        foster_gateway="Possessing Function",
        plain_english="Marks belonging, association, source, description, or relation.",
        traditional={
            "en": "genitive",
            "grc": "γενική",
            "lat": "genetivus",
            "san": "ṣaṣṭhī vibhakti",
            "san_role": "sambandha",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_GENITIVE_EVIDENCE,
        examples={"grc": "λόγου", "lat": "puellae", "san": "putrāṇām"},
        skills={
            "read": "Recognize possession, association, or relation.",
            "understand": "Connect the form to what it belongs to or relates to.",
            "learn": "Map Possessing Function to genitive terminology.",
            "write": "Choose a genitive form in controlled relation prompts.",
        },
    ),
    GrammarConcept(
        id="case.dative",
        kind="case",
        foster_gateway="To-For Function",
        plain_english="Marks a recipient, goal, beneficiary, or reference point.",
        traditional={
            "en": "dative",
            "grc": "δοτική",
            "lat": "dativus",
            "san": "caturthī vibhakti",
            "san_role": "sampradāna",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_DATIVE_EVIDENCE,
        examples={"grc": "λόγῳ", "lat": "puellae", "san": "putrāya"},
        skills={
            "read": "Look for to, for, toward, or recipient relationships.",
            "understand": "Connect the form to who receives or benefits.",
            "learn": "Map To-For Function to dative terminology.",
            "write": "Choose a dative form for controlled recipient prompts.",
        },
    ),
    GrammarConcept(
        id="case.accusative",
        kind="case",
        foster_gateway="Receiving Function",
        plain_english="Marks what receives the action or the goal of motion.",
        traditional={
            "en": "accusative",
            "grc": "αἰτιατική",
            "lat": "accusativus",
            "san": "dvitīyā vibhakti",
            "san_role": "karman",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_ACCUSATIVE_EVIDENCE,
        examples={"grc": "λόγον", "lat": "puellam", "san": "putram"},
        skills={
            "read": "Look for the receiver of an action.",
            "understand": "Connect the form to the action's object or goal.",
            "learn": "Map Receiving Function to accusative terminology.",
            "write": "Choose an accusative form for controlled object prompts.",
        },
    ),
    GrammarConcept(
        id="case.vocative",
        kind="case",
        foster_gateway="Calling Function",
        plain_english="Marks direct address: the person or thing being called.",
        traditional={
            "en": "vocative",
            "grc": "κλητική",
            "lat": "vocativus",
            "san": "sambuddhi / sambodhana",
            "san_role": "direct address",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_VOCATIVE_EVIDENCE,
        examples={"grc": "λόγε", "lat": "domine", "san": "he putra"},
        skills={
            "read": "Look for the person or thing directly addressed.",
            "understand": "Separate direct address from the clause's subject or object.",
            "learn": "Map Calling Function to vocative terminology.",
            "write": "Choose a vocative form for controlled address prompts.",
        },
    ),
    GrammarConcept(
        id="case.ablative",
        kind="case",
        foster_gateway="From-By Function",
        plain_english="Marks separation, source, cause, comparison, or by/with relationships.",
        traditional={
            "en": "ablative",
            "grc": "source/separation often expressed with genitive or prepositions",
            "lat": "ablativus",
            "san": "pañcamī vibhakti",
            "san_role": "apādāna",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_ABLATIVE_EVIDENCE,
        examples={"lat": "puellā", "san": "grāmāt"},
        skills={
            "read": "Look for from, away from, because of, by, or with relationships.",
            "understand": "Connect the form to source, separation, cause, or means.",
            "learn": "Map From-By Function to ablative terminology.",
            "write": "Choose an ablative form in controlled source or means prompts.",
        },
    ),
    GrammarConcept(
        id="case.instrumental",
        kind="case",
        foster_gateway="Means-By Function",
        plain_english="Marks the means, instrument, or companion by which something happens.",
        traditional={
            "en": "instrumental",
            "grc": "instrumental function often expressed with dative or prepositions",
            "lat": "ablative of means/instrument",
            "san": "tṛtīyā vibhakti",
            "san_role": "karaṇa",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_INSTRUMENTAL_EVIDENCE,
        examples={"lat": "gladiō", "san": "putreṇa"},
        skills={
            "read": "Look for by, with, or by means of relationships.",
            "understand": "Connect the form to the means or instrument of the action.",
            "learn": "Map Means-By Function to instrumental terminology.",
            "write": "Choose an instrumental expression in controlled means prompts.",
        },
    ),
    GrammarConcept(
        id="case.locative",
        kind="case",
        foster_gateway="In-At Function",
        plain_english="Marks the place, time, or setting where something is located.",
        traditional={
            "en": "locative",
            "grc": "location often expressed with dative or prepositions",
            "lat": "locative remnants / in + ablative",
            "san": "saptamī vibhakti",
            "san_role": "adhikaraṇa",
        },
        applies_to=["noun", "adjective", "pronoun"],
        processes=["process.declension"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_LOCATIVE_EVIDENCE,
        examples={"lat": "Rōmae", "san": "grāme"},
        skills={
            "read": "Look for in, at, on, or within relationships.",
            "understand": "Connect the form to the setting or location of the event.",
            "learn": "Map In-At Function to locative terminology.",
            "write": "Choose a locative expression in controlled location prompts.",
        },
    ),
    GrammarConcept(
        id="number.singular",
        kind="number",
        foster_gateway="Single",
        plain_english="One item, person, or concept.",
        traditional={"en": "singular", "grc": "ἑνικός", "lat": "singularis", "san": "ekavacana"},
        applies_to=["noun", "adjective", "pronoun", "verb"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_SINGULAR_EVIDENCE,
        examples={"grc": "λόγος", "lat": "puella", "san": "putraḥ"},
        skills=_NUMBER_SINGULAR_SKILLS,
    ),
    GrammarConcept(
        id="number.dual",
        kind="number",
        foster_gateway="Pair",
        plain_english="Exactly two items, persons, or actions.",
        traditional={
            "en": "dual",
            "grc": "δυϊκός",
            "lat": "no regular Latin dual",
            "san": "dvivacana",
        },
        applies_to=["noun", "adjective", "pronoun", "verb"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_DUAL_EVIDENCE,
        examples={"grc": "λόγω", "san": "putrau"},
        skills=_NUMBER_DUAL_SKILLS,
    ),
    GrammarConcept(
        id="number.plural",
        kind="number",
        foster_gateway="Group",
        plain_english="More than one item, person, or concept.",
        traditional={"en": "plural", "grc": "πληθυντικός", "lat": "pluralis", "san": "bahuvacana"},
        applies_to=["noun", "adjective", "pronoun", "verb"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_PLURAL_EVIDENCE,
        examples={"grc": "λόγοι", "lat": "puellae", "san": "putrāḥ"},
        skills=_NUMBER_PLURAL_SKILLS,
    ),
    GrammarConcept(
        id="gender.masculine",
        kind="gender",
        foster_gateway="Male",
        plain_english="Masculine grammatical gender.",
        traditional={"en": "masculine", "grc": "ἀρσενικόν", "lat": "masculinum", "san": "puṃliṅga"},
        applies_to=["noun", "adjective", "pronoun"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_MASCULINE_EVIDENCE,
        examples={"grc": "λόγος", "lat": "dominus", "san": "putraḥ"},
        skills=_GENDER_MASCULINE_SKILLS,
    ),
    GrammarConcept(
        id="gender.feminine",
        kind="gender",
        foster_gateway="Female",
        plain_english="Feminine grammatical gender.",
        traditional={"en": "feminine", "grc": "θηλυκόν", "lat": "femininum", "san": "strīliṅga"},
        applies_to=["noun", "adjective", "pronoun"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_FEMININE_EVIDENCE,
        examples={"grc": "φωνή", "lat": "puella", "san": "nadī"},
        skills=_GENDER_FEMININE_SKILLS,
    ),
    GrammarConcept(
        id="gender.neuter",
        kind="gender",
        foster_gateway="Neither",
        plain_english="Neuter grammatical gender.",
        traditional={
            "en": "neuter",
            "grc": "οὐδέτερον",
            "lat": "neutrum",
            "san": "napuṃsakaliṅga",
        },
        applies_to=["noun", "adjective", "pronoun"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_NEUTER_EVIDENCE,
        examples={"grc": "δῶρον", "lat": "bellum", "san": "phalam"},
        skills=_GENDER_NEUTER_SKILLS,
    ),
    GrammarConcept(
        id="tense.present",
        kind="tense",
        foster_gateway="Time-Now",
        plain_english="Presents an action as current, general, or ongoing.",
        traditional={"en": "present", "grc": "ἐνεστώς", "lat": "praesens", "san": "laṭ"},
        applies_to=["verb"],
        processes=["process.conjugation"],
        source_basis=[
            "Smyth Greek Grammar",
            "Allen and Greenough Latin Grammar",
            "Whitney Sanskrit Grammar",
        ],
        evidence=_PRESENT_EVIDENCE,
        examples={"grc": "λύω", "lat": "amo", "san": "bhavati"},
        skills=_TENSE_PRESENT_SKILLS,
    ),
    GrammarConcept(
        id="mood.indicative",
        kind="mood",
        foster_gateway="Statement",
        plain_english="Presents a statement or question as part of ordinary assertion.",
        traditional={
            "en": "indicative",
            "grc": "ὁριστική",
            "lat": "indicativus",
            "san": "lakāra context",
        },
        applies_to=["verb"],
        processes=["process.conjugation"],
        source_basis=[
            "Smyth Greek Grammar",
            "Allen and Greenough Latin Grammar",
            "Whitney Sanskrit Grammar",
        ],
        evidence=_INDICATIVE_EVIDENCE,
        examples={"grc": "λύω", "lat": "amat", "san": "bhavati"},
        skills=_MOOD_INDICATIVE_SKILLS,
    ),
    GrammarConcept(
        id="voice.active",
        kind="voice",
        foster_gateway="Doing",
        plain_english="Presents the subject as doing or performing the action.",
        traditional={
            "en": "active",
            "grc": "ἐνεργητική",
            "lat": "activum",
            "san": "kartari prayoga",
            "san_role": "kartari prayoga, agent-oriented expression",
        },
        applies_to=["verb"],
        processes=["process.conjugation"],
        source_basis=[
            "Smyth Greek Grammar",
            "Allen and Greenough Latin Grammar",
            "Whitney Sanskrit Grammar",
        ],
        evidence=_ACTIVE_EVIDENCE,
        examples={"grc": "λύω", "lat": "amat", "san": "bhavati"},
        skills=_VOICE_ACTIVE_SKILLS,
    ),
    GrammarConcept(
        id="voice.passive",
        kind="voice",
        foster_gateway="Undergoing",
        plain_english="Presents the subject as undergoing or receiving the action.",
        traditional={
            "en": "passive",
            "grc": "πάθος / παθητική",
            "lat": "passivum",
            "san": "karmaṇi / bhāvakarmaṇoḥ",
            "san_role": "patient- or result-oriented expression",
        },
        applies_to=["verb"],
        processes=["process.conjugation"],
        source_basis=[
            "Smyth Greek Grammar",
            "Allen and Greenough Latin Grammar",
            "Whitney Sanskrit Grammar",
        ],
        evidence=_PASSIVE_EVIDENCE,
        examples={"grc": "λύομαι", "lat": "legor", "san": "pacyate"},
        skills=_VOICE_PASSIVE_SKILLS,
    ),
    GrammarConcept(
        id="person.first",
        kind="person",
        foster_gateway="Speaker",
        plain_english="The speaker or speaker's group.",
        traditional={
            "en": "first person",
            "grc": "πρῶτον πρόσωπον",
            "lat": "prima persona",
            "san": "uttama puruṣa",
        },
        applies_to=["verb", "pronoun"],
        source_basis=[
            "Smyth Greek Grammar",
            "Allen and Greenough Latin Grammar",
            "Whitney Sanskrit Grammar",
        ],
        evidence=_FIRST_PERSON_EVIDENCE,
        examples={"grc": "λύω", "lat": "amo", "san": "bhavāmi"},
        skills=_PERSON_FIRST_SKILLS,
    ),
    GrammarConcept(
        id="process.declension",
        kind="process",
        foster_gateway="Form changes for noun jobs",
        plain_english=(
            "Nouns, adjectives, and pronouns decline: they change form for case, "
            "number, and gender."
        ),
        traditional={
            "en": "declension",
            "grc": "κλίσις",
            "lat": "declinatio",
            "san": "śabdarūpa / vibhakti",
            "san_process": "subanta formation",
        },
        applies_to=["noun", "adjective", "pronoun"],
        source_basis=_CASE_SOURCE_BASIS,
        evidence=_DECLENSION_EVIDENCE,
        examples={"grc": "λόγος, λόγου", "lat": "puella, puellae", "san": "putraḥ, putrāṇām"},
        skills={
            "read": "Recognize which job the noun form is doing.",
            "understand": "Connect endings to case, number, and gender.",
            "learn": "Map Foster form jobs to traditional declension.",
            "write": "Choose case endings in controlled nominal prompts.",
        },
    ),
    GrammarConcept(
        id="process.conjugation",
        kind="process",
        foster_gateway="Form changes for verb jobs",
        plain_english=(
            "Verbs conjugate: they change form for person, number, tense, mood, and voice."
        ),
        traditional={
            "en": "conjugation",
            "grc": "συζυγία",
            "lat": "coniugatio",
            "san": "tiṅanta / lakāra",
            "san_process": "tiṅanta formation",
        },
        applies_to=["verb"],
        source_basis=[
            "Smyth Greek Grammar",
            "Allen and Greenough Latin Grammar",
            "Whitney Sanskrit Grammar",
        ],
        evidence=_CONJUGATION_EVIDENCE,
        examples={"grc": "λύω", "lat": "amamus", "san": "bhavati"},
        skills={
            "read": "Recognize who is doing the action and when/how it happens.",
            "understand": "Connect endings to person, number, tense, mood, and voice.",
            "learn": "Map Foster verb labels to traditional conjugation.",
            "write": "Choose verb endings in controlled prompts.",
        },
    ),
    GrammarConcept(
        id="sound_change.vrddhi",
        kind="sound_change",
        foster_gateway="Fully strengthened vowel grade",
        plain_english=(
            "Vṛddhi is a stronger Sanskrit vowel grade used in grammatical "
            "derivation and sound-change explanation."
        ),
        traditional={
            "en": "vrddhi grade",
            "san": "vṛddhi",
            "san_process": "vṛddhi vowel substitution",
        },
        applies_to=["vowel", "root", "stem"],
        processes=["process.inflection"],
        source_basis=[
            "Pāṇini, Aṣṭādhyāyī",
            "Kāśikāvṛtti",
            "Sanskrit vyākaraṇa sound-change tradition",
        ],
        evidence=_VRDDHI_EVIDENCE,
        examples={"san": "a/ā plus i/u-like grades can yield ai/au in relevant rules"},
        skills={
            "read": "Recognize vṛddhi as a fully strengthened vowel grade in a derived form.",
            "understand": (
                "Connect the stronger vowel grade to the rule environment that triggers it."
            ),
            "learn": "Map Fully strengthened vowel grade to the Sanskrit term vṛddhi.",
            "write": "Apply vṛddhi only in controlled prompts where a verified rule calls for it.",
        },
    ),
    GrammarConcept(
        id="sound_change.guna",
        kind="sound_change",
        foster_gateway="Strengthened vowel grade",
        plain_english=(
            "Guṇa is a Sanskrit vowel-strengthening grade used in grammatical "
            "derivation and sound-change explanation."
        ),
        traditional={
            "en": "guna grade",
            "san": "guṇa",
            "san_process": "guṇa vowel substitution",
        },
        applies_to=["vowel", "root", "stem"],
        processes=["process.inflection"],
        source_basis=[
            "Pāṇini, Aṣṭādhyāyī",
            "Kāśikāvṛtti",
            "Sanskrit vyākaraṇa sound-change tradition",
        ],
        evidence=_GUNA_EVIDENCE,
        examples={"san": "i/u/ṛ take guṇa grades e/o/ar in relevant environments"},
        skills={
            "read": "Recognize guṇa as a strengthened vowel grade in a derived form.",
            "understand": "Connect a changed vowel to the grammatical process that triggered it.",
            "learn": "Map Strengthened vowel grade to the Sanskrit term guṇa.",
            "write": "Apply guṇa only in controlled prompts where a verified rule calls for it.",
        },
    ),
    GrammarConcept(
        id="sound_relation.savarna",
        kind="sound_relation",
        foster_gateway="Same sound class",
        plain_english=(
            "Savarṇa groups sounds that share the same place and effort of articulation, "
            "so the grammar can reason about related sounds as a class."
        ),
        traditional={
            "en": "homorganic/same-class sound",
            "san": "savarṇa",
            "san_process": "shared articulation class",
        },
        applies_to=["vowel", "consonant", "sound"],
        processes=["process.inflection"],
        source_basis=[
            "Pāṇini, Aṣṭādhyāyī",
            "Kāśikāvṛtti",
            "Sanskrit vyākaraṇa sound-class tradition",
        ],
        evidence=_SAVARNA_EVIDENCE,
        examples={"san": "sounds with matching mouth position and articulatory effort"},
        skills={
            "read": "Recognize savarṇa as a same-class sound relation used by rules.",
            "understand": "Connect sound replacement or grouping to shared articulation.",
            "learn": "Map Same sound class to the Sanskrit term savarṇa.",
            "write": "Use savarṇa only where a rule asks for same-class sound comparison.",
        },
    ),
]
