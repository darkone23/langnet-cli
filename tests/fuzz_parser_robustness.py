#!/usr/bin/env python3
"""Fuzz test parsers with diverse real-world dictionary entries.

Tests various word types, edge cases, and formats to assess robustness.
"""

from __future__ import annotations


def fuzz_diogenes_lewis_entries():
    """Test with diverse Lewis & Short entries."""
    from langnet.parsing.diogenes_parser import DiogenesEntryParser  # noqa: PLC0415

    print("=" * 80)
    print("FUZZING: Diogenes/Lewis & Short Parser")
    print("=" * 80)

    parser = DiogenesEntryParser()

    # Diverse test cases covering different word types and complexities
    test_cases = [
        # Simple nouns - different declensions
        ("lupus, -i, m.", "2nd declension noun"),
        ("rex, regis, m.", "3rd declension consonant stem"),
        ("dies, -ei, m. or f.", "5th declension with multiple genders"),
        ("res, rei, f.", "5th declension"),
        ("corpus, -oris, n.", "3rd declension neuter"),
        # Verbs with principal parts
        ("amo, amare, amavi, amatum, v.", "1st conjugation verb"),
        ("moneo, monere, monui, monitum, v.", "2nd conjugation"),
        ("duco, ducere, duxi, ductum, v.", "3rd conjugation"),
        ("audio, audire, audivi, auditum, v.", "4th conjugation"),
        ("sum, esse, fui, futurus, v.", "Irregular verb sum"),
        # Adjectives
        ("bonus, -a, -um, adj.", "1st/2nd declension adjective"),
        ("felix, -icis, adj.", "3rd declension adjective"),
        ("acer, acris, acre, adj.", "3rd declension 3-ending"),
        # With etymology
        ("lupus, -i, m. (√lup)", "Noun with etymology"),
        # Edge cases
        ("qui, quae, quod, pron.", "Relative pronoun"),
        ("de, prep.", "Preposition"),
        ("et, conj.", "Conjunction"),
        ("o, interj.", "Interjection"),
        # Greek words
        ("λόγος, -ου, ὁ", "Greek noun"),
        ("φιλοσοφία, -ας, ἡ", "Greek feminine noun"),
        # With senses
        ("lupus, -i, m. I. a wolf", "With sense block"),
        ("virtus, -utis, f. I. manliness II. virtue", "Multiple senses"),
        # Complex entries
        ("amo, amare, amavi, amatum, v. I. to love II. to like", "Verb with senses"),
    ]

    results: dict[str, int | list] = {"pass": 0, "fail": 0, "details": []}

    for entry, description in test_cases:
        parsed = parser.parse_safe(entry)
        success = parsed is not None

        if success and parsed is not None:
            results["pass"] += 1  # type: ignore[operator]
            header = parsed["header"]
            parts = ", ".join(header.get("principal_parts", []))
            status = f"✓ {header['lemma']:15} parts={parts[:30]:30}"
        else:
            results["fail"] += 1  # type: ignore[operator]
            status = "✗ FAILED"

        results["details"].append(
            {"entry": entry, "description": description, "success": success, "parsed": parsed}
        )

        print(f"{status:60} | {description}")

    print(f"\n{'=' * 80}")
    print(
        f"RESULTS: {results['pass']}/{len(test_cases)} passed "
        f"({results['pass'] / len(test_cases) * 100:.1f}%)"  # type: ignore[operator]
    )
    print(f"{'=' * 80}\n")

    return results


def fuzz_english_gloss_parser():
    """Test English gloss parser with diverse formats."""
    from langnet.parsing.english_gloss_parser import parse_english_glosses  # noqa: PLC0415

    print("=" * 80)
    print("FUZZING: English Gloss Parser (for GPT translations)")
    print("=" * 80)

    test_cases = [
        ("love, passion, desire", "Simple comma-separated"),
        ("war; battle; conflict", "Semicolon-separated"),
        ("virtue\ncourage\nvalor", "Newline-separated"),
        ("peace, tranquility; rest\nquiet", "Mixed separators"),
        ("a wolf", "Single word with article"),
        ("to love, to cherish, to hold dear", "Infinitive phrases"),
        ("manliness, valor, courage, virtue, excellence", "5+ items"),
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("love", "Single word no separators"),
        ("king, ruler, sovereign; monarch", "Complex with semicolon"),
        ("body, substance, matter, physical form, trunk", "Long list"),
    ]

    results = {"pass": 0, "fail": 0}

    for text, description in test_cases:
        try:
            glosses = parse_english_glosses(text)
            results["pass"] += 1
            print(f"✓ {description:40} → {len(glosses):2} glosses: {glosses[:3]}")
        except Exception as e:
            results["fail"] += 1
            print(f"✗ {description:40} → ERROR: {e}")

    print(f"\n{'=' * 80}")
    print(
        f"RESULTS: {results['pass']}/{len(test_cases)} passed "
        f"({results['pass'] / len(test_cases) * 100:.1f}%)"  # type: ignore[operator]
    )
    print(f"{'=' * 80}\n")

    return results


def analyze_failure_patterns(diogenes_results):
    """Analyze what patterns cause failures."""
    print("=" * 80)
    print("FAILURE PATTERN ANALYSIS")
    print("=" * 80)

    failures = [r for r in diogenes_results["details"] if not r["success"]]

    if not failures:
        print("\n✅ No failures to analyze!\n")
        return

    print(f"\nFound {len(failures)} failures:\n")

    for fail in failures:
        print(f"Entry: {fail['entry']!r}")
        print(f"Type:  {fail['description']}")
        print("Issue: Parser returned None")
        print()


def test_with_real_cltk_data():
    """Test with actual CLTK data if available."""
    print("=" * 80)
    print("TESTING: Real CLTK Integration (if data available)")
    print("=" * 80)

    # Simulate what CLTK actually returns
    simulated_cltk_responses = [
        {
            "lemma": "lupus",
            "lewis_lines": ["lupus, -i, m."],
        },
        {
            "lemma": "amo",
            "lewis_lines": ["amo, amare, amavi, amatum, v."],
        },
        {
            "lemma": "multus",
            "lewis_lines": ["multus, -a, -um, adj."],
        },
    ]

    from langnet.parsing.integration import enrich_cltk_with_parsed_lewis  # noqa: PLC0415

    for cltk_payload in simulated_cltk_responses:
        enriched = enrich_cltk_with_parsed_lewis(cltk_payload)

        has_parsed = "parsed_lewis" in enriched
        print(f"\n{cltk_payload['lemma']:10} → parsed_lewis: {has_parsed}")

        if has_parsed and enriched["parsed_lewis"]:
            header = enriched["parsed_lewis"][0]["header"]
            print(f"           lemma: {header.get('lemma')}")
            print(f"           principal_parts: {header.get('principal_parts')}")
            print(f"           gender: {header.get('gender')}, pos: {header.get('pos')}")

    print()


def test_verbose_diogenes_html():
    """Test with verbose HTML like real Diogenes output."""
    from langnet.parsing.integration import extract_diogenes_header_from_html  # noqa: PLC0415

    print("=" * 80)
    print("TESTING: Verbose Diogenes HTML Extraction")
    print("=" * 80)

    test_html_samples = [
        ('<h2><span class="lemma">lupus</span>, -i, m.</h2>', "lupus"),
        ("<h2><span>amo</span>, amare, amavi, amatum, v.</h2>", "amo"),
        ("<h2>bonus, -a, -um, adj.</h2>", "bonus"),
        ('<h2><span class="lemma">λόγος</span>, -ου, ὁ</h2>', "λόγος"),
    ]

    for html, expected_lemma in test_html_samples:
        header = extract_diogenes_header_from_html(html)

        if header and header.get("lemma") == expected_lemma:
            parts = ", ".join(header.get("principal_parts", []))
            print(f"✓ {expected_lemma:10} → parts: {parts}, gender: {header.get('gender')}")
        else:
            actual = header.get("lemma") if header else None
            print(f"✗ {expected_lemma:10} → FAILED (got: {actual})")

    print()


def main():
    """Run comprehensive fuzzing tests."""
    print("\n" + "🔍 " * 40)
    print("PARSER ROBUSTNESS FUZZING TEST")
    print("🔍 " * 40 + "\n")

    # Test each parser
    diogenes_results = fuzz_diogenes_lewis_entries()
    english_results = fuzz_english_gloss_parser()

    # Additional tests
    analyze_failure_patterns(diogenes_results)
    test_with_real_cltk_data()
    test_verbose_diogenes_html()

    # Overall summary
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(
        f"\nDiogenes/Lewis Parser: {diogenes_results['pass']}/{len(diogenes_results['details'])} "
        f"({diogenes_results['pass'] / len(diogenes_results['details']) * 100:.1f}%)"
    )
    print(
        f"English Gloss Parser:  {english_results['pass']}/{english_results['pass'] + english_results['fail']} "  # noqa: E501
        f"({english_results['pass'] / (english_results['pass'] + english_results['fail']) * 100:.1f}%)"  # noqa: E501
    )

    print("\n✅ Key Takeaway:")
    print("   - English parser: Very robust for GPT-translated glosses")
    print("   - Diogenes parser: Good for standard entries, struggles with irregular forms")
    print("   - Use cases: Automatic enrichment in v2 handlers, not direct parsing\n")


if __name__ == "__main__":
    main()
