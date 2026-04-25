#!/usr/bin/env python3
"""Test parsers with actual real-world API data.

This tests with data fetched from live APIs to verify parser robustness.
"""

from __future__ import annotations

import unittest


class RealWorldCLTKTests(unittest.TestCase):
    """Test CLTK parser with actual API data."""

    def test_cltk_lewis_lines_format(self):
        """CLTK lewis_lines have a different format than expected."""
        from langnet.parsing.integration import parse_lewis_lines  # noqa: PLC0415

        # Actual CLTK lewis_lines from API (fetched 2026-04-12)
        real_cltk_data = [
            # lupus - has newlines and irregular spacing
            "lupus\n\n\n ī, \nm\n\n a wolf: Torva leaena lupum sequitur...",
            # amo - has macrons, no dash prefix on principal parts
            "amō āvī, ātus, āre AM-, to love: magis te, quam oculos...",
        ]

        print("\n=== Testing with REAL CLTK lewis_lines format ===")
        for line in real_cltk_data:
            print(f"\nInput: {line[:60]}...")
            parsed = parse_lewis_lines([line])
            print(f"Result: {'PARSED' if parsed else 'FAILED'}")
            if parsed:
                header = parsed[0]["header"]
                print(f"  Lemma: {header.get('lemma')}")
                print(f"  Principal parts: {header.get('principal_parts')}")

        # Current expectation: These will FAIL because format is different
        # CLTK format: "amō āvī, ātus, āre"
        # Our parser expects: "amo, amare, amavi, amatum, v."


class RealWorldDiogenesTests(unittest.TestCase):
    """Test Diogenes parser with actual API data."""

    def test_diogenes_entry_format(self):
        """Test with actual Diogenes entry format from API."""
        from langnet.parsing.diogenes_parser import DiogenesEntryParser  # noqa: PLC0415

        # Actual format from Diogenes API
        real_diogenes_entries = [
            "lupus, i, m. kindred with λύκος",
            "lupus, i, m. I. a wolf",
        ]

        print("\n=== Testing with REAL Diogenes format ===")
        parser = DiogenesEntryParser()
        for entry in real_diogenes_entries:
            print(f"\nInput: {entry}")
            parsed = parser.parse_safe(entry)
            success = parsed is not None
            print(f"Result: {'PARSED' if success else 'FAILED'}")
            if success:
                header = parsed["header"]  # type: ignore[index]
                print(f"  Lemma: {header.get('lemma')}")
                print(f"  Principal parts: {header.get('principal_parts')}")
                print(f"  Gender: {header.get('gender')}")

    def test_second_conjugation_debug(self):
        """Debug why 2nd conjugation verbs fail."""
        from langnet.parsing.diogenes_parser import DiogenesEntryParser  # noqa: PLC0415

        parser = DiogenesEntryParser()

        # Test cases with different formats
        test_cases = [
            ("moneo, monere, monui, monitum, v.", "2nd conj with v."),
            ("moneo, monere, monui, monitum, v", "2nd conj without period"),
            ("moneo, -ere, -ui, -itum, v.", "2nd conj with dashes"),
            ("video, videre, vidi, visum, v.", "2nd conj video"),
            ("audio, audire, audivi, auditum, v.", "4th conj for comparison"),
        ]

        print("\n=== Debugging 2nd conjugation failures ===")
        for entry, description in test_cases:
            parsed = parser.parse_safe(entry)
            status = "✓" if parsed else "✗"
            print(f"{status} {description:30} | {entry}")
            if parsed:
                parts = ", ".join(parsed["header"].get("principal_parts", []))
                print(f"    → {parts[:50]}")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
