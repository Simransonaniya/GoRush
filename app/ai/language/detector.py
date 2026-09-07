import re

from app.common.enums.chat import Language

# Script Regexes for Indian Regional Languages
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
GUJARATI_RE = re.compile(r"[\u0A80-\u0AFF]")
BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
KANNADA_RE = re.compile(r"[\u0C80-\u0CFF]")
MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")
PUNJABI_RE = re.compile(r"[\u0A00-\u0A7F]")
ODIA_RE = re.compile(r"[\u0B00-\u0B7F]")
URDU_RE = re.compile(r"[\u0600-\u06FF]")

# Assamese unique characters in Bengali script
ASSAMESE_CHAR_RE = re.compile(r"[\u09F0\u09F1]")  # ৰ, ৱ

# Language-specific marker sets
MARATHI_MARKERS = {
    "आहे", "नाही", "मला", "तुमचा", "गाडी", "चालक", "कधी", "कुठे", "झाले",
    "नमस्कार", "का", "काय", "कसे", "आलो", "पाहिजे", "करायचे", "माझा", "माझी",
    "माझे", "होतो", "होती", "आहोत", "करा", "पहा", "ड्राइव्हर"
}

ASSAMESE_MARKERS = {
    "আপুনি", "ক'ত", "নহয়", "মোৰ", "গাড়ী", "ড্রাইভাৰ", "কেতিয়া", "ধন্যবাদ",
    "হয়", "কি", "কেনেকৈ", "কৰক"
}

HINGLISH_MARKERS = {
    "bhai", "kahan", "kaha", "nahi", "nahin", "hai", "raha", "rahi", "rahe",
    "kyun", "kyu", "kab", "abhi", "tak", "gaya", "gayi", "kar", "karo",
    "kro", "mera", "meri", "mujhe", "aap", "tum", "bata",
    "batao", "kitna", "kitni", "paisa", "paise", "haan", "acha", "theek",
    "yaar", "zyada", "thoda",
}


class LanguageDetector:
    """Detects languages across Launch (EN, HI, Hinglish, Mixed) and
    Phase 2 Regional Languages (Marathi, Gujarati, Bengali, Tamil, Telugu,
    Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu)."""

    def detect(self, text: str) -> Language:
        if not text or not text.strip():
            return Language.UNKNOWN

        # Character counts per script
        counts = {
            "devanagari": len(DEVANAGARI_RE.findall(text)),
            "gujarati": len(GUJARATI_RE.findall(text)),
            "bengali": len(BENGALI_RE.findall(text)),
            "tamil": len(TAMIL_RE.findall(text)),
            "telugu": len(TELUGU_RE.findall(text)),
            "kannada": len(KANNADA_RE.findall(text)),
            "malayalam": len(MALAYALAM_RE.findall(text)),
            "punjabi": len(PUNJABI_RE.findall(text)),
            "odia": len(ODIA_RE.findall(text)),
            "urdu": len(URDU_RE.findall(text)),
        }

        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        hinglish_hits = sum(1 for t in tokens if t in HINGLISH_MARKERS)
        latin_tokens = len(tokens)

        # Count scripts with significant character presence (>= 2 chars)
        active_scripts = [name for name, cnt in counts.items() if cnt >= 2]
        if latin_tokens >= 2 and hinglish_hits == 0:
            active_scripts.append("latin")

        if len(active_scripts) >= 2 and hinglish_hits == 0:
            return Language.MIXED

        # Find dominant script
        dominant_script = max(counts, key=counts.get) if counts else None
        dominant_count = counts[dominant_script] if dominant_script else 0

        if dominant_count > 0:
            if dominant_script == "gujarati":
                return Language.GUJARATI
            if dominant_script == "tamil":
                return Language.TAMIL
            if dominant_script == "telugu":
                return Language.TELUGU
            if dominant_script == "kannada":
                return Language.KANNADA
            if dominant_script == "malayalam":
                return Language.MALAYALAM
            if dominant_script == "punjabi":
                return Language.PUNJABI
            if dominant_script == "odia":
                return Language.ODIA
            if dominant_script == "urdu":
                return Language.URDU

            if dominant_script == "bengali":
                if bool(ASSAMESE_CHAR_RE.search(text)):
                    return Language.ASSAMESE
                words = text.split()
                if any(w in ASSAMESE_MARKERS for w in words):
                    return Language.ASSAMESE
                return Language.BENGALI

            if dominant_script == "devanagari":
                if "\u0933" in text or any(w in MARATHI_MARKERS for w in text.split()):
                    return Language.MARATHI
                if latin_tokens > 0:
                    return Language.HINGLISH
                if hinglish_hits == 0:
                    return Language.HINDI

        if hinglish_hits > 0:
            return Language.HINGLISH
        if latin_tokens > 0:
            return Language.ENGLISH

        return Language.UNKNOWN



language_detector = LanguageDetector()