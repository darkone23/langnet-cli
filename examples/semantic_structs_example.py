#!/usr/bin/env python3
"""
Example demonstrating the new semantic structs schema for LangNet.

This shows how to use the Protocol Buffer generated classes from
vendor/langnet-spec/schema/langnet_spec.proto to create and serialize
language query responses according to the semantic structs design.

Based on: docs/technical/design/01-semantic-structs.md
"""

import sys
import json

# Add the generated schema to the path
sys.path.insert(0, "vendor/langnet-spec/generated/python")

try:
    from langnet_spec import (
        QueryResponse,
        Query,
        LanguageHint,
        Language,
        Lemma,
        Analysis,
        AnalysisType,
        MorphologicalFeatures,
        PartOfSpeech,
        Case,
        Number,
        Gender,
        Sense,
        Witness,
        Provenance,
        UiHints,
        Source,
        NormalizationStep,
    )
except ImportError as e:
    print(f"Error importing generated schema: {e}")
    print("Make sure to run 'just codegen' first to generate the Python classes.")
    sys.exit(1)


def create_full_query_response():
    """Create a full QueryResponse example matching the semantic structs design."""
    print("=== Full QueryResponse Example ===")

    # Create the Query object
    query = Query(
        surface="agni",
        language_hint=LanguageHint.SAN,
        normalized="agni",
        normalization_steps=[
            NormalizationStep(
                operation="unicode_normalization",
                input="agni",
                output="agni",
                tool="normalizer",
            ),
            NormalizationStep(
                operation="slp1_conversion",
                input="agni",
                output="agni",
                tool="transliterator",
            ),
        ],
    )

    # Create lemmas
    lemmas = [
        Lemma(
            lemma_id="san:agni",
            display="agni",
            language=Language.SAN,
            sources=[Source.MW, Source.AP90, Source.HERITAGE],
        )
    ]

    # Create analyses (morphology)
    analyses = [
        Analysis(
            type=AnalysisType.MORPHOLOGY,
            features=MorphologicalFeatures(
                pos=PartOfSpeech.POS_NOUN,
                case=Case.NOMINATIVE,
                number=Number.SINGULAR,
                gender=Gender.MASCULINE,
            ),
            witnesses=[
                Witness(source=Source.HERITAGE, ref="heritage:morph:agni"),
                Witness(source=Source.CDSL, ref="cdsl:morph:agni:nom.sg.m"),
            ],
        )
    ]

    # Create senses with semantic constants
    senses = [
        Sense(
            sense_id="B1",
            semantic_constant="FIRE_ELEMENT",
            display_gloss="fire, sacrificial fire",
            domains=["general", "religious"],
            register=["vedic", "epic"],
            witnesses=[
                Witness(source=Source.MW, ref="217497"),
                Witness(source=Source.AP90, ref="agni.1"),
            ],
        ),
        Sense(
            sense_id="B2",
            semantic_constant="FIRE_GOD",
            display_gloss="the god Agni, deity of fire",
            domains=["mythology", "religious"],
            register=["vedic"],
            witnesses=[
                Witness(source=Source.MW, ref="217498"),
                Witness(source=Source.HERITAGE, ref="heritage:sense:agni:deity"),
            ],
        ),
    ]

    # Create provenance
    provenance = [
        Provenance(tool="langnet-engine"),
        Provenance(tool="cdsl-indexer"),
    ]

    # Create UI hints
    ui_hints = UiHints(
        default_mode="open",
        primary_lemma="san:agni",
        collapsed_senses=["B3", "B4"],  # Example of senses to collapse
    )

    # Create the full QueryResponse
    response = QueryResponse(
        schema_version="0.0.1",
        query=query,
        lemmas=lemmas,
        analyses=analyses,
        senses=senses,
        citations=[],
        provenance=provenance,
        ui_hints=ui_hints,
        warnings=["Some witnesses have low confidence"],
    )

    return response


def main():
    """Run the examples."""

    # Full semantic structs response
    response = create_full_query_response()

    # Convert full response to JSON
    json_str = response.to_json(indent=2)

    print(f"\n\n=== Full QueryResponse JSON ===")
    print(json_str)

    # Demonstrate serialization/deserialization
    print(f"\n\n=== Serialization/Deserialization Example ===")

    # Serialize to bytes
    binary_data = bytes(response)
    print(f"Binary size: {len(binary_data)} bytes")

    # Deserialize from bytes
    deserialized = QueryResponse.FromString(binary_data)
    print(f"Successfully deserialized: {deserialized.schema_version}")

    # Show schema validation
    print(f"\nSchema validates: {deserialized.schema_version == '0.0.1'}")
    print(f"Number of lemmas: {len(deserialized.lemmas)}")
    print(f"Number of senses: {len(deserialized.senses)}")
    if deserialized.ui_hints and deserialized.ui_hints.primary_lemma:
        print(f"Primary lemma: {deserialized.ui_hints.primary_lemma}")
    else:
        print("Primary lemma: Not specified")

    # Access nested data
    if deserialized.senses:
        first_sense = deserialized.senses[0]
        print(f"\nFirst sense:")
        print(f"  ID: {first_sense.sense_id}")
        print(f"  Semantic Constant: {first_sense.semantic_constant}")
        print(f"  Gloss: {first_sense.display_gloss}")
        if first_sense.witnesses:
            print(f"  Witnesses: {len(first_sense.witnesses)}")
            for witness in first_sense.witnesses:
                print(f"    - {witness.source.name}: {witness.ref}")


if __name__ == "__main__":
    main()
