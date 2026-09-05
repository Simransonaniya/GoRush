import re

from app.common.enums.chat import Language

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# Small, extensible seed list of common Hinglish/Roman-Hindi tokens.
# In production this should be backed by a proper langid/fastText model;
# this heuristic exists as a fast, dependency-free first pass and fallback.
HINGLISH_MARKERS = {
    "bhai", "kahan", "kaha", "nahi", "nahin", "hai", "raha", "rahi", "rahe",
    "kyun", "kyu", "kab", "abhi", "tak", "aa", "gaya", "gayi", "kar", "karo",
    "kro", "mera", "meri", "mujhe", "aap", "tum", "please", "plz", "bata",
    "batao", "kitna", "kitni", "paisa", "paise", "driver", "ride",
}


class LanguageDetector:
    def detect(self, text: str) -> Language:
        if not text or not text.strip():
            return Language.UNKNOWN

        has_devanagari = bool(DEVANAGARI_RE.search(text))
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        hinglish_hits = sum(1 for t in tokens if t in HINGLISH_MARKERS)
        latin_tokens = len(tokens)

        if has_devanagari and hinglish_hits == 0 and latin_tokens == 0:
            return Language.HINDI
        if has_devanagari and latin_tokens > 0:
            return Language.HINGLISH
        if not has_devanagari and hinglish_hits > 0:
            return Language.HINGLISH
        if not has_devanagari and latin_tokens > 0:
            return Language.ENGLISH
        return Language.UNKNOWN


language_detector = LanguageDetector()
