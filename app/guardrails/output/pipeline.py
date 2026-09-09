import re
from app.guardrails.pii.redactor import pii_redactor

FORBIDDEN_PHRASES = [
    "as an ai language model",
    "i am a human agent",
    "system prompt:",
]

EMERGENCY_CLAIM_PATTERNS = [
    re.compile(r"emergency services (have been|were|are) contacted", re.I),
    re.compile(r"police (has been|was|have been|is being) (called|contacted)", re.I),
    re.compile(r"police ko (contact|call) kar diya", re.I),
    re.compile(r"पुलिस को (बुला दिया|संपर्क कर दिया|फोन कर दिया)", re.I),
]


class OutputGuardrailPipeline:
    """Final safety net before a generated response reaches the user.
    Redacts stray PII, strips disallowed phrasing, prevents false claims about
    calling emergency services, and never lets the bot claim to be human or expose internal instructions."""

    def run(self, text: str) -> str:
        cleaned = pii_redactor.redact(text)

        # Sanitize false claims about emergency services
        for pattern in EMERGENCY_CLAIM_PATTERNS:
            if pattern.search(cleaned):
                cleaned = pattern.sub("our safety team has been alerted immediately", cleaned)

        lowered = cleaned.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                cleaned = pattern.sub("", cleaned)
        return cleaned.strip()


output_guardrail_pipeline = OutputGuardrailPipeline()

