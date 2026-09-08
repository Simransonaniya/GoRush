"""
Mock LLM provider.

Why this exists: spec section 43 explicitly says mock external
integrations clearly rather than pretending they're real. This lets us
build and test the whole chat pipeline (sessions, persistence, auth,
guardrails in later phases) without needing a real API key yet, and
without ever silently pretending to be a real model.
"""

from collections.abc import AsyncIterator
from typing import Any

from app.ai.llm.provider import ChatMessage, LLMProvider, LLMResponse, ToolSpec
from app.core.config import get_settings


class MockLLMProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or "mock-v1"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        last_user_msg = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        reply = (
            f"[MOCK RESPONSE] I received: \"{last_user_msg}\". "
            "GoRush AI support assistant active in local development mode."
        )
        return LLMResponse(text=reply, tool_calls=[], model="mock-v1", input_tokens=0, output_tokens=0)

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        reply = "[MOCK STREAM] Processing response..."
        yield reply

    async def structured_output(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any],
        system: str | None = None,
    ) -> dict[str, Any]:
        return {"intent": "faq", "confidence": 0.95, "note": "mock provider inference"}

    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        dim = get_settings().embedding_dim
        return [[0.0] * dim for _ in texts]


