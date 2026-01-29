from typing import Any

import structlog

from ..cologne.core import SanskritCologneLexicon

logger = structlog.get_logger(__name__)


class HeritageDictionaryService:
    """Service combining Heritage morphology with CDSL dictionary lookup"""

    def __init__(self):
        self.scl = SanskritCologneLexicon()

    def lookup_word(self, word: str, dict_id: str = "MW") -> dict[str, Any]:
        """Look up a word in the CDSL dictionary"""
        try:
            # Use SanskritCologneLexicon which handles SLP1 conversion automatically
            result = self.scl.lookup_ascii(word)

            # Extract the specific dictionary results
            dict_key = dict_id.lower()
            entries = result.get("dictionaries", {}).get(dict_key, [])

            return {
                "word": word,
                "dict_id": dict_id,
                "entries": entries,
                "transliteration": result.get("transliteration", {}),
                "root": result.get("root"),
            }

        except Exception as e:
            logger.error("Dictionary lookup failed", word=word, error=str(e))
            return {
                "word": word,
                "dict_id": dict_id,
                "error": str(e),
                "entries": [],
                "transliteration": {},
            }

    def get_word_info(self, word: str) -> dict[str, Any]:
        """Get comprehensive word information including dictionary entries"""
        try:
            # Get MW dictionary entry
            mw_result = self.lookup_word(word, "MW")

            # Get AP90 dictionary entry if available
            ap90_result = self.lookup_word(word, "AP90")

            # Combine results
            return {
                "word": word,
                "mw_entries": mw_result.get("entries", []),
                "ap90_entries": ap90_result.get("entries", []),
                "transliteration": mw_result.get("transliteration", {}),
                "root": mw_result.get("root"),
                "total_entries": len(mw_result.get("entries", []))
                + len(ap90_result.get("entries", [])),
            }

        except Exception as e:
            logger.error("Word info lookup failed", word=word, error=str(e))
            return {
                "word": word,
                "error": str(e),
                "mw_entries": [],
                "ap90_entries": [],
                "transliteration": {},
                "root": None,
                "total_entries": 0,
            }
