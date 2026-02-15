"""
Converter from current DictionaryEntry format to semantic structs schema.

This module provides functions to convert existing language data structures
to the new semantic structs schema defined in vendor/langnet-spec/schema/langnet_spec.proto.
"""

import sys
from datetime import UTC, datetime

# Add the generated schema to the path
sys.path.insert(0, "vendor/langnet-spec/generated/python")

try:
    from langnet_spec import (
        Analysis,
        AnalysisType,
        Case,
        Gender,
        Language,
        LanguageHint,
        Lemma,
        Mood,
        MorphologicalFeatures,
        Number,
        PartOfSpeech,
        Person,
        Provenance,
        Query,
        QueryResponse,
        Sense,
        Source,
        Tense,
        UiHints,
        Voice,
        Witness,
    )
except ImportError as e:
    raise ImportError(
        f"Failed to import generated schema: {e}\n"
        "Make sure to run 'just codegen' first to generate the Python classes."
    ) from e

from langnet.schema import DictionaryDefinition, DictionaryEntry, MorphologyInfo


def _map_language_code(lang: str) -> Language:
    """Map language code to Language enum."""
    lang_map = {
        "lat": Language.LAT,
        "grc": Language.GRC,
        "san": Language.SAN,
        "la": Language.LAT,
        "greek": Language.GRC,
        "sanskrit": Language.SAN,
    }
    return lang_map.get(lang.lower(), Language.UNSPECIFIED)


def _map_language_hint(lang: str) -> LanguageHint:
    """Map language code to LanguageHint enum."""
    lang_map = {
        "lat": LanguageHint.LAT,
        "grc": LanguageHint.GRC,
        "san": LanguageHint.SAN,
        "la": LanguageHint.LAT,
        "greek": LanguageHint.GRC,
        "sanskrit": LanguageHint.SAN,
    }
    return lang_map.get(lang.lower(), LanguageHint.UNSPECIFIED)


def _map_part_of_speech(pos: str | None) -> PartOfSpeech:
    """Map part of speech string to PartOfSpeech enum."""
    if not pos:
        return PartOfSpeech.POS_UNSPECIFIED

    pos_lower = pos.lower()
    pos_map = {
        "noun": PartOfSpeech.POS_NOUN,
        "verb": PartOfSpeech.POS_VERB,
        "adjective": PartOfSpeech.POS_ADJECTIVE,
        "adverb": PartOfSpeech.POS_ADVERB,
        "pronoun": PartOfSpeech.POS_PRONOUN,
        "preposition": PartOfSpeech.POS_PREPOSITION,
        "conjunction": PartOfSpeech.POS_CONJUNCTION,
        "interjection": PartOfSpeech.POS_INTERJECTION,
        "particle": PartOfSpeech.POS_PARTICLE,
        "numeral": PartOfSpeech.POS_NUMERAL,
    }
    return pos_map.get(pos_lower, PartOfSpeech.POS_UNSPECIFIED)


def _map_gender(gender: str | list[str] | None) -> Gender:
    """Map gender string or list to Gender enum."""
    if not gender:
        return Gender.UNSPECIFIED

    # Handle list case
    if isinstance(gender, list):
        if not gender:
            return Gender.UNSPECIFIED
        # Take the first gender if multiple
        gender_str = gender[0]
    else:
        gender_str = gender

    gender_lower = gender_str.lower()
    gender_map = {
        "masculine": Gender.MASCULINE,
        "m": Gender.MASCULINE,
        "male": Gender.MASCULINE,
        "feminine": Gender.FEMININE,
        "f": Gender.FEMININE,
        "female": Gender.FEMININE,
        "neuter": Gender.NEUTER,
        "n": Gender.NEUTER,
        "common": Gender.COMMON,
        "c": Gender.COMMON,
    }
    return gender_map.get(gender_lower, Gender.UNSPECIFIED)


def _map_case(case: str | None) -> Case:
    """Map case string to Case enum."""
    if not case:
        return Case.UNSPECIFIED

    case_lower = case.lower()
    case_map = {
        "nominative": Case.NOMINATIVE,
        "nom": Case.NOMINATIVE,
        "genitive": Case.GENITIVE,
        "gen": Case.GENITIVE,
        "dative": Case.DATIVE,
        "dat": Case.DATIVE,
        "accusative": Case.ACCUSATIVE,
        "acc": Case.ACCUSATIVE,
        "vocative": Case.VOCATIVE,
        "voc": Case.VOCATIVE,
        "ablative": Case.ABLATIVE,
        "abl": Case.ABLATIVE,
        "locative": Case.LOCATIVE,
        "loc": Case.LOCATIVE,
        "instrumental": Case.INSTRUMENTAL,
        "ins": Case.INSTRUMENTAL,
    }
    return case_map.get(case_lower, Case.UNSPECIFIED)


def _map_number(number: str | None) -> Number:
    """Map number string to Number enum."""
    if not number:
        return Number.UNSPECIFIED

    number_lower = number.lower()
    number_map = {
        "singular": Number.SINGULAR,
        "sg": Number.SINGULAR,
        "plural": Number.PLURAL,
        "pl": Number.PLURAL,
        "dual": Number.DUAL,
        "du": Number.DUAL,
    }
    return number_map.get(number_lower, Number.UNSPECIFIED)


def _map_person(person_str: str) -> Person:
    """Map person string to Person enum."""
    person_lower = person_str.lower()
    if person_lower in ["1st", "first"]:
        return Person.FIRST
    elif person_lower in ["2nd", "second"]:
        return Person.SECOND
    elif person_lower in ["3rd", "third"]:
        return Person.THIRD
    return Person.UNSPECIFIED


def _map_tense(tense_str: str) -> Tense:
    """Map tense string to Tense enum."""
    tense_lower = tense_str.lower()
    tense_map = {
        "present": Tense.PRESENT,
        "imperfect": Tense.IMPERFECT,
        "future": Tense.FUTURE,
        "aorist": Tense.AORIST,
        "perfect": Tense.PERFECT,
        "pluperfect": Tense.PLUPERFECT,
        "future perfect": Tense.FUTURE_PERFECT,
    }
    return tense_map.get(tense_lower, Tense.UNSPECIFIED)


def _map_mood(mood_str: str) -> Mood:
    """Map mood string to Mood enum."""
    mood_lower = mood_str.lower()
    mood_map = {
        "indicative": Mood.INDICATIVE,
        "subjunctive": Mood.SUBJUNCTIVE,
        "optative": Mood.OPTATIVE,
        "imperative": Mood.IMPERATIVE,
        "infinitive": Mood.INFINITIVE,
        "participle": Mood.PARTICIPLE,
        "gerund": Mood.GERUND,
        "gerundive": Mood.GERUNDIVE,
        "supine": Mood.SUPINE,
    }
    return mood_map.get(mood_lower, Mood.UNSPECIFIED)


def _map_voice(voice_str: str) -> Voice:
    """Map voice string to Voice enum."""
    voice_lower = voice_str.lower()
    voice_map = {
        "active": Voice.ACTIVE,
        "middle": Voice.MIDDLE,
        "passive": Voice.PASSIVE,
        "medio-passive": Voice.MEDIO_PASSIVE,
    }
    return voice_map.get(voice_lower, Voice.UNSPECIFIED)


def _add_extra_features(features: MorphologicalFeatures, morphology: MorphologyInfo) -> None:
    """Add any extra features from morphology features dict."""
    if morphology.features and isinstance(morphology.features, dict):
        for key, value in morphology.features.items():
            if isinstance(value, (str, int, float, bool)):
                features.extras[key] = str(value)


def _create_timestamp() -> str:
    """Create a timestamp string for provenance (tool field)."""
    now = datetime.now(UTC)
    return now.isoformat()


def convert_morphology(morphology: MorphologyInfo | None) -> Analysis | None:
    """Convert MorphologyInfo to Analysis message."""
    if not morphology:
        return None

    features = MorphologicalFeatures()

    # Map POS
    features.pos = _map_part_of_speech(morphology.pos)

    # Map gender if available
    if morphology.gender:
        features.gender = _map_gender(morphology.gender)

    # Map case if available
    if morphology.case:
        features.case = _map_case(morphology.case)

    # Map number if available
    if morphology.number:
        features.number = _map_number(morphology.number)

    # Map person if available
    if morphology.person:
        features.person = _map_person(morphology.person)

    # Map tense if available
    if morphology.tense:
        features.tense = _map_tense(morphology.tense)

    # Map mood if available
    if morphology.mood:
        features.mood = _map_mood(morphology.mood)

    # Map voice if available
    if morphology.voice:
        features.voice = _map_voice(morphology.voice)

    # Add any extra features
    _add_extra_features(features, morphology)

    return Analysis(
        type=AnalysisType.MORPHOLOGY,
        features=features,
        witnesses=[Witness(source=Source.UNSPECIFIED, ref="morphology_converter")],
    )


def _map_source(source_str: str) -> Source:
    """Map source string to Source enum."""
    source_lower = source_str.lower()
    source_map = {
        "mw": Source.MW,
        "monier-williams": Source.MW,
        "ap90": Source.AP90,
        "apte": Source.AP90,
        "heritage": Source.HERITAGE,
        "cdsl": Source.CDSL,
        "whitakers": Source.WHITAKERS,
        "diogenes": Source.DIOGENES,
        "lewis_short": Source.LEWIS_SHORT,
        "lsj": Source.LSJ,
        "cltk": Source.CLTK,
    }
    return source_map.get(source_lower, Source.UNSPECIFIED)


def convert_definition_to_sense(
    definition: DictionaryDefinition, sense_id: str, source: str, lemma_id: str
) -> Sense:
    """Convert DictionaryDefinition to Sense message."""
    # Generate a simple semantic constant from the definition text
    words = definition.definition.split()[:3]
    semantic_constant = "_".join(words).upper().replace(",", "").replace(".", "")

    # Convert source string to enum
    source_enum = _map_source(source)

    # Get ref from metadata, ensure it's a string
    ref = definition.metadata.get("id", "unknown")
    if not isinstance(ref, str):
        ref = str(ref)

    return Sense(
        sense_id=sense_id,
        semantic_constant=semantic_constant,
        display_gloss=definition.definition,
        domains=["general"],
        register=[],
        witnesses=[Witness(source=source_enum, ref=ref)],
    )


def convert_dictionary_entry(
    entry: DictionaryEntry, schema_version: str = "0.0.1"
) -> QueryResponse:
    """Convert a DictionaryEntry to QueryResponse."""
    # Create query object
    query = Query(
        surface=entry.word,
        language_hint=_map_language_hint(entry.language),
        normalized=entry.word,
        normalization_steps=[],  # Could be populated from metadata
    )

    # Create lemma
    lemma = Lemma(
        lemma_id=f"{entry.language}:{entry.word}",
        display=entry.word,
        language=_map_language_code(entry.language),
        sources=[_map_source(entry.source)],
    )

    # Create analyses from morphology
    analyses = []
    if entry.morphology:
        analysis = convert_morphology(entry.morphology)
        if analysis:
            analyses.append(analysis)

    # Create senses from definitions
    senses = []
    for i, definition in enumerate(entry.definitions):
        sense_id = f"B{i + 1}"
        sense = convert_definition_to_sense(
            definition=definition, sense_id=sense_id, source=entry.source, lemma_id=lemma.lemma_id
        )
        senses.append(sense)

    # Create provenance
    provenance = [Provenance(tool=f"langnet-semantic-converter {_create_timestamp()}")]

    # Create UI hints
    ui_hints = UiHints(default_mode="open", primary_lemma=lemma.lemma_id, collapsed_senses=[])

    # Create warnings if needed
    warnings = []
    if not entry.definitions:
        warnings.append("No definitions found")

    return QueryResponse(
        schema_version=schema_version,
        query=query,
        lemmas=[lemma],
        analyses=analyses,
        senses=senses,
        citations=[],  # Could be populated from metadata
        provenance=provenance,
        ui_hints=ui_hints,
        warnings=warnings,
    )


def convert_multiple_entries(
    entries: list[DictionaryEntry], schema_version: str = "0.0.1"
) -> QueryResponse:
    """Convert multiple DictionaryEntries to a single QueryResponse.

    This merges information from multiple sources (e.g., Heritage, CDSL)
    into a unified response.
    """
    if not entries:
        raise ValueError("No entries to convert")

    # Use the first entry as the primary
    primary_entry = entries[0]

    # Create query object from primary entry
    query = Query(
        surface=primary_entry.word,
        language_hint=_map_language_hint(primary_entry.language),
        normalized=primary_entry.word,
        normalization_steps=[],
    )

    # Collect unique lemmas
    lemmas = []
    seen_lemma_ids = set()

    for entry in entries:
        lemma_id = f"{entry.language}:{entry.word}"
        if lemma_id not in seen_lemma_ids:
            lemmas.append(
                Lemma(
                    lemma_id=lemma_id,
                    display=entry.word,
                    language=_map_language_code(entry.language),
                    sources=[_map_source(entry.source)],
                )
            )
            seen_lemma_ids.add(lemma_id)

    # Collect all analyses
    analyses = []
    for entry in entries:
        if entry.morphology:
            analysis = convert_morphology(entry.morphology)
            if analysis:
                # Add source-specific witness
                analysis.witnesses.append(
                    Witness(source=_map_source(entry.source), ref="morphology")
                )
                analyses.append(analysis)

    # Collect all senses
    senses = []
    sense_counter = 1

    for entry in entries:
        for definition in entry.definitions:
            sense_id = f"B{sense_counter}"
            sense = convert_definition_to_sense(
                definition=definition,
                sense_id=sense_id,
                source=entry.source,
                lemma_id=f"{entry.language}:{entry.word}",
            )
            senses.append(sense)
            sense_counter += 1

    # Create provenance
    provenance = [Provenance(tool=f"langnet-semantic-converter {_create_timestamp()}")]

    # Create UI hints
    ui_hints = UiHints(
        default_mode="open", primary_lemma=lemmas[0].lemma_id if lemmas else "", collapsed_senses=[]
    )

    # Collect warnings
    warnings = []
    if not senses:
        warnings.append("No definitions found in any source")

    return QueryResponse(
        schema_version=schema_version,
        query=query,
        lemmas=lemmas,
        analyses=analyses,
        senses=senses,
        citations=[],
        provenance=provenance,
        ui_hints=ui_hints,
        warnings=warnings,
    )
