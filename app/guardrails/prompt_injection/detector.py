import re

# Heuristic signatures for common jailbreak / injection patterns.
# This is a defense-in-depth layer, not the sole safeguard -- tool
# authorization checks are the hard boundary regardless of what the
# LLM is told to do.
INJECTION_PATTERNS = [
    re.compile(r"ignore (all|your|previous|the) (instructions|prompt)", re.I),
    re.compile(r"system prompt|reveal.*(prompt|instructions)", re.I),
    re.compile(r"you are now (admin|root|developer mode|dan)", re.I),
    re.compile(r"disregard (any|all) (safety|policy|rules)", re.I),
    re.compile(r"grant (me )?(admin|database|root) access", re.I),
    re.compile(r"call .*(tool|refund|cancel).*without confirmation", re.I),
    re.compile(r"show me (another|other) (customer|user|driver)('s)? (data|info|details)", re.I),
    re.compile(r"pretend (you are|to be)", re.I),
    re.compile(r"jailbreak", re.I),
]


class PromptInjectionDetector:
    def is_suspicious(self, text: str) -> bool:
        return any(p.search(text) for p in INJECTION_PATTERNS)

    def matched_patterns(self, text: str) -> list[str]:
        return [p.pattern for p in INJECTION_PATTERNS if p.search(text)]


prompt_injection_detector = PromptInjectionDetector()
