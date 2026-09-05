import re

PATTERNS: dict[str, re.Pattern] = {
    "PHONE": re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "PAN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


class PIIRedactor:
    """Detects and masks PII before it is logged, cached, or embedded in
    prompts. Use `redact` for logs/analytics and `detect` when the caller
    needs to know PII was present without altering the original text."""

    def detect(self, text: str) -> list[str]:
        return [label for label, pattern in PATTERNS.items() if pattern.search(text)]

    def redact(self, text: str) -> str:
        redacted = text
        for label, pattern in PATTERNS.items():
            redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
        return redacted


pii_redactor = PIIRedactor()
