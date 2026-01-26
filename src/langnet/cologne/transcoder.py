from indic_transliteration.detect import detect
from indic_transliteration.sanscript import transliterate, SLP1


class CdslTranscoder:
    @staticmethod
    def normalize_key(key: str) -> str:
        return key.lower().strip()

    @staticmethod
    def to_slp1(text: str) -> str:
        src = detect(text)
        return transliterate(text, src, SLP1).lower()

    @staticmethod
    def normalize_for_lookup(key: str) -> str:
        return CdslTranscoder.to_slp1(key).lower()
