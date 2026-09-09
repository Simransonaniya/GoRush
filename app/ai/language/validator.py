"""
Language Validation Step.
Validates whether the LLM generated response matches the expected_language code.
"""

import re
from app.ai.language.detector import (
    DEVANAGARI_RE,
    GUJARATI_RE,
    PUNJABI_RE,
    RAJASTHANI_DEVANAGARI_MARKERS,
    RAJASTHANI_ROMAN_MARKERS,
)
from app.common.enums.chat import Language


def validate_response_language(response: str, expected_language: str | Language) -> bool:
    """Validate that the generated response text matches expected_language."""
    if not response or not response.strip():
        return True

    lang_enum = Language.normalize(expected_language) if isinstance(expected_language, str) else expected_language
    code = lang_enum.value

    # Allow UNKNOWN or MIXED without strict rejection
    if lang_enum in (Language.UNKNOWN, Language.MIXED):
        return True

    resp_text = response.strip()

    if code == "en":
        # English response should not be dominated by non-Latin scripts
        dev_cnt = len(DEVANAGARI_RE.findall(resp_text))
        guj_cnt = len(GUJARATI_RE.findall(resp_text))
        pun_cnt = len(PUNJABI_RE.findall(resp_text))
        if dev_cnt > 5 or guj_cnt > 5 or pun_cnt > 5:
            return False
        return True

    if code == "hi":
        # Hindi response should have Devanagari script and not Rajasthani specific markers
        has_dev = bool(DEVANAGARI_RE.search(resp_text))
        has_raj_word = any(w in resp_text for w in ["कोनी", "कर्यो", "थारो", "म्हारो"])
        if not has_dev or has_raj_word:
            return False
        return True

    if code == "raj":
        # Rajasthani response can be Devanagari or Romanized Rajasthani
        has_dev = bool(DEVANAGARI_RE.search(resp_text))
        has_raj_word = any(w in resp_text for w in RAJASTHANI_DEVANAGARI_MARKERS) or any(
            w in resp_text.lower() for w in RAJASTHANI_ROMAN_MARKERS
        )
        if not (has_dev or has_raj_word):
            return False
        return True

    if code == "pa":
        # Punjabi response should have Gurmukhi or Roman Punjabi markers
        has_gur = bool(PUNJABI_RE.search(resp_text))
        has_pun_word = any(w in resp_text.lower() for w in ["tusi", "dasso", "veere", "paji", "kiti", "kitta", "ਭੁਗਤਾਨ", "ਕੀਤਾ"])
        if not (has_gur or has_pun_word):
            return False
        return True

    if code == "gu":
        # Gujarati response should have Gujarati script or Roman Gujarati markers
        has_guj = bool(GUJARATI_RE.search(resp_text))
        has_guj_word = any(w in resp_text.lower() for w in ["nathi", "tamare", "chhe", "kari", "ચુકવણી"])
        if not (has_guj or has_guj_word):
            return False
        return True

    if code in ("hi-en", "hinglish"):
        # Hinglish response should be primarily Roman script
        dev_cnt = len(DEVANAGARI_RE.findall(resp_text))
        if dev_cnt > 10:
            return False
        return True

    return True
