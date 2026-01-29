from typing import Any

# Import indic_transliteration library with proper error handling
try:
    from indic_transliteration.sanscript import DEVANAGARI, ITRANS, SLP1, VELTHUIS, transliterate

    HAS_INDIC_TRANSLIT = True
    DEVANAGARI_AVAILABLE = DEVANAGARI
    VELTHUIS_AVAILABLE = VELTHUIS
    ITRANS_AVAILABLE = ITRANS
    SLP1_AVAILABLE = SLP1
except ImportError:
    HAS_INDIC_TRANSLIT = False
    transliterate: Any | None = None
    DEVANAGARI_AVAILABLE = None
    VELTHUIS_AVAILABLE = None
    ITRANS_AVAILABLE = None
    SLP1_AVAILABLE = None


class HeritageParameterBuilder:
    """Utility class for building CGI script parameters"""

    @staticmethod
    def encode_text(text: str, encoding: str = "velthuis") -> str:
        """Encode Sanskrit text using specified encoding"""
        if HAS_INDIC_TRANSLIT and transliterate is not None:
            # Use indic_transliteration library if available
            if encoding == "velthuis" and VELTHUIS_AVAILABLE:
                return transliterate(text, DEVANAGARI_AVAILABLE, VELTHUIS_AVAILABLE)
            elif encoding == "itrans" and ITRANS_AVAILABLE:
                return transliterate(text, DEVANAGARI_AVAILABLE, ITRANS_AVAILABLE)
            elif encoding == "slp1" and SLP1_AVAILABLE:
                return transliterate(text, DEVANAGARI_AVAILABLE, SLP1_AVAILABLE)
            else:
                # Return as-is for unknown encodings
                return text
        # Fallback to custom mappings
        elif encoding == "velthuis":
            return HeritageParameterBuilder._to_velthuis(text)
        elif encoding == "itrans":
            return HeritageParameterBuilder._to_itrans(text)
        elif encoding == "slp1":
            return HeritageParameterBuilder._to_slp1(text)
        else:
            # Return as-is for unknown encodings
            return text

    @staticmethod
    def _to_velthuis(text: str) -> str:
        """Convert Devanagari to Velthuis encoding"""
        # Basic Velthuis mapping
        velthuis_map = {
            "अ": "a",
            "आ": "A",
            "इ": "i",
            "ई": "I",
            "उ": "u",
            "ऊ": "U",
            "ए": "e",
            "ऐ": "E",
            "ओ": "o",
            "औ": "O",
            "अं": "M",
            "अः": "H",
            "क": "k",
            "ख": "Kh",
            "ग": "g",
            "घ": "Gh",
            "ङ": "N",
            "च": "c",
            "छ": "Ch",
            "ज": "j",
            "झ": "Jh",
            "ञ": "Y",
            "ट": "T",
            "ठ": "Th",
            "ड": "D",
            "ढ": "Dh",
            "ण": "N",
            "त": "t",
            "थ": "th",
            "द": "d",
            "ध": "dh",
            "न": "n",
            "प": "p",
            "फ": "ph",
            "ब": "b",
            "भ": "bh",
            "म": "m",
            "य": "y",
            "र": "r",
            "ल": "l",
            "व": "v",
            "श": "z",
            "ष": "S",
            "स": "s",
            "ह": "h",
            "ळ": "L",
            "क्ष": "K",
            "ज्ञ": "J",
            "ा": "a",
            "ि": "i",
            "ी": "I",
            "ु": "u",
            "ू": "U",
            "े": "e",
            "ै": "E",
            "ो": "o",
            "ौ": "O",
            "ं": "M",
            "ः": "H",
            "्": "",
            "ँ": "~",
            "ऽ": "'",
            "ॐ": "OM",
        }

        result = ""
        for char in text:
            if char in velthuis_map:
                result += velthuis_map[char]
            else:
                result += char

        return result

    @staticmethod
    def _to_itrans(text: str) -> str:
        """Convert Devanagari to ITRANS encoding"""
        # Basic ITRANS mapping - simplified version
        itrans_map = {
            "अ": "a",
            "आ": "A",
            "इ": "i",
            "ई": "I",
            "उ": "u",
            "ऊ": "U",
            "ए": "e",
            "ऐ": "E",
            "ओ": "o",
            "औ": "O",
            "अं": "M",
            "अः": "H",
            "क": "k",
            "ख": "kh",
            "ग": "g",
            "घ": "gh",
            "ङ": "~N",
            "च": "ch",
            "छ": "Ch",
            "ज": "j",
            "झ": "jh",
            "ञ": "JN",
            "ट": "T",
            "ठ": "Th",
            "ड": "D",
            "ढ": "Dh",
            "ण": "N",
            "त": "t",
            "थ": "th",
            "द": "d",
            "ध": "dh",
            "न": "n",
            "प": "p",
            "फ": "ph",
            "ब": "b",
            "भ": "bh",
            "म": "m",
            "य": "y",
            "र": "r",
            "ल": "l",
            "व": "v",
            "श": "sh",
            "ष": "Sh",
            "स": "s",
            "ह": "h",
            "ळ": "L",
            "क्ष": "kSh",
            "ज्ञ": "j~n",
            "ा": "aa",
            "ि": "i",
            "ी": "ii",
            "ु": "u",
            "ू": "uu",
            "े": "e",
            "ै": "ai",
            "ो": "o",
            "ौ": "au",
            "ं": "M",
            "ः": "H",
            "्": "",
            "ँ": "~",
            "ऽ": "'",
            "ॐ": "OM",
        }

        result = ""
        for char in text:
            if char in itrans_map:
                result += itrans_map[char]
            else:
                result += char

        return result

    @staticmethod
    def _to_slp1(text: str) -> str:
        """Convert Devanagari to SLP1 encoding"""
        # Basic SLP1 mapping - simplified version
        slp1_map = {
            "अ": "a",
            "आ": "A",
            "इ": "i",
            "ई": "I",
            "उ": "u",
            "ऊ": "U",
            "ए": "e",
            "ऐ": "E",
            "ओ": "o",
            "औ": "O",
            "अं": "M",
            "अः": "H",
            "क": "k",
            "ख": "K",
            "ग": "g",
            "घ": "G",
            "ङ": "N",
            "च": "c",
            "छ": "C",
            "ज": "j",
            "झ": "J",
            "ञ": "Y",
            "ट": "w",
            "ठ": "W",
            "ड": "q",
            "ढ": "Q",
            "ण": "R",
            "त": "t",
            "थ": "T",
            "द": "d",
            "ध": "D",
            "न": "n",
            "प": "p",
            "फ": "P",
            "ब": "b",
            "भ": "B",
            "म": "m",
            "य": "y",
            "र": "r",
            "ल": "l",
            "व": "v",
            "श": "S",
            "ष": "z",
            "स": "s",
            "ह": "h",
            "ळ": "Z",
            "क्ष": "kz",
            "ज्ञ": "d~Z",
            "ा": "A",
            "ि": "i",
            "ी": "I",
            "ु": "u",
            "ू": "U",
            "े": "e",
            "ै": "E",
            "ो": "o",
            "ौ": "O",
            "ं": "M",
            "ः": "H",
            "्": "",
            "ँ": "~",
            "ऽ": "'",
            "ॐ": "aM",
        }

        result = ""
        for char in text:
            if char in slp1_map:
                result += slp1_map[char]
            else:
                result += char

        return result

    @staticmethod
    def get_cgi_encoding_param(encoding: str) -> str:
        """Get the CGI encoding parameter value for the specified encoding"""
        encoding_map = {
            "velthuis": "VH",
            "itrans": "IT",
            "slp1": "SL",
            "devanagari": "DN",
        }
        return encoding_map.get(encoding.lower(), "VH")

    @staticmethod
    def build_morphology_params(
        text: str, encoding: str | None = None, max_solutions: int | None = None, **kwargs
    ) -> dict[str, Any]:
        """Build parameters for morphological analysis (sktreader)"""
        params = {}

        # Text input - encode the text if encoding is specified
        if encoding:
            encoded_text = HeritageParameterBuilder.encode_text(text, encoding)
            params["text"] = encoded_text
            params["t"] = HeritageParameterBuilder.get_cgi_encoding_param(encoding)
        else:
            params["text"] = text

        # Number of solutions
        if max_solutions is not None:
            params["max"] = str(max_solutions)

        # Additional parameters
        params.update(kwargs)

        return params

    @staticmethod
    def build_search_params(
        query: str,
        lexicon: str = "MW",
        max_results: int | None = None,
        encoding: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Build parameters for dictionary search (sktsearch/sktindex)"""
        params = {
            "lex": lexicon,
            "q": query,
        }

        # Encoding parameter (t=VH for Velthuis, etc.)
        if encoding:
            params["t"] = HeritageParameterBuilder.get_cgi_encoding_param(encoding)

        if max_results is not None:
            params["max"] = str(max_results)

        params.update(kwargs)

        return params

    @staticmethod
    def build_lemma_params(word: str, encoding: str | None = None, **kwargs) -> dict[str, Any]:
        """Build parameters for lemmatization (sktlemmatizer)"""
        params = {}

        # Word input - always pass original word for CGI processing
        params["word"] = word

        # Encoding parameter (t=VH for Velthuis, etc.)
        if encoding:
            params["t"] = HeritageParameterBuilder.get_cgi_encoding_param(encoding)

        params.update(kwargs)

        return params

    @staticmethod
    def build_declension_params(
        lemma: str,
        gender: str = "m",
        case: int = 1,
        number: str = "s",
        encoding: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Build parameters for declension generation (sktdeclin)"""
        params = {
            "lemma": lemma,
            "gen": gender,
        }

        # Encoding parameter (t=VH for Velthuis, etc.)
        if encoding:
            params["t"] = HeritageParameterBuilder.get_cgi_encoding_param(encoding)

        params.update(kwargs)

        return params

    @staticmethod
    def build_conjugation_params(
        lemma: str,
        tense: str = "pres",
        person: int = 3,
        number: str = "s",
        encoding: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Build parameters for conjugation generation (sktconjug)"""
        params = {
            "verb": lemma,
            "ten": tense,
            "per": str(person),
            "num": number,
        }

        # Encoding parameter (t=VH for Velthuis, etc.)
        if encoding:
            params["t"] = HeritageParameterBuilder.get_cgi_encoding_param(encoding)

        params.update(kwargs)

        return params
