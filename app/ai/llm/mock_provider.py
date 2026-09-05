"""
Mock LLM provider.

Why this exists: spec section 43 explicitly says mock external
integrations clearly rather than pretending they're real. This lets us
build and test the whole chat pipeline (sessions, persistence, auth,
guardrails in later phases) without needing a real API key yet, and
without ever silently pretending to be a real model.
"""

from app.ai.llm.base import LLMMessage, LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        last_user_msg = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        reply = (
            f"[MOCK RESPONSE] I received: \"{last_user_msg}\". "
            "Real LLM provider is not yet configured (LLM_PROVIDER=mock)."
        )
        return LLMResponse(content=reply, model="mock-v1", input_tokens=0, output_tokens=0)

    async def structured_output(self, messages: list[LLMMessage], schema: dict, **kwargs) -> dict:
        return {"intent": "faq", "confidence": 0.0, "note": "mock provider - no real inference"}
