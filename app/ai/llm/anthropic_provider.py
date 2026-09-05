<<<<<<< HEAD
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.llm.provider import ChatMessage, LLMProvider, LLMResponse, ToolSpec
from app.common.exceptions.base import UpstreamUnavailableError
from app.core.config import get_settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.model = model or settings.llm_model_primary
        self.timeout = settings.llm_timeout_seconds
        self.max_retries = settings.llm_max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(ANTHROPIC_API_URL, headers=self._headers(), json=payload)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise UpstreamUnavailableError(f"LLM provider error: {exc}") from exc

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [m.model_dump() for m in messages],
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ]

        data = await self._post(payload)
        text_parts, tool_calls = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_calls.append({"name": block["name"], "input": block.get("input", {}), "id": block.get("id")})

        usage = data.get("usage", {})
        return LLMResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            model=data.get("model", self.model),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            stop_reason=data.get("stop_reason"),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [m.model_dump() for m in messages],
            "stream": True,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", ANTHROPIC_API_URL, headers=self._headers(), json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if raw == "[DONE]" or not raw:
                        continue
                    event = json.loads(raw)
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")

    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        # Anthropic does not currently expose a first-party embeddings endpoint;
        # plug in the org's chosen embeddings provider here (Voyage AI is
        # Anthropic's recommended partner). Kept as an explicit seam.
        raise NotImplementedError("Configure an embeddings backend (e.g. Voyage AI) here.")

    async def structured_output(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any],
        system: str | None = None,
    ) -> dict[str, Any]:
        instruction = (
            "Respond with ONLY valid JSON matching this schema, no prose, no markdown fences:\n"
            + json.dumps(json_schema)
        )
        full_system = f"{system}\n\n{instruction}" if system else instruction
        result = await self.chat(messages, system=full_system, temperature=0.0, max_tokens=1024)
        cleaned = result.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
=======
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
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
