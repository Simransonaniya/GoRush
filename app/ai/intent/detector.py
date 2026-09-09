import re

from app.ai.intent.schema import IntentResult
from app.ai.language.detector import language_detector
from app.common.enums.chat import Intent, Priority, RiskLevel

# Multilingual safety patterns for active emergencies (P0) vs safety policy/procedure inquiries (P3)
SAFETY_POLICY_PATTERN = re.compile(
    r"(procedure|policy|rules|guidelines|what (to|should i) do after|yesterday|last week|few days ago|past accident"
    r"|नियम|नीति|प्रक्रिया|दिशा-निर्देश|कल हुआ|कल का|पिछले हफ्ते|क्या करना चाहिए|kya karein|kya karna"
    r"|પોલિસી|પ્રક્રિયા|ਨਿਯਮ|ਪ੍ਰਕਿਰਿਆ)",
    re.IGNORECASE,
)

IMMEDIATE_EMERGENCY_OVERRIDE = re.compile(
    r"(turant|abhi|right now|immediately|call police|in danger|help me right now|save me|तुरंत|अभी|तत्काल)",
    re.IGNORECASE,
)

ACTIVE_SAFETY_PATTERN = re.compile(
    r"(accident|i crashed|car crash|vehicle crash|crashed into|crashed my|crashed the|had a crash|collision|hit|durghatna|hadsa|akastmat|apghat"
    r"|एक्सीडेंट|दुर्घटना|हादसा|अपघात|અકસ્માત|দুর্ঘটনা|حادثہ|விபத்து|అపాయం|ಅಪಘಾತ|അപകടം"
    r"|emergency|sos|danger|dangerous|unsafe|khatra|khatre|in danger"
    r"|आपातकाल|आपत्कालीन|खतरा|खतरे|जोखम|धोका|বিপদ|അപകടം|అత్యవసరం|ತುರ್ತು"
    r"|threat|threatened|threaten|dhamki|attack|attacked|assault|assaulted|harass|harassed|hamla"
    r"|धमकी|हमला|हल्ला|হুমকি|হামলা|బెదిరింపు|ದಾಳಿ|ഭീഷണി"
    r"|police|ambulance|help emergency|help accident|immediate help|turant madad|turant sahayata|abhi help|save me|bachao"
    r"|मदद|सहायता|पुलिस|एंबुलेंस|बचाओ|ਮਦਦ|ਸਹਾਇਤਾ|ਮਦਦ|પોલીਸ|మదత్|உதவி|ಸಹಾಯ|സഹായം"
    r"|सहायता चाहिए|मदद चाहिए|help chahiye)",
    re.IGNORECASE,
)

# Backward compatibility alias
SAFETY_KEYWORDS = ACTIVE_SAFETY_PATTERN


INTENT_KEYWORD_MAP: list[tuple[Intent, re.Pattern]] = [
    # Driver specific intents
    (Intent.CUSTOMER_CANCELLED, re.compile(r"customer cancel|rider cancel|customer ne cancel|rider ne cancel|customer cancelled|rider.*trip cancel|customer.*trip cancel", re.I)),
    (Intent.CUSTOMER_NOT_FOUND, re.compile(r"customer (is )?not (at|found|here)|rider missing|customer nahi mila|customer nahi hai|rider location pe nahi|customer unreachable|customer not picking", re.I)),
    (Intent.ACCEPTANCE, re.compile(r"accept.*(ride|booking|duty|rule|rules|policy)|ride accept|booking accept|duty accept|cannot accept|accept issue", re.I)),
    (Intent.RIDE_OFFER, re.compile(r"ride offer|booking offer|offer nahi aa|ride offer nahi|booking nahi mil", re.I)),
    (Intent.PAYOUT, re.compile(r"payout|withdraw|bank transfer|payout delay|paise kab aayenge|payout issue|bank payout", re.I)),
    (Intent.INCENTIVE, re.compile(r"incentive|bonus|target bonus|trip bonus|peak hour bonus|incentive status|bonus kab milega", re.I)),
    (Intent.DOCUMENT_STATUS, re.compile(
        r"document.*(status|approve|reject|expir|require|needed|list|rule|verification|verify|verified)|(license|rc|insurance).*(expir|status|approve|require|needed)"
        r"|kagaz|document verification|what documents|driver document|onboarding document|दस्तावेज़|દસ્તાવેજ|নথি",
        re.I,
    )),
    (Intent.VEHICLE_DOCUMENT, re.compile(r"vehicle (document|support|change)|add vehicle|change vehicle|update rc|gadi badalna|new vehicle", re.I)),
    (Intent.NAVIGATION, re.compile(r"navigation|gps|map issue|map wrong|galat route|map nahi chal", re.I)),
    (Intent.APP_TROUBLESHOOTING, re.compile(r"app (crash|freeze|freezing|hang|issue|kharab|update|not working|work|problem|error)|not working|slow app|driver app", re.I)),
    (Intent.CASH_PAYMENT, re.compile(
        r"cash payment|cash ride|customer didn'?t pay|customer did not|customer has not paid|cash nahi diya|cash collection|cash amount"
        r"|payment nahi|ne payment|payment nahi kiya|payment nahi mila|payment nahi hua|pay nahi kiya|payment नहीं"
        r"|भुगतान नहीं|पैसे नहीं दिए|कैश नहीं दिया|रुपये नहीं दिए|पैसे नहीं मिले|कैश नहीं मिला"
        r"|भुगतान कोनी|कोनी कर्यो|पिया कोनी|पैसे कोनी|कोनी दिया|koni karyo|koni"
        r"|ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ|ਪੇਮੈਂਟ ਨਹੀਂ|ਕੀਤਾ|kiti|kitta|ਪੈਸੇ ਨਹੀਂ ਦਿੱਤੇ"
        r"|ચુકવણી કરી નથી|ચુકવણી નથી|nathi kari|nathi|પૈસા નથી આપ્યા|payment કર્યું નથી"
        r"|পেমেন্ট করেনি|পেমেন্ট হয়নি|টাকা দেয়নি|পেমেন্ট|ক্যাশ|payment করেনি"
        r"|पेमेंट केले नाही|पैसे दिले नाहीत|कॅश दिली नाही"
        r"|பணம் செலுத்தவில்லை|பணம் தரவில்லை"
        r"|చెల్లింపు చేయలేదు|డబ్బులు ఇవ్వలేదు"
        r"|ಪಾವತಿ ಮಾಡಲಿಲ್ಲ|ಹಣ ನೀಡಲಿಲ್ಲ"
        r"|പണമടച്ചില്ല|പണം നൽകിയില്ല"
        r"|ଦେୟ ଦେଇନାହାଁନ୍ତି|ଟଙ୍କା ଦେଇନାହାଁନ୍ତି"
        r"|পৰিশোধ কৰা নাই|টকা দিয়া নাই"
        r"|ادائیگی نہیں کی|رقم نہیں دی",
        re.I,
    )),
    # Customer / Driver overlapping intents
    (Intent.DRIVER_CANCELLED, re.compile(r"driver.*(cancel|cancelled)|driver ne cancel", re.I)),
    (Intent.DRIVER_LATE, re.compile(r"driver.*(late|not come|nahi aa raha|aayega|come|arrive|kab aayega|delay)|what is my eta|driver eta|my eta|get eta|\beta\b", re.I)),
    (Intent.DRIVER_NOT_MOVING, re.compile(
        r"driver.*(not moving|stuck|stopped|ruk gaya|khada hai|move nahi|nahi chal raha)"
        r"|driver is not moving|driver hasn'?t moved",
        re.I,
    )),
    (Intent.NO_DRIVER, re.compile(r"no driver|driver nahi mil|koi driver nahi", re.I)),
    (Intent.RIDE_STATUS, re.compile(r"(where|when|kaha|kahan|location|eta|कहाँ|कहा|कहान|ક્યાં|કોথায়|ਕਿੱਥੇ|कुठे).*(driver|ride|राइड|રાઇડ|রাইড|ਰਾਈਡ)|ride status|active ride|active.*ride|एक्टिव राइड|એક્ટિવ રાઇડ|সক্রিয় রাইড|ਸਰਗਰਮ ਰਾਈਡ", re.I)),
    (Intent.FARE, re.compile(r"fare|price|kitna paisa|charge|how much.*fare|fare breakdown|calculated|why.*fare|fare calculation|fare policy|किराया", re.I)),
    (Intent.PAYMENT_FAILED, re.compile(r"payment fail|paise nahi kate|payment issue|payment status|what is my payment status|check payment status|payment policy|payment method", re.I)),
    (Intent.REFUND, re.compile(
        r"refund|paisa wapas|refund policy|refund process|how.*refund|refund rules"
        r"|பணம்\s*திரும்ப|திரும்பப்\s*பெற|பணத்தைத்\s*திரும்ப"
        r"|రీఫండ్|డబ్బు\s*తిరిగి"
        r"|ಹಣ\s*ಮರಳಿ|ರಿಫಂಡ್"
        r"|തിരിച്ചടവ്|റീഫണ്ട്"
        r"|परतावा|पैसे\s*परत"
        r"|પૈસા\s*પાછા|રિફંડ"
        r"|টাকা\s*ফেরত|রিফান্ড"
        r"|ਪੈਸੇ\s*ਵਾਪਸ|ਰਿਫੰਡ",
        re.I,
    )),
    (Intent.CANCELLATION, re.compile(
        r"cancellation|cancel.*(policy|rule|rules|fee|charge|karna|kar|ride|trip)|(ride|trip).*cancel|cancellations"
        r"|कैंसिलेशन|केन्सलेशन|कैंसिल|केंसल|રદ|કેન્સલ|বাতিল|రద్దు|ரத்து|ರದ್ದು|റദ്ദാക്കൽ",
        re.I,
    )),
    (Intent.LOST_ITEM, re.compile(r"lost item|chhoot gaya|left.*(phone|bag|item)", re.I)),
    (Intent.WALLET, re.compile(
        r"wallet|balance|top.?up|add money|transaction history|wallet se",
        re.I,
    )),
    (Intent.RATING, re.compile(r"rating|rate.*driver", re.I)),
    (Intent.PROMO, re.compile(r"promo|coupon|discount code|promotion|promo policy|promo terms|offer terms", re.I)),
    (Intent.REFERRAL, re.compile(
        r"referral|refer.*(friend|code|earn)|invite.*friend|share.*code",
        re.I,
    )),
    (Intent.ACCOUNT, re.compile(
        r"account|profile|login|password|delete.*(account|data)|change.*(email|phone|setting|settings)|name change|privacy|onboard|onboarding|join as driver|sign up driver|register driver|चालक पंजीकरण",
        re.I,
    )),
    (Intent.FAQ, re.compile(r"faq|help center|support sla|support time|how long.*support|response time|general query|help info|\bsla\b", re.I)),
    (Intent.HUMAN_AGENT, re.compile(r"human agent|talk to (a )?person|real agent|connect.*agent|agent connect|support agent|customer care|speak to agent", re.I)),
    (Intent.EARNINGS, re.compile(r"earning|earn|kamai|daily earning|weekly earning|monthly earning|kitna kamaya|today'?s earning|haftewari kamai|aaj ki kamai|how much did i earn", re.I)),
]


class IntentDetector:
    """Deterministic fast-path over common intents. Anything that doesn't
    match confidently should be routed to the LLM-based classifier
    (ai/orchestrator) rather than guessed here."""

    @staticmethod
    def _is_policy_faq_text(text: str) -> bool:
        text_lower = text.lower()
        policy_phrases = [
            "policy", "rule", "rules", "how does", "what is the", "what are the",
            "terms", "faq", "procedure", "how long does", "what documents do", "how to", "what documents are",
            "why was", "how is", "explain", "onboarding", "sla", "process", "tell me about", "can you explain",
            "when can", "what happens if", "what should i do", "how can i",
            "पॉलिसी", "नियम", "क्या नियम", "नियम क्या", "प्रक्रिया", "दिशा-निर्देश", "kya hai", "kya hain",
            "પોલિસી", "નિયમો", "શું છે", "নীতি", "নিয়ম", "কী"
        ]
        exclude_personal = [
            "my document", "my documents", "my ride", "my refund", "my payment", "my earnings", "check my", "cancel my", "my account"
        ]
        return any(p in text_lower for p in policy_phrases) and not any(p in text_lower for p in exclude_personal)

    def detect(self, text: str) -> IntentResult:
        language = language_detector.detect(text)

        # 1. Distinguish safety policy / procedure / past non-active inquiries (P3) from active emergencies (P0)
        is_policy_past = bool(SAFETY_POLICY_PATTERN.search(text)) and not bool(IMMEDIATE_EMERGENCY_OVERRIDE.search(text))
        if is_policy_past and ACTIVE_SAFETY_PATTERN.search(text):
            return IntentResult(
                intent=Intent.SAFETY,
                confidence=0.90,
                urgency=Priority.P3_FAQ,
                language=language,
                requires_tool=False,
                requires_human=False,
                risk_level=RiskLevel.LOW,
            )

        # 2. Active safety emergency (P0)
        if ACTIVE_SAFETY_PATTERN.search(text):
            return IntentResult(
                intent=Intent.SAFETY,
                confidence=0.95,
                urgency=Priority.P0_EMERGENCY,
                language=language,
                requires_tool=True,
                requires_human=True,
                risk_level=RiskLevel.CRITICAL,
            )


        for intent, pattern in INTENT_KEYWORD_MAP:
            if pattern.search(text):
                is_policy = self._is_policy_faq_text(text)
                return IntentResult(
                    intent=intent,
                    confidence=0.75,
                    urgency=self._determine_urgency(text, intent),
                    language=language,
                    requires_tool=False if is_policy else self._requires_tool(intent, text),
                    risk_level=self._risk_level(intent),
                )


        # Low confidence -> caller should escalate to LLM classification
        # or ask a clarification question. Never fabricate an intent here.
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.2,
            urgency=Priority.P3_FAQ,
            language=language,
        )

    @staticmethod
    def _determine_urgency(text: str, intent: Intent) -> Priority:
        text_lower = text.lower()
        if ACTIVE_SAFETY_PATTERN.search(text):
            is_policy_past = bool(SAFETY_POLICY_PATTERN.search(text)) and not bool(IMMEDIATE_EMERGENCY_OVERRIDE.search(text))
            if is_policy_past:
                return Priority.P3_FAQ
            return Priority.P0_EMERGENCY


        # P1: Hacked account, security breach, critically blocked earnings/payment, cash payment dispute, or missing customer
        if any(w in text_lower for w in ["hack", "hacked", "compromise", "compromised", "account hacked"]) or \
           (any(w in text_lower for w in ["critical", "blocked", "cannot access", "severely blocked"]) and any(w in text_lower for w in ["payment", "earning", "earnings", "payout"])):
            return Priority.P1_CRITICAL

        if intent in {Intent.CASH_PAYMENT, Intent.CUSTOMER_NOT_FOUND, Intent.PAYOUT}:
            return Priority.P1_CRITICAL

        # P3: Policy, FAQ, generic rules questions
        if any(w in text_lower for w in ["policy", "rule", "rules", "how does", "what is the", "what are the", "terms", "faq", "procedure", "how long does", "what documents do"]):
            return Priority.P3_FAQ

        # P2: Driver issue, service issue, refund issue
        return Priority.P2_STANDARD

    @classmethod
    def _requires_tool(cls, intent: Intent, text: str = "") -> bool:
        if text and cls._is_policy_faq_text(text):
            return False
        return intent in {
            Intent.RIDE_STATUS, Intent.DRIVER_LATE, Intent.DRIVER_NOT_MOVING,
            Intent.DRIVER_CANCELLED, Intent.NO_DRIVER, Intent.FARE,
            Intent.PAYMENT_FAILED, Intent.REFUND,
            Intent.CANCELLATION,
            Intent.LOST_ITEM,
            Intent.WALLET,
            Intent.EARNINGS, Intent.PAYOUT, Intent.INCENTIVE,
            Intent.DOCUMENT_STATUS, Intent.VEHICLE_DOCUMENT, Intent.CASH_PAYMENT,
            Intent.RIDE_OFFER, Intent.ACCEPTANCE, Intent.CUSTOMER_NOT_FOUND, Intent.CUSTOMER_CANCELLED,
            Intent.HUMAN_AGENT,
        }


    @staticmethod
    def _risk_level(intent: Intent) -> RiskLevel:
        if intent in {Intent.REFUND, Intent.CANCELLATION, Intent.ACCOUNT}:
            return RiskLevel.HIGH
        if intent in {Intent.PAYMENT_FAILED, Intent.WALLET, Intent.LOST_ITEM, Intent.PAYOUT, Intent.VEHICLE_DOCUMENT, Intent.CASH_PAYMENT}:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


intent_detector = IntentDetector()
