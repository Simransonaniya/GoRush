from pydantic import BaseModel

from app.guardrails.pii.redactor import pii_redactor
from app.guardrails.prompt_injection.detector import prompt_injection_detector


class InputGuardrailResult(BaseModel):
    is_safe: bool
    prompt_injection_detected: bool
    pii_labels_found: list[str]
    sanitized_for_logging: str


class InputGuardrailPipeline:
    def run(self, text: str) -> InputGuardrailResult:
        injection = prompt_injection_detector.is_suspicious(text)
        pii_labels = pii_redactor.detect(text)
        return InputGuardrailResult(
            # Suspicious input is not auto-blocked -- the LLM is instructed
            # to refuse acting on embedded instructions while still helping
            # with the user's legitimate underlying request where possible.
            is_safe=True,
            prompt_injection_detected=injection,
            pii_labels_found=pii_labels,
            sanitized_for_logging=pii_redactor.redact(text),
        )


input_guardrail_pipeline = InputGuardrailPipeline()
