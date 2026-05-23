from __future__ import annotations

from langnet.learning.grammar_concepts import get_grammar_concept, load_grammar_concepts


def test_grammar_concept_registry_loads_core_gateway_concepts() -> None:
    concepts = load_grammar_concepts()

    assert "case.genitive" in concepts
    assert "process.declension" in concepts
    assert "process.conjugation" in concepts
    assert "process.participle" in concepts


def test_all_current_concepts_have_buttoned_up_learner_fields() -> None:
    concepts = load_grammar_concepts()

    for concept in concepts.values():
        assert concept.foster_gateway, concept.id
        assert concept.plain_english, concept.id
        assert concept.traditional, concept.id
        assert concept.source_basis, concept.id
        assert concept.evidence, concept.id
        assert concept.examples, concept.id
        assert concept.skills, concept.id
        for key in ("read", "understand", "learn", "write"):
            assert concept.skills.get(key), f"{concept.id} missing skill {key}"
        for evidence in concept.evidence:
            assert evidence.evidence_level in {"reader_work", "reader_segment"}
            assert evidence.source_anchor_id
            assert evidence.work_id
            assert evidence.canonical_text_id
            assert evidence.canonical_address
            assert evidence.label


def test_genitive_concept_maps_foster_to_traditional_terms() -> None:
    concept = get_grammar_concept("case.genitive")

    assert concept.id == "case.genitive"
    assert concept.foster_gateway == "Possessing Function"
    assert concept.traditional["en"] == "genitive"
    assert concept.traditional["grc"] == "γενική"
    assert concept.traditional["lat"] == "genetivus"
    assert concept.traditional["san"] == "ṣaṣṭhī vibhakti"
    assert concept.traditional["san_role"] == "sambandha"
    assert concept.examples["grc"] == "λόγου"


def test_genitive_concept_has_structured_source_and_segment_evidence() -> None:
    concept = get_grammar_concept("case.genitive")

    source_anchor_ids = {evidence.source_anchor_id for evidence in concept.evidence}
    assert "grammar.source.dionysius_thrax.ars_grammatica" in source_anchor_ids
    assert "grammar.source.varro.de_lingua_latina" in source_anchor_ids
    assert "grammar.source.panini.astadhyayi" in source_anchor_ids
    assert {evidence.evidence_level for evidence in concept.evidence} == {
        "reader_work",
        "reader_segment",
    }
    panini = next(
        evidence
        for evidence in concept.evidence
        if evidence.source_anchor_id == "grammar.source.panini.astadhyayi"
        and evidence.evidence_level == "reader_work"
    )
    assert panini.work_id == "langnet:reader:sanskrit_dcs:dcs_413"
    assert panini.canonical_text_id == "urn:ctsv2:san:astadhyayi-vrddhir-adaic"
    assert panini.citation_path is None
    segment = next(
        evidence for evidence in concept.evidence if evidence.evidence_level == "reader_segment"
    )
    assert segment.citation_path == "551238"
    assert segment.canonical_address == "urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=551238"
    assert "ṣaṣṭhī śeṣe" in segment.label
    greek_segment = next(
        evidence
        for evidence in concept.evidence
        if evidence.evidence_level == "reader_segment"
        and evidence.source_anchor_id == "grammar.source.dionysius_thrax.ars_grammatica"
    )
    assert greek_segment.citation_path == "1.1.31.7"
    assert greek_segment.canonical_address == (
        "urn:ctsv2:grc:ars-grammatica-peri-grammatike-s?ref=1.1.31.7"
    )
    assert "γενικὴ κτητική" in greek_segment.label


def test_guna_concept_has_verified_reader_segment_evidence() -> None:
    concept = get_grammar_concept("sound_change.guna")

    segment = next(
        evidence for evidence in concept.evidence if evidence.evidence_level == "reader_segment"
    )
    assert segment.source_anchor_id == "grammar.source.panini.astadhyayi"
    assert segment.work_id == "langnet:reader:sanskrit_dcs:dcs_413"
    assert segment.citation_path == "550729"
    assert segment.canonical_address == "urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550729"
    assert "adeṅ guṇaḥ" in segment.label


def test_vrddhi_and_savarna_concepts_have_verified_reader_segment_evidence() -> None:
    vrddhi = get_grammar_concept("sound_change.vrddhi")
    savarna = get_grammar_concept("sound_relation.savarna")

    vrddhi_segment = next(
        evidence for evidence in vrddhi.evidence if evidence.evidence_level == "reader_segment"
    )
    assert vrddhi_segment.citation_path == "550728"
    assert vrddhi_segment.canonical_address == ("urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550728")
    assert "vṛddhir ādaic" in vrddhi_segment.label

    savarna_segment = next(
        evidence for evidence in savarna.evidence if evidence.evidence_level == "reader_segment"
    )
    assert savarna_segment.citation_path == "550736"
    assert savarna_segment.canonical_address == (
        "urn:ctsv2:san:astadhyayi-vrddhir-adaic?ref=550736"
    )
    assert "tulyāsyaprayatnaṃ savarṇam" in savarna_segment.label


def test_core_sanskrit_case_and_number_concepts_have_verified_segments() -> None:
    nominative = get_grammar_concept("case.nominative")
    plural = get_grammar_concept("number.plural")
    singular = get_grammar_concept("number.singular")

    nominative_segment = next(
        evidence for evidence in nominative.evidence if evidence.evidence_level == "reader_segment"
    )
    assert nominative_segment.citation_path == "551234"
    assert "prātipadikārthaliṅgaparimāṇavacanamātre prathamā" in nominative_segment.label

    plural_segment = next(
        evidence for evidence in plural.evidence if evidence.evidence_level == "reader_segment"
    )
    assert plural_segment.citation_path == "550989"
    assert "bahuṣu bahuvacanam" in plural_segment.label

    singular_segment = next(
        evidence for evidence in singular.evidence if evidence.evidence_level == "reader_segment"
    )
    assert singular_segment.citation_path == "550990"
    assert "dvyekayor dvivacanaikavacane" in singular_segment.label


def test_core_greek_concepts_have_verified_dionysius_segments() -> None:
    expected = {
        "case.nominative": ("1.1.31.6", "ὀνομαςτικὴ"),
        "case.dative": ("1.1.31.7", "δοτικὴ"),
        "case.accusative": ("1.1.32.1", "αἰτιατικὴ"),
        "number.singular": ("1.1.30.5", "ἑνικός"),
        "number.plural": ("1.1.31.1", "πληθυντικὸς"),
        "gender.masculine": ("1.1.24.8", "ἀρςενικόν"),
        "gender.feminine": ("1.1.24.8", "θηλυκόν"),
        "mood.indicative": ("1.1.47.3", "ὁριςτική"),
        "voice.active": ("1.1.48.1", "ἐνέργεια"),
        "person.first": ("1.1.51.4", "πρῶτον"),
        "tense.present": ("1.1.53.1", "ἐνεςτώς"),
        "process.conjugation": ("1.1.53.6", "Συζυγία"),
        "process.participle": ("1.1.23.1", "μετοχή"),
    }

    for concept_id, (citation_path, label_fragment) in expected.items():
        concept = get_grammar_concept(concept_id)
        segment = next(
            evidence
            for evidence in concept.evidence
            if evidence.evidence_level == "reader_segment"
            and evidence.source_anchor_id == "grammar.source.dionysius_thrax.ars_grammatica"
        )
        assert segment.work_id == "langnet:reader:tlg:tlg0063.001", concept_id
        assert segment.citation_path == citation_path, concept_id
        assert label_fragment in segment.label, concept_id


def test_core_latin_concepts_have_verified_school_grammar_segments() -> None:
    expected = {
        "case.nominative": ("grammar.source.donatus.ars_minor", "76", "nominatiuus"),
        "case.genitive": ("grammar.source.donatus.ars_minor", "76", "genetiuus"),
        "case.dative": ("grammar.source.donatus.ars_minor", "76", "datiuus"),
        "case.accusative": ("grammar.source.donatus.ars_minor", "76", "accusatiuus"),
        "number.singular": ("grammar.source.donatus.ars_minor", "7", "singularis"),
        "number.plural": ("grammar.source.donatus.ars_minor", "7", "pluralis"),
        "gender.masculine": ("grammar.source.donatus.ars_minor", "18", "masculinum"),
        "gender.feminine": ("grammar.source.donatus.ars_minor", "18", "femininum"),
        "mood.indicative": ("grammar.source.donatus.ars_minor", "38", "indicatiuus"),
        "voice.active": ("grammar.source.donatus.ars_minor", "43", "actiua"),
        "person.first": ("grammar.source.donatus.ars_maior", "112", "prima"),
        "tense.present": ("grammar.source.dositheus.ars_grammatica", "35", "praesens"),
        "process.conjugation": ("grammar.source.priscian.institutiones", "1743", "coniugatio"),
        "process.participle": ("grammar.source.donatus.ars_minor", "73", "participium"),
    }

    for concept_id, (source_anchor_id, citation_path, label_fragment) in expected.items():
        concept = get_grammar_concept(concept_id)
        segment = next(
            evidence
            for evidence in concept.evidence
            if evidence.evidence_level == "reader_segment"
            and evidence.source_anchor_id == source_anchor_id
        )
        assert segment.citation_path == citation_path, concept_id
        assert label_fragment in segment.label, concept_id


def test_expanded_nominal_concepts_have_verified_reader_segments() -> None:
    expected = {
        "number.dual": ("grammar.source.dionysius_thrax.ars_grammatica", "1.1.30.5", "δυϊκός"),
        "gender.neuter": (
            "grammar.source.dionysius_thrax.ars_grammatica",
            "1.1.24.8",
            "οὐδέτερον",
        ),
        "case.vocative": ("grammar.source.donatus.ars_minor", "76", "uocatiuus"),
        "case.ablative": ("grammar.source.donatus.ars_minor", "76", "ablatiuus"),
        "case.instrumental": ("grammar.source.panini.astadhyayi", "551206", "tṛtīyā"),
        "case.locative": ("grammar.source.panini.astadhyayi", "551224", "saptamyadhikarane"),
    }

    for concept_id, (source_anchor_id, citation_path, label_fragment) in expected.items():
        concept = get_grammar_concept(concept_id)
        segment = next(
            evidence
            for evidence in concept.evidence
            if evidence.evidence_level == "reader_segment"
            and evidence.source_anchor_id == source_anchor_id
            and evidence.citation_path == citation_path
        )
        assert label_fragment in segment.label, concept_id


def test_passive_voice_concept_has_greek_and_latin_segments() -> None:
    concept = get_grammar_concept("voice.passive")
    evidence_by_source = {
        evidence.source_anchor_id: evidence
        for evidence in concept.evidence
        if evidence.evidence_level == "reader_segment"
    }

    greek = evidence_by_source["grammar.source.dionysius_thrax.ars_grammatica"]
    latin = evidence_by_source["grammar.source.donatus.ars_minor"]
    assert greek.citation_path == "1.1.49.1"
    assert "πάθος" in greek.label
    assert latin.citation_path == "44"
    assert "passiua" in latin.label


def test_process_concepts_teach_decline_conjugate_rule() -> None:
    declension = get_grammar_concept("process.declension")
    conjugation = get_grammar_concept("process.conjugation")
    participle = get_grammar_concept("process.participle")

    assert "decline" in declension.plain_english
    assert "conjugate" in conjugation.plain_english
    assert "action" in participle.plain_english
    assert "noun" in declension.applies_to
    assert "verb" in conjugation.applies_to
    assert "participle" in participle.applies_to


def test_participle_concept_has_cross_tradition_reader_segments() -> None:
    concept = get_grammar_concept("process.participle")
    evidence_by_source = {
        evidence.source_anchor_id: evidence
        for evidence in concept.evidence
        if evidence.evidence_level == "reader_segment"
    }

    assert concept.foster_gateway == "Action As Noun Form"
    assert concept.traditional["grc"] == "μετοχή"
    assert concept.traditional["lat"] == "participium"
    assert concept.traditional["san"] == "kṛdanta / kṛt"

    panini = evidence_by_source["grammar.source.panini.astadhyayi"]
    assert panini.citation_path == "551927"
    assert "kartari kṛt" in panini.label

    dionysius = evidence_by_source["grammar.source.dionysius_thrax.ars_grammatica"]
    assert dionysius.citation_path == "1.1.23.1"
    assert "μετοχή" in dionysius.label

    donatus = evidence_by_source["grammar.source.donatus.ars_minor"]
    assert donatus.citation_path == "74"
    assert "participio sex accidunt" in donatus.label
