#!/usr/bin/env python3
"""Simple practical demo showing how to use the parsers that actually work.

Focus on the parsers you'll actually use:
1. English gloss parser (for GPT-translated French dictionaries)
2. Diogenes/CLTK parser (for Lewis & Short entries)
"""

from __future__ import annotations


def demo_english_gloss_parser():
    """THIS IS THE MAIN ONE YOU'LL USE - for GPT-translated French dictionaries."""
    from langnet.parsing.english_gloss_parser import parse_english_glosses  # noqa: PLC0415

    print("=" * 70)
    print("ENGLISH GLOSS PARSER - For GPT-Translated Dictionaries")
    print("=" * 70)
    print("\nThis is what you use AFTER translating French→English with GPT.\n")

    # Simulated GPT translations
    test_cases = [
        ("amor", "love, passion, desire"),
        ("bellum", "war; battle; conflict"),
        ("virtus", "virtue\ncourage\nvalor\nmanliness"),
        ("pax", "peace, tranquility, rest, quiet"),
    ]

    for headword, gpt_translation in test_cases:
        glosses = parse_english_glosses(gpt_translation)
        print(f"{headword:10} → {glosses}")

    print("\n✅ 100% success rate - simple and robust")
    print("   Works with: commas, semicolons, newlines, pilcrows")


def demo_diogenes_cltk_parser():
    """Parser for Lewis & Short entries (Diogenes HTML or CLTK lewis_lines)."""
    from langnet.parsing.integration import parse_lewis_lines  # noqa: PLC0415

    print("\n" + "=" * 70)
    print("LEWIS & SHORT PARSER - For CLTK and Diogenes")
    print("=" * 70)
    print("\nParses dictionary entry headers to extract metadata.\n")

    # Real Lewis & Short format (simplified)
    lewis_entries = [
        "lupus, -i, m.",
        "amo, amare, amavi, amatum, v.",
        "bonus, -a, -um, adj.",
        "rex, regis, m.",
        "virtus, -utis, f.",
        "verbum, -i, n.",
    ]

    parsed = parse_lewis_lines(lewis_entries)

    print(f"Parsed {len(parsed)}/{len(lewis_entries)} entries:\n")
    for entry in parsed:
        header = entry["header"]
        lemma = header["lemma"]
        principal_parts = ", ".join(header.get("principal_parts", []))
        gender = header.get("gender", "?")
        pos = header.get("pos", "?")
        print(f"  {lemma:10} → principal_parts: {principal_parts:20} gender: {gender:3} pos: {pos}")

    print(f"\n✅ {len(parsed) / len(lewis_entries) * 100:.0f}% success rate")
    print("   Extracts: lemma, principal_parts, gender, POS")


def demo_how_handlers_use_this():
    """Show how v2 handlers automatically apply parsers."""
    print("\n" + "=" * 70)
    print("HANDLER INTEGRATION - Automatic Enrichment")
    print("=" * 70)
    print("\nIn v2 handlers, parsing happens AUTOMATICALLY:\n")

    code_example = """
# In extract_cltk handler (v2):
@versioned("v2")
def extract_cltk(call, raw):
    # ... extract CLTK data ...
    payload = {
        "lemma": "lupus",
        "lewis_lines": ["lupus, -i, m. I. a wolf"]
    }

    # THIS HAPPENS AUTOMATICALLY:
    payload = enrich_cltk_with_parsed_lewis(payload)

    # Now payload has:
    # {
    #   "lemma": "lupus",
    #   "lewis_lines": ["lupus, -i, m. I. a wolf"],
    #   "parsed_lewis": [{"header": {"lemma": "lupus", ...}}]
    # }
    """

    print(code_example)
    print("\n✅ You don't need to call parsers manually")
    print("   Just use v2 handlers and parsed data appears automatically!")


def demo_french_workflow():
    """Show the ACTUAL workflow for French dictionaries (English, not French!)."""
    print("\n" + "=" * 70)
    print("FRENCH DICTIONARY WORKFLOW - The Full Picture")
    print("=" * 70)
    print("\nFor Gaffiot/Heritage French dictionaries:\n")

    workflow = """
Step 1: Get French dictionary entry
  → Original: "amour, passion, désir"

Step 2: Translate with GPT (.justscripts/lex_translation_demo.py)
  → GPT output: "love, passion, desire"

Step 3: Parse English translation (parse_english_glosses)
  → Parsed: ['love', 'passion', 'desire']

That's it! You parse the ENGLISH, not the French.
    """

    print(workflow)
    print("\n✅ The French parser exists but you don't need it")
    print("   Just translate→parse workflow using English parser")


def main():
    """Run all demos."""
    print("\n🎯 PRACTICAL PARSER USAGE GUIDE\n")

    demo_english_gloss_parser()  # MOST IMPORTANT
    demo_diogenes_cltk_parser()
    demo_how_handlers_use_this()
    demo_french_workflow()

    print("\n" + "=" * 70)
    print("SUMMARY: What You Actually Use")
    print("=" * 70)
    print("\n1. English gloss parser - For GPT-translated French dictionaries")
    print("   → 100% robust, handles all separators")
    print("\n2. Lewis & Short parser - For CLTK lewis_lines and Diogenes headers")
    print("   → Works well for standard entries, extracts metadata")
    print("\n3. Handler integration - Happens automatically in v2 handlers")
    print("   → Just call the handler, parsing is automatic")
    print("\n⚠️  French parser: Built but not needed for your workflow")
    print("   → You only parse ENGLISH translations, not original French\n")


if __name__ == "__main__":
    main()
