"""
Heritage Platform Velthuis converter.

Direct port of the utf82VH.js implementation from Heritage.
Reference: http://localhost:48080/skt/utf82VH.js
"""

# Devanagari Unicode range constants
DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F

# Mapping from Unicode code points (as decimal strings) to Velthuis
ROMA_TO_VELTHUIS = {
    "7773": ".rr",  # ṝ (long vocalic r)
    "0257": "aa",  # ā (long a)
    "0299": "ii",  # ī (long i)
    "0363": "uu",  # ū (long u)
    "7771": ".r",  # ṛ (vocalic r)
    "7735": ".l",  # ḷ (vocalic l)
    "7749": "f",  # ṅ (velar n)
    "0241": "~n",  # ñ (palatal n)
    "7789": ".t",  # ṭ (retroflex t)
    "7693": ".d",  # ḍ (retroflex d)
    "7751": ".n",  # ṇ (retroflex n)
    "7747": ".m",  # ṃ (anusvāra)
    "7779": ".s",  # ṣ (retroflex s)
    "0347": "z",  # ś (palatal s)
    "7717": ".h",  # ḥ (visarga)
    "7745": "~~",  # anunasika (candrabindu)
}

# Vowel dictionary (independent vowels)
VOWEL_TO_VELTHUIS = {
    "05": "a",
    "06": "aa",
    "07": "i",
    "08": "ii",
    "09": "u",
    "0a": "uu",
    "0b": ".r",
    "60": ".rr",
    "0c": ".l",
    "0f": "e",
    "10": "ai",
    "13": "o",
    "14": "au",
    "4d": "",  # virama/halant - no vowel
}

# Matra dictionary (vowel marks/diacritics)
MATRA_TO_VELTHUIS = {
    "3e": "aa",
    "3f": "i",
    "40": "ii",
    "41": "u",
    "42": "uu",
    "43": ".r",
    "44": ".rr",
    "62": ".l",
    "47": "e",
    "48": "ai",
    "4b": "o",
    "4c": "au",
}

# Consonant dictionary
CONSONANT_TO_VELTHUIS = {
    "15": "k",
    "16": "kh",
    "17": "g",
    "18": "gh",
    "19": "f",  # ṅ
    "1a": "c",
    "1b": "ch",
    "1c": "j",
    "1d": "jh",
    "1e": "~n",  # ñ
    "1f": ".t",
    "20": ".th",
    "21": ".d",
    "22": ".dh",
    "23": ".n",
    "24": "t",
    "25": "th",
    "26": "d",
    "27": "dh",
    "28": "n",
    "2a": "p",
    "2b": "ph",
    "2c": "b",
    "2d": "bh",
    "2e": "m",
    "2f": "y",
    "30": "r",
    "32": "l",
    "35": "v",
    "36": "z",  # ś
    "37": ".s",  # ṣ
    "38": "s",
    "39": "h",
}

# Special characters
SPECIAL_TO_VELTHUIS = {
    "01": "~~",  # candrabindu/anunasika
    "02": ".m",  # anusvāra
    "03": ".h",  # visarga
    "3d": "'",  # avagraha
    "64": "|",  # danda
    "65": "||",  # double danda
}


def convert_roma_to_velthuis(text: str) -> str:
    """
    Convert IAST/Roman text to Heritage Velthuis encoding.

    Based on Heritage's convertRoma() function from utf82VH.js.
    Maps Unicode characters to Velthuis sequences.
    """
    result = []
    for char in text:
        # Format code point as 4-digit zero-padded string to match Heritage format
        code_point = f"{ord(char):04d}"
        if code_point in ROMA_TO_VELTHUIS:
            result.append(ROMA_TO_VELTHUIS[code_point])
        else:
            result.append(char)

    return "".join(result)


def _normalize_hex_code(hex_str: str) -> str:
    """Pad hex string to 4 characters (e.g., '5' -> '0005', '15' -> '0015')."""
    return hex_str.zfill(4)


def _convert_deva_char(
    check_suffix: str, was_cons: bool, after_virama: bool = False
) -> tuple[str, bool, bool]:
    """
    Convert a single Devanagari character suffix to Velthuis.

    Returns the converted string, whether this character was a consonant,
    and whether this character is a virama.
    """
    # Check vowels first
    if check_suffix in VOWEL_TO_VELTHUIS:
        vowel = VOWEL_TO_VELTHUIS[check_suffix]
        # Virama (halant) is a special case - it suppresses the implicit 'a' vowel
        # but keeps the consonant "open" for a following matra or consonant cluster.
        if check_suffix == "4d":  # Virama
            return "", True, True
        result = "a" + vowel if was_cons else vowel
        return result, False, False

    # Check matras (vowel marks)
    # Matras modify the vowel of the preceding consonant, so they should NOT
    # trigger the implicit 'a' vowel that would normally follow a consonant.
    if check_suffix in MATRA_TO_VELTHUIS:
        matra = MATRA_TO_VELTHUIS[check_suffix]
        # Matras replace the implicit 'a', so don't prepend 'a' even if was_cons
        return matra, False, False

    # Check special characters
    if check_suffix in SPECIAL_TO_VELTHUIS:
        spec = SPECIAL_TO_VELTHUIS[check_suffix]
        result = "a" + spec if was_cons else spec
        return result, False, False

    # Check consonants
    if check_suffix in CONSONANT_TO_VELTHUIS:
        cons = CONSONANT_TO_VELTHUIS[check_suffix]
        # If this consonant follows a virama, don't add implicit 'a'
        # as it's part of a consonant cluster
        result = cons if after_virama else ("a" + cons if was_cons else cons)
        return result, True, False

    # Unknown character
    result = ("" if after_virama else ("a" if was_cons else "")) + check_suffix
    return result, True, False


def _process_deva_character(
    char: str, was_cons: bool, after_virama: bool = False
) -> tuple[str, bool, bool]:
    """
    Process a single character, handling Devanagari and non-Devanagari.

    Returns the processed string, the new was_cons state, and whether this char was a virama.
    """
    char_code = ord(char)

    # Check if it's in Devanagari range
    if DEVANAGARI_START <= char_code <= DEVANAGARI_END:
        hex_code = _normalize_hex_code(hex(char_code)[2:])
        check_suffix = hex_code[2:]  # Last 2 hex digits
        return _convert_deva_char(check_suffix, was_cons, after_virama)

    # Non-Devanagari character
    result = char if after_virama else ("a" + char if was_cons else char)
    return result, True, False


def convert_deva_to_velthuis(text: str) -> str:
    """
    Convert Devanagari text to Heritage Velthuis encoding.

    Based on Heritage's convertDeva() function from utf82VH.js.
    """
    output = []
    was_cons = False
    after_virama = False

    for char in text:
        converted, was_cons, is_virama = _process_deva_character(char, was_cons, after_virama)
        output.append(converted)
        after_virama = is_virama

    # Add final 'a' if last char was a consonant (and not after virama)
    if was_cons and not after_virama:
        output.append("a")

    return "".join(output)


def _contains_devanagari(text: str) -> bool:
    """Check if text contains any Devanagari characters."""
    return any(DEVANAGARI_START <= ord(c) <= DEVANAGARI_END for c in text)


def to_heritage_velthuis(text: str) -> str:
    """
    Convert text to Heritage Platform Velthuis encoding.

    Auto-detects whether input is Devanagari or Roman/IAST and converts appropriately.
    """
    if _contains_devanagari(text):
        return convert_deva_to_velthuis(text)
    return convert_roma_to_velthuis(text)
