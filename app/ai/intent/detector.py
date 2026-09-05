import re

from app.ai.intent.schema import IntentResult
from app.ai.language.detector import language_detector
from app.common.enums.chat import Intent, Priority, RiskLevel

# Safety keywords are checked FIRST and override everything else.
# Never let a P0 signal get reclassified as routine FAQ.
SAFETY_KEYWORDS = re.compile(
    r"\b(accident|emergency|sos|help me|threat|assault|harass|unsafe|danger|"
    r"police|आपातकाल|मदद|दुर्घटना|khतरा|jaan ka khatra)\b",
    re.IGNORECASE,
)

INTENT_KEYWORD_MAP: list[tuple[Intent, re.Pattern]] = [
    (Intent.DRIVER_CANCELLED, re.compile(r"driver.*(cancel|cancelled)|driver ne cancel", re.I)),
    (Intent.DRIVER_LATE, re.compile(r"driver.*(late|not come|nahi aa raha|aayega)", re.I)),
    (Intent.NO_DRIVER, re.compile(r"no driver|driver nahi mil|koi driver nahi", re.I)),
    (Intent.RIDE_STATUS, re.compile(r"where.*driver|ride status|kaha hai driver", re.I)),
    (Intent.FARE, re.compile(r"fare|price|kitna paisa|charge", re.I)),
    (Intent.PAYMENT_FAILED, re.compile(r"payment fail|paise nahi kate|payment issue", re.I)),
    (Intent.REFUND, re.compile(r"refund|paisa wapas", re.I)),
    (Intent.CANCELLATION, re.compile(r"cancel my ride|ride cancel karna", re.I)),
    (Intent.LOST_ITEM, re.compile(r"lost item|chhoot gaya|left.*(phone|bag|item)", re.I)),
    (Intent.WALLET, re.compile(r"wallet", re.I)),
    (Intent.RATING, re.compile(r"rating|rate.*driver", re.I)),
    (Intent.PROMO, re.compile(r"promo|coupon|discount code", re.I)),
    (Intent.HUMAN_AGENT, re.compile(r"human agent|talk to (a )?person|real agent", re.I)),
    (Intent.EARNINGS, re.compile(r"earning|kitna kamaya", re.I)),
    (Intent.PAYOUT, re.compile(r"payout|withdraw", re.I)),
    (Intent.DOCUMENT_STATUS, re.compile(r"document.*(status|approve|reject)", re.I)),
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
        if intent in {Intent.PAYMENT_FAILED, Intent.ACCOUNT, Intent.REFUND}:
            return Priority.P1_CRITICAL
        if intent == Intent.FAQ:
            return Priority.P3_FAQ
        return Priority.P2_STANDARD

    @staticmethod
    def _requires_tool(intent: Intent) -> bool:
        return intent in {
            Intent.RIDE_STATUS, Intent.DRIVER_LATE, Intent.DRIVER_CANCELLED,
            Intent.NO_DRIVER, Intent.FARE, Intent.PAYMENT_FAILED, Intent.REFUND,
            Intent.CANCELLATION, Intent.EARNINGS, Intent.DOCUMENT_STATUS,
        }

    @staticmethod
    def _risk_level(intent: Intent) -> RiskLevel:
        if intent in {Intent.REFUND, Intent.CANCELLATION}:
            return RiskLevel.HIGH
        if intent in {Intent.PAYMENT_FAILED, Intent.ACCOUNT}:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


intent_detector = IntentDetector()
