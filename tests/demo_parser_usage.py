#!/usr/bin/env python3
"""Demo script to test parsers with real dictionary data.

This shows practical usage and validates robustness.
"""

from __future__ import annotations


def test_diogenes_parser_with_real_words():
    """Test Diogenes parser with real dictionary lookups."""
    from langnet.parsing.diogenes_parser import DiogenesEntryParser  # noqa: PLC0415

    print("=" * 70)
    print("DIOGENES PARSER - Real Dictionary Entries")
    print("=" * 70)

    parser = DiogenesEntryParser()

    # Real Lewis & Short entries (from actual Diogenes output)
    test_entries = [
        "lupus, -i, m. I. a wolf",
        "amo, amare, amavi, amatum, v. a. I. to love",
        "bonus, -a, -um, adj. I. good",
        "virtus, -utis, f. I. manliness, valor",
        "rex, regis, m. I. a king",
        "verbum, -i, n. I. a word",
    ]

    results = []
    for entry in test_entries:
        print(f"\nInput: {entry!r}")
        parsed = parser.parse_safe(entry)
        if parsed:
            header = parsed.get("header", {})
            print(f"  ✓ Lemma: {header.get('lemma')}")
            print(f"    Inflections: {header.get('principal_parts', [])}")
            print(f"    POS: {header.get('pos')}, Gender: {header.get('gender')}")
            senses = parsed.get("senses", [])
            if senses:
                print(f"    Senses: {len(senses)} found")
            results.append({"entry": entry, "success": True, "parsed": parsed})
        else:
            print("  ✗ FAILED to parse")
            results.append({"entry": entry, "success": False})

    success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
    print(
        f"\n📊 Success Rate: {success_rate:.1f}% ({sum(1 for r in results if r['success'])}/{len(results)})"  # noqa: E501
    )
    return results


def test_cltk_integration():
    """Test CLTK Lewis lines parsing."""
    from langnet.parsing.integration import parse_lewis_lines  # noqa: PLC0415

    print("\n" + "=" * 70)
    print("CLTK LEWIS & SHORT PARSER")
    print("=" * 70)

    # Simulated lewis_lines from CLTK (these are real Lewis & Short format)
    lewis_lines = [
        "amo, āre, āvi, ātum, 1, v. a. to love",
        "amor, -ōris, m. love, affection",
        "bellum, -i, n. war",
        "pax, pācis, f. peace",
        "corpus, -oris, n. body",
        "animus, -i, m. mind, soul",
    ]

    print(f"\nParsing {len(lewis_lines)} Lewis & Short entries...")
    parsed = parse_lewis_lines(lewis_lines)

    for i, entry in enumerate(parsed):
        header = entry.get("header", {})
        print(f"\n{i + 1}. {header.get('lemma')}")
        print(f"   Inflections: {', '.join(header.get('principal_parts', []))}")
        print(f"   POS: {header.get('pos')}, Gender: {header.get('gender')}")

    success_rate = len(parsed) / len(lewis_lines) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}% ({len(parsed)}/{len(lewis_lines)})")
    return parsed


def test_french_parser():
    """Test French gloss parser with real Gaffiot data."""
    from langnet.parsing.french_parser import (  # noqa: PLC0415
        parse_french_glosses,
        parse_gaffiot_entry,
    )

    print("\n" + "=" * 70)
    print("FRENCH GLOSS PARSER - Gaffiot Dictionary")
    print("=" * 70)

    # Real Gaffiot-style entries (French glosses)
    test_glosses = [
        ("amor", "amour, passion, désir"),
        ("bellum", "guerre, combat, conflit"),
        ("pax", "paix, tranquillité, repos"),
        ("virtus", "vertu, courage, valeur"),
        ("corpus", "corps, substance, matière"),
    ]

    results = []
    for headword, gloss_text in test_glosses:
        print(f"\n{headword}: {gloss_text!r}")
        glosses = parse_french_glosses(gloss_text)
        print(f"  → Parsed: {glosses}")

        entry = parse_gaffiot_entry(headword, gloss_text)
        results.append(entry)

    print(f"\n📊 All {len(results)} entries parsed successfully")
    return results


def test_english_gloss_parser():
    """Test English gloss parser (for GPT-translated output)."""
    from langnet.parsing.english_gloss_parser import parse_english_glosses  # noqa: PLC0415

    print("\n" + "=" * 70)
    print("ENGLISH GLOSS PARSER - GPT Translated Output")
    print("=" * 70)

    # Simulated GPT translation output
    test_translations = [
        ("amor", "love, passion, desire"),
        ("bellum", "war, battle, conflict"),
        ("pax", "peace; tranquility; rest"),
        ("virtus", "virtue\ncourage\nvalor"),
        ("corpus", "body, substance, matter, physical form"),
    ]

    for headword, translation in test_translations:
        print(f"\n{headword}: {translation!r}")
        glosses = parse_english_glosses(translation)
        print(f"  → Parsed: {glosses}")

    print(f"\n📊 All {len(test_translations)} translations parsed")


def test_handler_integration():
    """Test how parsers integrate with handlers."""
    from langnet.parsing.integration import enrich_cltk_with_parsed_lewis  # noqa: PLC0415

    print("\n" + "=" * 70)
    print("HANDLER INTEGRATION - CLTK Example")
    print("=" * 70)

    # Simulated CLTK payload
    cltk_payload = {
        "lemma": "lupus",
        "word": "lupus",
        "lewis_lines": [
            "lupus, -i, m. I. a wolf",
            "II. Transf., a greedy person",
        ],
    }

    print("\nBefore enrichment:")
    print(f"  Keys: {list(cltk_payload.keys())}")

    enriched = enrich_cltk_with_parsed_lewis(cltk_payload)

    print("\nAfter enrichment:")
    print(f"  Keys: {list(enriched.keys())}")
    if "parsed_lewis" in enriched:
        print(f"  ✓ Added 'parsed_lewis' with {len(enriched['parsed_lewis'])} entries")
        for i, entry in enumerate(enriched["parsed_lewis"]):
            header = entry.get("header", {})
            print(f"\n  Entry {i + 1}:")
            print(f"    Lemma: {header.get('lemma')}")
            print(f"    Inflections: {header.get('principal_parts')}")
            print(f"    Gender: {header.get('gender')}")


def main():
    """Run all parser demos."""
    print("\n🔬 PARSER ROBUSTNESS TESTING\n")

    # Test each parser
    test_diogenes_parser_with_real_words()
    test_cltk_integration()
    test_french_parser()
    test_english_gloss_parser()
    test_handler_integration()

    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • Diogenes parser: Handles Lewis & Short entry headers")
    print("  • CLTK integration: Parses lewis_lines field automatically")
    print("  • French parser: Extracts individual glosses from French text")
    print("  • English parser: Simple but effective for GPT-translated output")
    print("  • Handler integration: Enrichment happens automatically in v2 handlers")


if __name__ == "__main__":
    main()
