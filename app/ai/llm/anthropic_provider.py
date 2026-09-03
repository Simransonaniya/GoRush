"""
Anthropic Claude provider.

Real implementation -- used when LLM_PROVIDER=anthropic and LLM_API_KEY
is set. Uses httpx directly against the Messages API so we don't force
an extra SDK dependency in Phase 1; can swap to the official `anthropic`
python SDK later without changing anything outside this file.
"""

import httpx

from app.ai.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.core.config import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(LLMProvider):
    def __init__(self):
        if not settings.LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is not set for AnthropicProvider")
        self._headers = {
            "x-api-key": settings.LLM_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        system = next((m.content for m in messages if m.role == "system"), None)
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        body = {
            "model": kwargs.get("model", settings.LLM_MODEL),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "messages": turns,
        }
        if system:
            body["system"] = system

        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(ANTHROPIC_API_URL, headers=self._headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        text = "".join(block["text"] for block in data["content"] if block["type"] == "text")
        usage = data.get("usage", {})
        return LLMResponse(
            content=text,
            model=data.get("model", settings.LLM_MODEL),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

    async def structured_output(self, messages: list[LLMMessage], schema: dict, **kwargs) -> dict:
        # Phase 1: not yet implemented -- wired up properly in Phase 2
        # (intent engine) using tool-call-style structured outputs.
        raise NotImplementedError("structured_output arrives in Phase 2 (intent engine)")
