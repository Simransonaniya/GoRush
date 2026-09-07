from app.ai.language.detector import language_detector
from app.common.enums.chat import Language


def test_language_detection_all_15_languages():
    # 1. English
    assert language_detector.detect("Where is my driver?") == Language.ENGLISH

    # 2. Hindi
    assert language_detector.detect("मेरा ड्राइवर कहाँ है?") == Language.HINDI

    # 3. Hinglish
    assert language_detector.detect("bhai driver nahi aa raha") == Language.HINGLISH

    # 4. Marathi
    assert language_detector.detect("माझा चालक कुठे आहे?") == Language.MARATHI

    # 5. Gujarati
    assert language_detector.detect("મારો ડ્રાઇવર ક્યાં છે?") == Language.GUJARATI

    # 6. Bengali
    assert language_detector.detect("আমার ড্রাইভার কোথায়?") == Language.BENGALI

    # 7. Tamil
    assert language_detector.detect("என் டிரைவர் எங்கே?") == Language.TAMIL

    # 8. Telugu
    assert language_detector.detect("నా డ్రൈవర్ ఎక్కడ ఉన్నాడు?") == Language.TELUGU

    # 9. Kannada
    assert language_detector.detect("ನನ್ನ ಚಾಲಕ ಎಲ್ಲಿದ್ದಾನೆ?") == Language.KANNADA

    # 10. Malayalam
    assert language_detector.detect("എന്റെ ഡ്രൈവർ എവിടെ?") == Language.MALAYALAM

    # 11. Punjabi
    assert language_detector.detect("ਮੇਰਾ ਡਰਾਈਵਰ ਕਿੱਥੇ ਹੈ?") == Language.PUNJABI

    # 12. Odia
    assert language_detector.detect("ମୋର ଡ୍ରାଇଭର କାହାନ୍ତି?") == Language.ODIA

    # 13. Assamese
    assert language_detector.detect("মোৰ ড্ৰাইভাৰ ক'ত?") == Language.ASSAMESE

    # 14. Urdu
    assert language_detector.detect("میرا ڈرائیور کہاں ہے؟") == Language.URDU

    # 15. Mixed / Code-switching
    assert language_detector.detect("Where is my driver? मेरा ड्राइवर कहाँ है?") == Language.MIXED
