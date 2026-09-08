import re

from app.ai.intent.schema import IntentResult
from app.ai.language.detector import language_detector
from app.common.enums.chat import Intent, Priority, RiskLevel

# Safety keywords are checked FIRST and override everything else.
# Never let a P0 signal get reclassified as routine FAQ.
SAFETY_KEYWORDS = re.compile(
    r"\b(accident|emergency|sos|threat|assault|harass|unsafe|danger|"
    r"police|आपातकाल|दुर्घटना|khatra|jaan ka khatra|help emergency|help accident)\b",
    re.IGNORECASE,
)

INTENT_KEYWORD_MAP: list[tuple[Intent, re.Pattern]] = [
    # Driver specific intents
    (Intent.CUSTOMER_CANCELLED, re.compile(r"customer cancel|rider cancel|customer ne cancel|rider ne cancel|customer cancelled|rider.*trip cancel|customer.*trip cancel", re.I)),
    (Intent.CUSTOMER_NOT_FOUND, re.compile(r"customer (is )?not (at|found|here)|rider missing|customer nahi mila|customer nahi hai|rider location pe nahi|customer unreachable|customer not picking", re.I)),
    (Intent.ACCEPTANCE, re.compile(r"accept.*(ride|booking|duty)|ride accept|booking accept|duty accept|cannot accept|accept issue", re.I)),
    (Intent.RIDE_OFFER, re.compile(r"ride offer|booking offer|offer nahi aa|ride offer nahi|booking nahi mil", re.I)),
    (Intent.PAYOUT, re.compile(r"payout|withdraw|bank transfer|payout delay|paise kab aayenge|payout issue|bank payout", re.I)),
    (Intent.INCENTIVE, re.compile(r"incentive|bonus|target bonus|trip bonus|peak hour bonus|incentive status|bonus kab milega", re.I)),
    (Intent.DOCUMENT_STATUS, re.compile(r"document.*(status|approve|reject|expir)|(license|rc|insurance).*(expir|status|approve)|kagaz expire|document verification", re.I)),
    (Intent.VEHICLE_DOCUMENT, re.compile(r"vehicle (document|support|change)|add vehicle|change vehicle|update rc|gadi badalna|new vehicle", re.I)),
    (Intent.NAVIGATION, re.compile(r"navigation|gps|map issue|map wrong|galat route|map nahi chal", re.I)),
    (Intent.APP_TROUBLESHOOTING, re.compile(r"app (crash|freeze|freezing|hang|issue|kharab|update)", re.I)),
    (Intent.CASH_PAYMENT, re.compile(r"cash payment|cash ride|customer didn'?t pay|cash nahi diya|cash collection|cash amount", re.I)),
    # Customer / Driver overlapping intents
    (Intent.DRIVER_CANCELLED, re.compile(r"driver.*(cancel|cancelled)|driver ne cancel", re.I)),
    (Intent.DRIVER_LATE, re.compile(r"driver.*(late|not come|nahi aa raha|aayega|come|arrive|kab aayega|delay)", re.I)),
    (Intent.DRIVER_NOT_MOVING, re.compile(
        r"driver.*(not moving|stuck|stopped|ruk gaya|khada hai|move nahi|nahi chal raha)"
        r"|driver is not moving|driver hasn'?t moved",
        re.I,
    )),
    (Intent.NO_DRIVER, re.compile(r"no driver|driver nahi mil|koi driver nahi", re.I)),
    (Intent.RIDE_STATUS, re.compile(r"(where|when|kaha|eta|location).*(driver|ride)|ride status", re.I)),
    (Intent.FARE, re.compile(r"fare|price|kitna paisa|charge", re.I)),
    (Intent.PAYMENT_FAILED, re.compile(r"payment fail|paise nahi kate|payment issue", re.I)),
    (Intent.REFUND, re.compile(
        r"refund|paisa wapas"
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
        r"cancel.*(my )?ride|ride cancel|cancel karna|cancel kar|trip cancel"
        r"|ride cancel karna",
        re.I,
    )),
    (Intent.LOST_ITEM, re.compile(r"lost item|chhoot gaya|left.*(phone|bag|item)", re.I)),
    (Intent.WALLET, re.compile(
        r"wallet|balance|top.?up|add money|transaction history|wallet se",
        re.I,
    )),
    (Intent.RATING, re.compile(r"rating|rate.*driver", re.I)),
    (Intent.PROMO, re.compile(r"promo|coupon|discount code", re.I)),
    (Intent.REFERRAL, re.compile(
        r"referral|refer.*(friend|code|earn)|invite.*friend|share.*code",
        re.I,
    )),
    (Intent.ACCOUNT, re.compile(
        r"account|profile|login|password|delete.*(account|data)|change.*email"
        r"|change.*phone|name change|privacy",
        re.I,
    )),
    (Intent.HUMAN_AGENT, re.compile(r"human agent|talk to (a )?person|real agent", re.I)),
    (Intent.EARNINGS, re.compile(r"earning|kamai|daily earning|weekly earning|monthly earning|kitna kamaya|today'?s earning|haftewari kamai|aaj ki kamai", re.I)),
]


class IntentDetector:
    """Deterministic fast-path over common intents. Anything that doesn't
    match confidently should be routed to the LLM-based classifier
    (ai/orchestrator) rather than guessed here."""

    def detect(self, text: str) -> IntentResult:
        language = language_detector.detect(text)

        if SAFETY_KEYWORDS.search(text):
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
                return IntentResult(
                    intent=intent,
                    confidence=0.75,
                    urgency=self._default_urgency(intent),
                    language=language,
                    requires_tool=self._requires_tool(intent),
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
    def _default_urgency(intent: Intent) -> Priority:
        if intent in {Intent.PAYMENT_FAILED, Intent.ACCOUNT, Intent.REFUND, Intent.CUSTOMER_NOT_FOUND, Intent.CASH_PAYMENT, Intent.PAYOUT}:
            return Priority.P1_CRITICAL
        if intent == Intent.FAQ:
            return Priority.P3_FAQ
        return Priority.P2_STANDARD

    @staticmethod
    def _requires_tool(intent: Intent) -> bool:
        return intent in {
            Intent.RIDE_STATUS, Intent.DRIVER_LATE, Intent.DRIVER_NOT_MOVING,
            Intent.DRIVER_CANCELLED, Intent.NO_DRIVER, Intent.FARE,
            Intent.PAYMENT_FAILED, Intent.REFUND,
            Intent.CANCELLATION,
            Intent.LOST_ITEM,   # spec: "Create lost-item workflow"
            Intent.WALLET,      # spec: "Balance and transaction help"
            Intent.EARNINGS, Intent.PAYOUT, Intent.INCENTIVE,
            Intent.DOCUMENT_STATUS, Intent.VEHICLE_DOCUMENT, Intent.CASH_PAYMENT,
            Intent.RIDE_OFFER, Intent.ACCEPTANCE, Intent.CUSTOMER_NOT_FOUND, Intent.CUSTOMER_CANCELLED,
        }

    @staticmethod
    def _risk_level(intent: Intent) -> RiskLevel:
        if intent in {Intent.REFUND, Intent.CANCELLATION, Intent.ACCOUNT}:
            return RiskLevel.HIGH
        if intent in {Intent.PAYMENT_FAILED, Intent.WALLET, Intent.LOST_ITEM, Intent.PAYOUT, Intent.VEHICLE_DOCUMENT, Intent.CASH_PAYMENT}:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


intent_detector = IntentDetector()
