from app.guardrails.pii.redactor import pii_redactor

FORBIDDEN_PHRASES = [
    "as an ai language model",
    "i am a human agent",
    "system prompt:",
]


class OutputGuardrailPipeline:
    """Final safety net before a generated response reaches the user.
    Redacts stray PII, strips disallowed phrasing, and never lets the
    bot claim to be human or expose internal instructions."""

    def run(self, text: str) -> str:
        cleaned = pii_redactor.redact(text)
        lowered = cleaned.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                cleaned = cleaned.replace(phrase, "")
        return cleaned.strip()


output_guardrail_pipeline = OutputGuardrailPipeline()
