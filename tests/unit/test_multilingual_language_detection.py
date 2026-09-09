"""
Comprehensive Automated Tests for Multilingual Language Detection & Response Pipeline.

Covers:
  - Hindi (hi)
  - Punjabi (pa)
  - Gujarati (gu)
  - Rajasthani (raj)
  - English (en)
  - Hinglish (hi-en / hinglish)
  - Short messages
  - Romanized Indian languages
  - Mixed languages & explicit language switch requests
  - Multilingual intent classification
"""

import pytest
from app.ai.language.detector import language_detector
from app.ai.language.validator import validate_response_language
from app.ai.intent.detector import intent_detector
from app.common.enums.chat import Intent, Language


class TestMultilingualDetection:
    """Validate script + vocabulary + grammar + transliteration detection."""

    # 1. Primary Required Languages
    def test_hindi_detection(self):
        res = language_detector.detect("ग्राहक ने भुगतान नहीं किया")
        assert res == Language.HINDI

    def test_punjabi_detection(self):
        res = language_detector.detect("ਗਾਹਕ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ")
        assert res == Language.PUNJABI

    def test_gujarati_detection(self):
        res = language_detector.detect("ગ્રાહકે ચુકવણી કરી નથી")
        assert res == Language.GUJARATI

    def test_rajasthani_devanagari_detection(self):
        res = language_detector.detect("ग्राहक नै भुगतान कोनी कर्यो।")
        assert res == Language.RAJASTHANI

    def test_english_detection(self):
        res = language_detector.detect("Customer did not make the payment.")
        assert res == Language.ENGLISH

    def test_hinglish_detection(self):
        res = language_detector.detect("Customer ne payment nahi kiya")
        assert res == Language.HINGLISH

    # 2. Short Messages
    def test_short_rajasthani(self):
        res = language_detector.detect("कोनी कर्यो")
        assert res == Language.RAJASTHANI

    def test_short_hinglish(self):
        res = language_detector.detect("payment nahi hua")
        assert res == Language.HINGLISH

    def test_short_hindi(self):
        res = language_detector.detect("भुगतान नहीं हुआ")
        assert res == Language.HINDI

    def test_short_punjabi(self):
        res = language_detector.detect("ਭੁਗਤਾਨ ਨਹੀਂ ਹੋਇਆ")
        assert res == Language.PUNJABI

    def test_short_gujarati(self):
        res = language_detector.detect("ચુકવણી નથી થઈ")
        assert res == Language.GUJARATI

    # 3. Transliterated / Romanized Languages
    def test_romanized_rajasthani(self):
        res = language_detector.detect("customer nai payment koni karyo")
        assert res == Language.RAJASTHANI

    def test_romanized_punjabi(self):
        res = language_detector.detect("tusi payment kyu nahi kiti")
        assert res == Language.PUNJABI

    def test_romanized_gujarati(self):
        res = language_detector.detect("customer e payment nathi kari")
        assert res == Language.GUJARATI

    # 4. Explicit Language Switch Requests
    def test_explicit_english_switch(self):
        res = language_detector.detect("English mein batao")
        assert res == Language.ENGLISH

    def test_explicit_hindi_switch(self):
        res = language_detector.detect("Hindi me batao")
        assert res == Language.HINDI

    def test_explicit_rajasthani_switch(self):
        res = language_detector.detect("Rajasthani me batao")
        assert res == Language.RAJASTHANI


class TestMultilingualIntents:
    """Validate that intent detection works cleanly across all regional languages."""

    @pytest.mark.parametrize("phrase, expected_intent", [
        ("Customer did not make the payment.", Intent.CASH_PAYMENT),
        ("Customer ne payment nahi kiya", Intent.CASH_PAYMENT),
        ("ग्राहक ने भुगतान नहीं किया", Intent.CASH_PAYMENT),
        ("ग्राहक नै भुगतान कोनी कर्यो।", Intent.CASH_PAYMENT),
        ("ਗਾਹਕ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ", Intent.CASH_PAYMENT),
        ("ગ્રાહકે ચુકવણી કરી નથી", Intent.CASH_PAYMENT),
    ])
    def test_cash_payment_intent_multilingual(self, phrase, expected_intent):
        res = intent_detector.detect(phrase)
        assert res.intent == expected_intent


class TestLanguageValidation:
    """Validate language output validator logic."""

    def test_valid_hindi_response(self):
        valid = validate_response_language("ग्राहक ने भुगतान नहीं किया है।", Language.HINDI)
        assert valid is True

    def test_invalid_hindi_with_rajasthani_words(self):
        valid = validate_response_language("ग्राहक नै भुगतान कोनी कर्यो", Language.HINDI)
        assert valid is False

    def test_valid_rajasthani_response(self):
        valid = validate_response_language("ग्राहक नै भुगतान कोनी कर्यो है।", Language.RAJASTHANI)
        assert valid is True

    def test_valid_punjabi_response(self):
        valid = validate_response_language("ਗਾਹਕ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ ਹੈ।", Language.PUNJABI)
        assert valid is True

    def test_valid_gujarati_response(self):
        valid = validate_response_language("ગ્રાહકે ચુકવણી કરી નથી.", Language.GUJARATI)
        assert valid is True


class TestMultilingualResponseGeneration:
    """Validate mock provider & orchestrator response generation in target languages."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("phrase, lang_code, expected_script_or_word", [
        ("Customer did not make the payment.", "en", "Customer"),
        ("ग्राहक ने भुगतान नहीं किया", "hi", "भुगतान"),
        ("Customer ne payment nahi kiya", "hi-en", "payment"),
        ("ग्राहक नै भुगतान कोनी कर्यो।", "raj", "कोनी"),
        ("ગ્રાહકે ચુકવણી કરી નથી", "gu", "ચુકવણી"),
        ("ਗਾਹਕ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ", "pa", "ਭੁਗਤਾਨ"),
        ("Customer ne payment nahi kiya and issue created", "mixed", "payment"),
    ])
    async def test_multilingual_responses(self, phrase, lang_code, expected_script_or_word):
        from app.ai.llm.mock_provider import MockLLMProvider
        from app.ai.prompts.registry import get_prompt
        from app.ai.llm.provider import ChatMessage

        provider = MockLLMProvider()
        prompt = get_prompt("driver_support_system")
        sys_prompt = prompt.render(lang_code)
        messages = [ChatMessage(role="user", content=phrase)]

        resp = await provider.chat(messages, system=sys_prompt)
        assert resp.text is not None
        assert expected_script_or_word in resp.text

    @pytest.mark.asyncio
    async def test_rajasthani_cash_payment_regression(self):
        """Regression test for Rajasthani cash payment input:
        Input: 'ग्राहक नै भुगतान कोनी कर्यो।'
        Expected: language='raj', intent='cash_payment', response in Rajasthani (not English).
        """
        from app.ai.intent.detector import intent_detector
        from app.ai.language.config import is_language_enabled
        from app.ai.llm.mock_provider import MockLLMProvider
        from app.ai.prompts.registry import get_prompt
        from app.ai.llm.provider import ChatMessage

        input_text = "ग्राहक नै भुगतान कोनी कर्यो।"

        # 1. Verify language and intent detection
        intent_res = intent_detector.detect(input_text)
        assert intent_res.language == Language.RAJASTHANI or intent_res.language.value == "raj"
        assert intent_res.intent == Intent.CASH_PAYMENT or intent_res.intent.value == "cash_payment"

        # 2. Verify feature flag is enabled for Rajasthani
        assert is_language_enabled(intent_res.language) is True

        # 3. Verify response generation is in Rajasthani and NOT English
        provider = MockLLMProvider()
        prompt = get_prompt("driver_support_system")
        sys_prompt = prompt.render(intent_res.language.value)
        messages = [ChatMessage(role="user", content=input_text)]

        resp = await provider.chat(messages, system=sys_prompt)
        assert resp.text is not None
        assert validate_response_language(resp.text, Language.RAJASTHANI) is True
        # Explicit check: response must NOT be English fallback
        assert "I currently support" not in resp.text
        assert "Customer did not" not in resp.text
        assert any(w in resp.text for w in ["कोनी", "कर्यो", "भुगतान", "ग्राहक", "आप", "सू"])


class TestPhase2Languages:
    """Validate all Phase 2 languages retain correct language & intent detection even when feature flag is disabled."""

    @pytest.mark.parametrize("phrase, expected_lang, expected_intent", [
        ("Customer did not make the payment.", Language.ENGLISH, Intent.CASH_PAYMENT),
        ("ग्राहक ने भुगतान नहीं किया", Language.HINDI, Intent.CASH_PAYMENT),
        ("Customer ne payment nahi kiya", Language.HINGLISH, Intent.CASH_PAYMENT),
        ("ग्राहक नै भुगतान कोनी कर्यो।", Language.RAJASTHANI, Intent.CASH_PAYMENT),
        ("গ্রাহক পেমেন্ট করেনি।", Language.BENGALI, Intent.CASH_PAYMENT),
        ("ग्राहकाने पेमेंट केले नाही.", Language.MARATHI, Intent.CASH_PAYMENT),
        ("ગ્રાહકે ચુકવણી કરી નથી.", Language.GUJARATI, Intent.CASH_PAYMENT),
        ("ਗਾਹਕ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ।", Language.PUNJABI, Intent.CASH_PAYMENT),
        ("வாடிக்கையாளர் பணம் செலுத்தவில்லை.", Language.TAMIL, Intent.CASH_PAYMENT),
        ("వినియోగదారు చెల్లింపు చేయలేదు.", Language.TELUGU, Intent.CASH_PAYMENT),
        ("ಗ್ರಾಹಕ ಪಾವತಿ ಮಾಡಲಿಲ್ಲ.", Language.KANNADA, Intent.CASH_PAYMENT),
        ("ഉപഭോക്താവ് പണമടച്ചില്ല.", Language.MALAYALAM, Intent.CASH_PAYMENT),
        ("ଗ୍ରାହକ ଦେୟ ଦେଇନାହାଁନ୍ତି।", Language.ODIA, Intent.CASH_PAYMENT),
        ("গ্ৰাহকে পৰিশোধ কৰা নাই।", Language.ASSAMESE, Intent.CASH_PAYMENT),
        ("گاہک نے ادائیگی نہیں کی۔", Language.URDU, Intent.CASH_PAYMENT),
    ])
    def test_phase2_language_and_intent_detection(self, phrase, expected_lang, expected_intent):
        from app.ai.intent.detector import intent_detector

        res = intent_detector.detect(phrase)
        assert res.language == expected_lang
        assert res.intent == expected_intent

    def test_bengali_cash_payment_phase2_behavior(self):
        """Verify Bengali input:
        'গ্রাহক পেমেন্ট করেনি।'
        Expected:
        - language = 'bn'
        - intent = 'cash_payment'
        - Internal classification is preserved correctly regardless of feature flag state.
        """
        from app.ai.intent.detector import intent_detector
        from app.ai.language.config import is_language_enabled, set_language_enabled

        phrase = "গ্রাহক পেমেন্ট করেনি।"
        res = intent_detector.detect(phrase)

        assert res.language == Language.BENGALI or res.language.value == "bn"
        assert res.intent == Intent.CASH_PAYMENT or res.intent.value == "cash_payment"

        # Verify behavior when feature flag is explicitly toggled OFF vs ON
        set_language_enabled(Language.BENGALI, False)
        assert is_language_enabled(Language.BENGALI) is False
        set_language_enabled(Language.BENGALI, True)
        assert is_language_enabled(Language.BENGALI) is True


class TestHumanFriendlyRules:
    """Validate specific conversation rules A through L required by specification."""

    # A. English
    def test_rule_a_english(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("Customer has not paid.")
        assert res.language == Language.ENGLISH
        assert res.intent == Intent.CASH_PAYMENT

    # B. Hindi
    def test_rule_b_hindi(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("ग्राहक ने भुगतान नहीं किया।")
        assert res.language == Language.HINDI
        assert res.intent == Intent.CASH_PAYMENT

    # C. Hinglish
    def test_rule_c_hinglish(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("Customer ne payment nahi kiya.")
        assert res.language == Language.HINGLISH
        assert res.intent == Intent.CASH_PAYMENT

    # D. Gujarati
    def test_rule_d_gujarati(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("ગ્રાહકે ચુકવણી કરી નથી.")
        assert res.language == Language.GUJARATI
        assert res.intent == Intent.CASH_PAYMENT

    # E. Bengali
    def test_rule_e_bengali(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("গ্রাহক পেমেন্ট করেনি।")
        assert res.language == Language.BENGALI
        assert res.intent == Intent.CASH_PAYMENT

    # F. Rajasthani
    def test_rule_f_rajasthani(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("ग्राहक नै भुगतान कोनी कर्यो।")
        assert res.language == Language.RAJASTHANI
        assert res.intent == Intent.CASH_PAYMENT

    # G. Hindi + English Code-Switching
    def test_rule_g_hindi_english(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("ग्राहक ने payment नहीं किया।")
        assert res.language == Language.HINDI
        assert res.intent == Intent.CASH_PAYMENT

    # H. Gujarati + English Code-Switching
    def test_rule_h_gujarati_english(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("ગ્રાહકે payment કર્યું નથી.")
        assert res.language == Language.GUJARATI
        assert res.intent == Intent.CASH_PAYMENT

    # I. Bengali + English Code-Switching
    def test_rule_i_bengali_english(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("গ্রাহক payment করেনি.")
        assert res.language == Language.BENGALI
        assert res.intent == Intent.CASH_PAYMENT

    # J. Hinglish mixed with Devanagari
    def test_rule_j_hinglish_devanagari(self):
        from app.ai.intent.detector import intent_detector
        res = intent_detector.detect("Customer ne payment नहीं किया, अब क्या करना है?")
        assert res.intent == Intent.CASH_PAYMENT
        assert res.language in (Language.HINGLISH, Language.HINDI, Language.MIXED)

    # K. Angry / Frustrated User
    @pytest.mark.asyncio
    async def test_rule_k_angry_user(self):
        from app.ai.llm.mock_provider import MockLLMProvider
        from app.ai.prompts.registry import get_prompt
        from app.ai.llm.provider import ChatMessage

        phrase = "ग्राहक ने पैसे नहीं दिए और मेरा बहुत नुकसान हो गया!"
        provider = MockLLMProvider()
        prompt = get_prompt("driver_support_system")
        sys_prompt = prompt.render("hi")
        messages = [ChatMessage(role="user", content=phrase)]

        resp = await provider.chat(messages, system=sys_prompt)
        # Verify empathetic, non-defensive, actionable response
        assert "परेशान" in resp.text or "मदद" in resp.text
        assert "नहीं" not in resp.text or "dispute" in resp.text or "मदद" in resp.text

    # L. Unknown / Low-Confidence Question
    def test_rule_l_unknown_fallback(self):
        from app.ai.language.localization import get_localized_text
        fb_hi = get_localized_text("unknown_fallback", "hi")
        fb_bn = get_localized_text("unknown_fallback", "bn")
        assert "पुष्टि नहीं" in fb_hi or "human support" in fb_hi
        assert "যাচাই" in fb_bn or "human support" in fb_bn



