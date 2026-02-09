import unittest

from langnet.validation import (
    LANG_ALIASES,
    normalize_language,
    validate_query,
    validate_tool_request,
)


class ValidationTests(unittest.TestCase):
    def test_normalize_language_accepts_alias(self):
        self.assertEqual(normalize_language("grk"), LANG_ALIASES["grk"])

    def test_validate_query_missing_word(self):
        error, lang = validate_query("lat", "")
        self.assertIsNone(lang)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("Search term cannot be empty", error)

    def test_validate_tool_request_success(self):
        error = validate_tool_request("diogenes", "parse", "lat", "amo")
        self.assertIsNone(error)

    def test_validate_tool_request_rejects_unknown_tool(self):
        error = validate_tool_request("unknown", "parse", "lat", "amo")
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("Invalid tool", error)

    def test_validate_tool_request_rejects_bad_action(self):
        error = validate_tool_request("whitakers", "parse", "lat", "amo")
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("Invalid action", error)


if __name__ == "__main__":
    unittest.main()
