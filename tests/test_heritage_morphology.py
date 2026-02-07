#!/usr/bin/env python3
"""
Test suite for Heritage Platform backend functionality
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from langnet.heritage.config import heritage_config
from langnet.heritage.models import (
    HeritageMorphologyResult,
    HeritageSolution,
    HeritageWordAnalysis,
)
from langnet.heritage.morphology import HeritageMorphologyService
from langnet.heritage.parameters import HeritageParameterBuilder


class TestHeritageParameterBuilder(unittest.TestCase):
    """Test suite for HeritageParameterBuilder"""

    def test_build_morphology_params_velthuis(self):
        """Test building morphology parameters with Velthuis encoding"""
        params = HeritageParameterBuilder.build_morphology_params(
            text="agni", encoding="velthuis", max_solutions=5
        )

        self.assertEqual(params["text"], "agnii")  # Should double final vowels in Velthuis
        self.assertEqual(params["t"], "VH")
        self.assertEqual(params["max"], "5")

    def test_build_search_params(self):
        """Test building search parameters"""
        params = HeritageParameterBuilder.build_search_params(
            query="yoga", lexicon="MW", max_results=10, encoding="velthuis"
        )

        self.assertEqual(params["lex"], "MW")
        self.assertEqual(params["q"], "yoga")
        self.assertEqual(params["t"], "VH")
        self.assertEqual(params["max"], "10")

    def test_build_lemma_params(self):
        """Test building lemmatization parameters"""
        params = HeritageParameterBuilder.build_lemma_params(word="योगेन", encoding="velthuis")

        self.assertEqual(params["word"], "योगेन")
        self.assertEqual(params["t"], "VH")

    def test_get_cgi_encoding_param(self):
        """Test CGI encoding parameter mapping"""
        self.assertEqual(HeritageParameterBuilder.get_cgi_encoding_param("velthuis"), "VH")
        self.assertEqual(HeritageParameterBuilder.get_cgi_encoding_param("itrans"), "IT")
        self.assertEqual(HeritageParameterBuilder.get_cgi_encoding_param("slp1"), "SL")
        self.assertEqual(
            HeritageParameterBuilder.get_cgi_encoding_param("unknown"), "VH"
        )  # default


class TestHeritageModels(unittest.TestCase):
    """Test suite for Heritage data models"""

    def test_heritage_word_analysis(self):
        """Test HeritageWordAnalysis model"""
        analysis = HeritageWordAnalysis(
            word="agni",
            lemma="agni",
            root="अग्नि",
            pos="noun",
            case=None,
            gender=None,
            number=None,
            meaning=["fire", "god of fire"],
        )

        self.assertEqual(analysis.word, "agni")
        self.assertEqual(analysis.lemma, "agni")
        self.assertEqual(analysis.pos, "noun")
        self.assertEqual(len(analysis.meaning), 2)

    def test_heritage_solution(self):
        """Test HeritageSolution model"""
        analysis = HeritageWordAnalysis(
            word="agni", lemma="agni", root="अग्नि", pos="noun", meaning=["fire"]
        )

        solution = HeritageSolution(
            type="morphological", analyses=[analysis], total_words=1, score=0.95
        )

        self.assertEqual(solution.type, "morphological")
        self.assertEqual(len(solution.analyses), 1)
        self.assertEqual(solution.total_words, 1)
        self.assertEqual(solution.score, 0.95)

    def test_heritage_morphology_result(self):
        """Test HeritageMorphologyResult model"""
        analysis = HeritageWordAnalysis(
            word="agni", lemma="agni", root="अग्नि", pos="noun", meaning=["fire"]
        )

        solution = HeritageSolution(
            type="morphological", analyses=[analysis], total_words=1, score=0.95
        )

        result = HeritageMorphologyResult(
            input_text="agni",
            solutions=[solution],
            word_analyses=[],
            total_solutions=1,
            encoding="velthuis",
            processing_time=0.5,
        )

        self.assertEqual(result.input_text, "agni")
        self.assertEqual(len(result.solutions), 1)
        self.assertEqual(result.total_solutions, 1)
        self.assertEqual(result.encoding, "velthuis")
        self.assertGreater(result.processing_time, 0)


class TestHeritageMorphologyService(unittest.TestCase):
    """Test suite for HeritageMorphologyService"""

    @patch("langnet.heritage.morphology.HeritageHTTPClient")
    @patch("langnet.heritage.morphology.MorphologyParser")
    def test_analyze_success(self, mock_parser, mock_client):
        """Test successful morphology analysis"""
        # Mock HTML response
        mock_html = "<html><body><span>Solution 1</span><table>...</table></body></html>"

        # Mock parser response
        mock_parser.return_value.parse.return_value = {
            "solutions": [
                {
                    "type": "morphological_analysis",
                    "solution_number": 1,
                    "entries": [
                        {
                            "word": "agni",
                            "lemma": "agni",
                            "root": "अग्नि",
                            "pos": "noun",
                            "meaning": ["fire"],
                        }
                    ],
                    "total_words": 1,
                }
            ],
            "total_solutions": 1,
            "word_analyses": [],
            "encoding": "velthuis",
        }

        # Mock client
        mock_client_instance = Mock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_client_instance.fetch_cgi_script.return_value = mock_html
        mock_client.return_value = mock_client_instance

        # Test service
        service = HeritageMorphologyService()
        result = service.analyze("agni", encoding="velthuis", max_solutions=2)

        self.assertEqual(result.input_text, "agni")
        self.assertEqual(result.total_solutions, 1)
        self.assertEqual(len(result.solutions), 1)
        self.assertEqual(len(result.solutions[0].analyses), 1)
        self.assertEqual(result.solutions[0].analyses[0].word, "agni")

        # Verify correct parameters were passed - Velthuis encoding doubles final long vowels
        # and includes optimized parameters from VELTHUIS_INPUT_TIPS.md
        expected_params = {
            "text": "agnii",
            "t": "VH",
            "lex": "SH",
            "font": "roma",
            "cache": "t",
            "st": "t",
            "us": "f",
            "topic": "",
            "abs": "f",
            "corpmode": "",
            "corpdir": "",
            "sentno": "",
            "mode": "p",
            "cpts": "",
            "max": "2",
        }
        mock_client_instance.fetch_cgi_script.assert_called_once_with(
            "sktreader", params=expected_params, timeout=None
        )

    @patch("langnet.heritage.morphology.HeritageHTTPClient")
    def test_analyze_error_handling(self, mock_client):
        """Test error handling in morphology analysis"""
        # Mock client to raise exception
        mock_client_instance = Mock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_client_instance.fetch_cgi_script.side_effect = Exception("Connection error")
        mock_client.return_value = mock_client_instance

        # Test service
        service = HeritageMorphologyService()

        with self.assertRaises(Exception) as context:
            service.analyze("agni", encoding="velthuis")

        self.assertIn("Connection error", str(context.exception))


class TestHeritageIntegration(unittest.TestCase):
    """Integration tests for Heritage Platform"""

    def test_end_to_end_morphology_analysis(self):
        """Test complete morphology analysis workflow"""
        # Test parameter building
        params = HeritageParameterBuilder.build_morphology_params(
            text="agni", encoding="velthuis", max_solutions=3
        )

        # Verify expected parameters - Velthuis encoding doubles final long vowels
        self.assertEqual(params["text"], "agnii")
        self.assertEqual(params["t"], "VH")
        self.assertEqual(params["max"], "3")

        # Test URL construction - expect doubled vowel
        expected_url = f"{heritage_config.base_url}/cgi-bin/skt/sktreader?text=agnii&t=VH&max=3"
        self.assertEqual(
            expected_url, "http://localhost:48080/cgi-bin/skt/sktreader?text=agnii&t=VH&max=3"
        )

    def test_multiple_encodings_support(self):
        """Test support for different text encodings"""
        test_cases = [
            ("velthuis", "VH"),
            ("itrans", "IT"),
            ("slp1", "SL"),
            ("devanagari", "DN"),
        ]

        for encoding, expected_param in test_cases:
            params = HeritageParameterBuilder.build_search_params(query="test", encoding=encoding)
            self.assertEqual(params["t"], expected_param)


if __name__ == "__main__":
    unittest.main()
