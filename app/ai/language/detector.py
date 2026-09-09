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

# ---------------------------------------------------------------------------
# Vocabulary & Grammar Markers
# ---------------------------------------------------------------------------

EXPLICIT_LANG_PATTERNS = [
    (Language.ENGLISH, re.compile(r"\b(in english|english me|english mein|tell me in english|speak in english|switch to english)\b", re.I)),
    (Language.HINDI, re.compile(r"\b(in hindi|hindi me|hindi mein|hindi me batao|hindi mein batao)\b", re.I)),
    (Language.PUNJABI, re.compile(r"\b(in punjabi|punjabi vich|punjabi me|punjabi mein|punjabi vich dasso|punjabi me batao)\b", re.I)),
    (Language.GUJARATI, re.compile(r"\b(in gujarati|gujarati ma|gujarati me|gujarati ma batao|gujarati me batao)\b", re.I)),
    (Language.RAJASTHANI, re.compile(r"\b(in rajasthani|rajasthani me|rajasthani mein|rajasthani me batao)\b", re.I)),
    (Language.MARATHI, re.compile(r"\b(in marathi|marathi me|marathi mein|marathi me batao)\b", re.I)),
]

RAJASTHANI_DEVANAGARI_MARKERS = {
    "कोनी", "कोनी।", "कोनी,", "कोनी?", "कोन", "कोनि", "कौनी",
    "कर्यो", "कर्यो।", "कर्यो,", "कर्यो?", "करियो",
    "नै", "ने।",
    "थारो", "थारी", "थारा", "थारे",
    "म्हारे", "म्हारो", "म्हारी", "म्हानी",
    "काईं", "काई", "कठै", "आयो", "गयो", "पिया", "कानी", "क्युं", "खम्मा"
}

RAJASTHANI_ROMAN_MARKERS = {
    "koni", "karyo", "koni.", "karyo.", "tharo", "thari", "thare",
    "mhare", "mharo", "mhari", "kain", "kathe", "piya"
}

MARATHI_MARKERS = {
    "आहे", "नाही", "मला", "तुमचा", "गाडी", "चालक", "कधी", "कुठे", "झाले",
    "नमस्कार", "का", "काय", "कसे", "आलो", "पाहिजे", "करायचे", "माझा", "माझी",
    "माझे", "होतो", "होती", "आहोत", "करा", "पहा", "ड्राइव्हर"
}

ASSAMESE_MARKERS = {
    "আপুনি", "ক'ত", "নহয়", "মোৰ", "গাড়ী", "ড্রাইভাৰ", "কেতিয়া", "ধন্যবাদ",
    "হয়", "কি", "কেনেকৈ", "কৰক"
}

PUNJABI_ROMAN_MARKERS = {
    "tusi", "tussi", "kiti", "kitta", "veere", "paji", "dasso", "hoya",
    "bhugtan", "kiti.", "kitta.", "dasso."
}

GUJARATI_ROMAN_MARKERS = {
    "nathi", "kari", "karyu", "tamare", "aaviyo", "thay", "nathi.", "kari.",
    "chukavani", "chukavani."
}

HINGLISH_MARKERS = {
    "bhai", "kahan", "kaha", "nahi", "nahin", "hai", "raha", "rahi", "rahe",
    "kyun", "kyu", "kab", "abhi", "tak", "gaya", "gayi", "kar", "karo",
    "kro", "mera", "meri", "mujhe", "aap", "tum", "bata", "batao",
    "kitna", "kitni", "paisa", "paise", "haan", "acha", "theek", "yaar",
    "zyada", "thoda", "hua", "karna", "karein", "de", "kiya", "chahiye", "ne"
}


class LanguageDetector:
    """Multilingual Language Detector.
    Evaluates script, vocabulary, grammar, sentence structure, transliteration,
    code-switching, and explicit user requests to accurately detect:
      - en (English)
      - hi (Hindi)
      - hi-en (Hinglish)
      - mixed (Mixed language)
      - pa, gu, raj, mr, ta, te, kn, ml, bn, or, as, ur
    """

    def detect(self, text: str) -> Language:
        if not text or not text.strip():
            return Language.UNKNOWN

        clean_text = text.strip()

        # 1. Highest Priority: Explicit language switch requests
        for lang_enum, pattern in EXPLICIT_LANG_PATTERNS:
            if pattern.search(clean_text):
                return lang_enum

        # 2. Extract tokens & script character counts
        dev_cnt = len(DEVANAGARI_RE.findall(clean_text))
        guj_cnt = len(GUJARATI_RE.findall(clean_text))
        bng_cnt = len(BENGALI_RE.findall(clean_text))
        tam_cnt = len(TAMIL_RE.findall(clean_text))
        tel_cnt = len(TELUGU_RE.findall(clean_text))
        kan_cnt = len(KANNADA_RE.findall(clean_text))
        mal_cnt = len(MALAYALAM_RE.findall(clean_text))
        pun_cnt = len(PUNJABI_RE.findall(clean_text))
        odi_cnt = len(ODIA_RE.findall(clean_text))
        urd_cnt = len(URDU_RE.findall(clean_text))

        words_raw = clean_text.split()
        words_lower = [re.sub(r"[^\w]", "", w.lower()) for w in words_raw if w]

        # 3. Direct Script Matches (Non-Devanagari Indian Scripts)
        if pun_cnt >= 2 or any(c in clean_text for c in "ਗਾਹਕਕੀਤਾਨਹੀਂਹੋਇਆਭੁਗਤਾਨ"):
            return Language.PUNJABI

        if guj_cnt >= 2 or any(c in clean_text for c in "ગ્રાહકેચુકવણીનથીથઈકરી"):
            return Language.GUJARATI

        if tam_cnt >= 2:
            return Language.TAMIL

        if tel_cnt >= 2:
            return Language.TELUGU

        if kan_cnt >= 2:
            return Language.KANNADA

        if mal_cnt >= 2:
            return Language.MALAYALAM

        if odi_cnt >= 2:
            return Language.ODIA

        if urd_cnt >= 2:
            return Language.URDU

        if bng_cnt >= 2:
            if bool(ASSAMESE_CHAR_RE.search(clean_text)) or any(w in ASSAMESE_MARKERS for w in words_raw):
                return Language.ASSAMESE
            return Language.BENGALI

        # 4. Devanagari Script Evaluation (Hindi vs Rajasthani vs Marathi vs Code-Switching)
        if dev_cnt >= 2:
            # Check Rajasthani markers (must not be blindly classified as Hindi!)
            if any(w in RAJASTHANI_DEVANAGARI_MARKERS for w in words_raw) or any(w.lower() in RAJASTHANI_DEVANAGARI_MARKERS for w in words_raw):
                return Language.RAJASTHANI
            if any(marker in clean_text for marker in ["कोनी", "कर्यो", "नै", "थारो", "म्हारो", "कठै"]):
                return Language.RAJASTHANI

            # Check Marathi markers
            if "\u0933" in clean_text or any(marker in clean_text for marker in ["केले", "नाही", "आहे", "मला", "तुमचा", "झाले", "झालं", "ग्राहकाने", "माझा", "माझी"]):
                return Language.MARATHI

            # Check for sentence-level or multi-script code switching
            latin_words = [w for w in words_lower if re.match(r"^[a-z]+$", w)]
            if len(latin_words) >= 2:
                # If distinct English words or sentence present alongside Devanagari
                english_words = {"where", "is", "my", "driver", "customer", "payment", "did", "not", "please"}
                if any(w in english_words for w in latin_words):
                    return Language.MIXED
                return Language.HINGLISH

            return Language.HINDI

        # 5. Roman Script / Transliterated Indian Language Evaluation
        latin_tokens = re.findall(r"[a-zA-Z']+", clean_text.lower())
        if latin_tokens:
            # Check Transliterated Rajasthani
            if any(w in RAJASTHANI_ROMAN_MARKERS for w in latin_tokens) or ("koni" in clean_text.lower() or "karyo" in clean_text.lower()):
                return Language.RAJASTHANI

            # Check Transliterated Punjabi
            if any(w in PUNJABI_ROMAN_MARKERS for w in latin_tokens) or ("tusi" in clean_text.lower() or "kiti" in clean_text.lower()):
                return Language.PUNJABI

            # Check Transliterated Gujarati
            if any(w in GUJARATI_ROMAN_MARKERS for w in latin_tokens) or ("nathi" in clean_text.lower() and "kari" in clean_text.lower()):
                return Language.GUJARATI

            # Check Hinglish / Code-Switching
            hinglish_hits = sum(1 for w in latin_tokens if w in HINGLISH_MARKERS)
            english_words = {"customer", "did", "not", "make", "the", "payment", "status", "ride", "driver", "location", "issue", "help", "cancel", "refund", "receipt", "where", "when", "why"}
            has_english_structure = len(latin_tokens) >= 3 and any(w in english_words for w in latin_tokens)

            if hinglish_hits > 0:
                return Language.HINGLISH

            if has_english_structure and hinglish_hits == 0:
                return Language.ENGLISH

            if len(latin_tokens) == 1 and latin_tokens[0] in {"koni", "karyo"}:
                return Language.RAJASTHANI

            return Language.ENGLISH

        # Short fallback checks
        if "कोनी" in clean_text or "कर्यो" in clean_text:
            return Language.RAJASTHANI

        return Language.UNKNOWN


language_detector = LanguageDetector()