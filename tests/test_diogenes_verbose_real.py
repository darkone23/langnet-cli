"""Test parser with realistic verbose Diogenes output."""

from __future__ import annotations

import unittest

from query_spec import ToolCallSpec, ToolStage

from langnet.clients.base import RawResponseEffect
from langnet.execution.handlers.diogenes import _parse_diogenes_html, extract_html


class DiogenesVerboseRealWorldTests(unittest.TestCase):
    """Test with realistic verbose Diogenes HTML."""

    def test_parse_logos_greek_verbose(self) -> None:
        """Test parsing λόγος - a very verbose entry with multiple senses."""
        # Simplified version of real Diogenes output for λόγος
        html = """
        <html>
        <h1>Perseus analysis</h1>
        <ul>
            <li>λόγος, λόγου: noun masc nom sg</li>
            <li>λόγος, λόγου: noun masc voc sg</li>
        </ul>

        <hr />

        <div id="logeion_links" class="logeion-link">
            <span>Could not find dictionary headword</span>
            <span>Showing nearest entry</span>
        </div>

        <hr />

        <h2><span class="lemma">λόγος</span>, -ου, ὁ</h2>

        <div id="sense" style="padding-left: 0px;">
            I. the word by which the inward thought is expressed, Lat. oratio
            <span class="origjump perseus:abo:tlg,0012,001:1:1">Hom. Il. 1.1</span>
        </div>

        <div id="sense" style="padding-left: 20px;">
            A. speech, discourse
            <span class="origjump perseus:abo:tlg,0059,001:1:1">Hdt. 1.1</span>
        </div>

        <div id="sense" style="padding-left: 40px;">
            1. a particular saying, statement
            <span class="origjump perseus:abo:tlg,0086,001:1:1">Pl. Rep. 1.1</span>
        </div>

        <div id="sense" style="padding-left: 20px;">
            B. the inward thought itself, Lat. ratio
        </div>

        <div id="sense" style="padding-left: 40px;">
            1. reason, understanding
        </div>

        <div id="sense" style="padding-left: 40px;">
            2. account, reckoning
        </div>

        <div id="sense" style="padding-left: 0px;">
            II. the relation or proportion of one thing to another, analogy
        </div>

        <div id="sense" style="padding-left: 20px;">
            A. in Mathematics, ratio, proportion
        </div>

        <div id="sense" style="padding-left: 0px;">
            III. reflection, deliberation
        </div>
        </html>
        """

        result = _parse_diogenes_html(html)

        # Should parse multiple chunks
        self.assertGreater(len(result["chunks"]), 0)

        # Should identify as fuzzy (nearest entry)
        self.assertTrue(result.get("is_fuzzy_overall"))

        # Should have morphology chunk
        morph_chunks = [
            c for c in result["chunks"] if c.get("chunk_type") == "PerseusAnalysisHeader"
        ]
        self.assertGreater(len(morph_chunks), 0)

        # Should have definition chunks
        def_chunks = [
            c
            for c in result["chunks"]
            if c.get("chunk_type") in {"DiogenesMatchingReference", "DiogenesFuzzyReference"}
        ]
        self.assertGreater(len(def_chunks), 0)

        # Check that definitions have nested structure
        if def_chunks:
            defs = def_chunks[0].get("definitions", {})
            blocks = defs.get("blocks", [])
            self.assertGreater(len(blocks), 3)  # Should have multiple sense blocks

    def test_parse_amo_latin_verbose(self) -> None:
        """Test parsing 'amo' - verbose Latin verb with many senses."""
        html = """
        <html>
        <h1>Perseus analysis</h1>
        <ul>
            <li>amo, amare, amavi, amatum: verb 1st sg pres act ind</li>
        </ul>

        <hr />

        <h2><span>amo</span>, āre, āvi, ātum, 1, v. a.</h2>

        <div id="sense" style="padding-left: 0px;">
            I. To love (as a general term for affection of every kind)
            <span class="origjump perseus:abo:phi,0474,056:1:1">Cic. Fam. 1.1</span>
        </div>

        <div id="sense" style="padding-left: 20px;">
            A. Of persons
        </div>

        <div id="sense" style="padding-left: 40px;">
            1. To love in a sexual sense
            <span class="origjump perseus:abo:phi,0959,001:1:1">Verg. Aen. 1.1</span>
        </div>

        <div id="sense" style="padding-left: 40px;">
            2. To love as a friend
        </div>

        <div id="sense" style="padding-left: 20px;">
            B. Of things, to be fond of, have a predilection for
            <span class="origjump perseus:abo:phi,0893,001:1:1">Hor. Carm. 1.1</span>
        </div>

        <div id="sense" style="padding-left: 40px;">
            1. With inf., to be wont, be accustomed
        </div>

        <div id="sense" style="padding-left: 40px;">
            2. To like, choose, prefer
        </div>

        <div id="sense" style="padding-left: 0px;">
            II. In colloq. lang., to say please, if you please (= si me amas)
        </div>
        </html>
        """

        result = _parse_diogenes_html(html)

        self.assertTrue(result["dg_parsed"])
        self.assertGreater(len(result["chunks"]), 0)

        # Check for both morphology and definitions
        chunk_types = [c.get("chunk_type") for c in result["chunks"]]
        self.assertIn("PerseusAnalysisHeader", chunk_types)

    def test_extract_from_verbose_html(self) -> None:
        """Test full extraction pipeline with verbose HTML."""
        # Realistic verbose HTML
        html = b"""
        <html>
        <h1>Perseus analysis</h1>
        <ul>
            <li>lupus, lupi: noun masc nom sg</li>
            <li>lupus, lupi: noun masc voc sg</li>
        </ul>
        <hr />
        <h2><span>lupus</span>, i, m.</h2>
        <div id="sense" style="padding-left: 0px;">
            I. A wolf
            <span class="origjump perseus:abo:phi,0474,001:1:1">Cic. N. D. 1.1</span>
        </div>
        <div id="sense" style="padding-left: 20px;">
            A. Lit., the animal
            <span class="origjump perseus:abo:phi,0959,001:1:1">Verg. Ecl. 1.1</span>
        </div>
        <div id="sense" style="padding-left: 20px;">
            B. Transf., a greedy, rapacious person
            <span class="origjump perseus:abo:phi,0119,001:1:1">Plaut. Aul. 1.1</span>
        </div>
        <div id="sense" style="padding-left: 0px;">
            II. A kind of fish, the pike
            <span class="origjump perseus:abo:phi,0978,001:1:1">Plin. H. N. 1.1</span>
        </div>
        </html>
        """

        raw = RawResponseEffect(
            response_id="test-resp",
            tool="fetch.diogenes",
            call_id="test-call",
            endpoint="http://example.com",
            status_code=200,
            content_type="text/html",
            headers={},
            body=html,
        )

        call = ToolCallSpec(
            tool="extract.diogenes.html",
            call_id="test-extract",
            endpoint="internal://extract",
            params={"q": "lupus"},
            stage=ToolStage.TOOL_STAGE_EXTRACT,
        )

        result = extract_html(call, raw)

        # Should extract lemmas
        self.assertIn("lemmas", result.payload)
        lemmas = result.payload.get("lemmas", [])
        self.assertGreater(len(lemmas), 0)

        # Should have parsed data
        self.assertIn("parsed", result.payload)
        parsed = result.payload.get("parsed", {})
        self.assertTrue(parsed.get("dg_parsed"))

        # Should have parsed_header (v2 feature)
        self.assertIn("parsed_header", result.payload)
        parsed_header = result.payload.get("parsed_header")
        if parsed_header:
            self.assertEqual(parsed_header["lemma"], "lupus")
            self.assertIn("i", parsed_header["principal_parts"])


if __name__ == "__main__":
    unittest.main()
