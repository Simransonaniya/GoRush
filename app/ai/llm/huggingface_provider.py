import json
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.llm.provider import ChatMessage, LLMProvider, LLMResponse, ToolSpec
from app.common.exceptions.base import UpstreamUnavailableError
from app.core.config import get_settings

HF_ROUTER_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
HF_EMBEDDINGS_URL_TEMPLATE = "https://router.huggingface.co/hf-inference/models/{model}"

DEFAULT_HF_CHAT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
DEFAULT_HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Matches any JSON object that contains a "tool_call" key anywhere in the
# model's text output — used as a fast pre-check before the full scan.
_TOOL_CALL_SENTINEL = re.compile(r'"tool_call"\s*:', re.DOTALL)


def _scan_tool_call(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Robustly find and remove a ``{"tool_call": {...}}`` JSON object from
    arbitrary model output using Python's own JSON decoder for brace matching
    rather than a regex.  Handles:
    - Nested objects in ``input`` (e.g. structured arguments)
    - Model preamble / postamble text before or after the JSON blob
    - Variable whitespace and line breaks inside the JSON

    Returns (remaining_text, tool_calls) where remaining_text has the JSON
    object stripped out and tool_calls is a list of extracted call dicts.
    If no valid tool-call JSON is found, returns (original_text, []).
    """
    if not _TOOL_CALL_SENTINEL.search(text):
        return text, []

    # Walk every '{' in the string; try to parse a JSON object starting there.
    decoder = json.JSONDecoder()
    idx = 0
    while True:
        start = text.find("{", idx)
        if start == -1:
            break
        try:
            parsed, end_offset = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            idx = start + 1
            continue

        # Found a valid JSON object — check whether it has a "tool_call" key
        if isinstance(parsed, dict) and "tool_call" in parsed:
            call = parsed["tool_call"]
            if isinstance(call, dict) and "name" in call:
                tool_calls = [{"name": call["name"], "input": call.get("input", {}), "id": None}]
                # Remove the matched span from the text and clean up whitespace
                remaining = (text[:start] + text[start + end_offset:]).strip()
                return remaining, tool_calls

        idx = start + 1

    return text, []


class HuggingFaceProvider(LLMProvider):
    def __init__(self, model: str | None = None, embedding_model: str | None = None):
        settings = get_settings()
        self.api_key = settings.llm_api_key
        self.model = model or DEFAULT_HF_CHAT_MODEL
        self.embedding_model = embedding_model or DEFAULT_HF_EMBEDDING_MODEL
        self.timeout = settings.llm_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4), reraise=True)
    async def _post(self, url: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, headers=self._headers(), json=payload)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as exc:
                raise UpstreamUnavailableError(f"Hugging Face provider error: {exc}") from exc

    def _build_tool_instruction(self, tools: list[ToolSpec]) -> str:
        tool_list = "\n".join(f"- {t.name}: {t.description} (args schema: {json.dumps(t.input_schema)})" for t in tools)
        return (
            "You may call ONE of the following tools if needed. "
            "To call a tool, respond with ONLY this JSON and nothing else -- "
            "no greeting, no explanation, no extra text before or after it:\n"
            '{"tool_call": {"name": "<tool_name>", "input": {...}}}\n'
            "Otherwise, respond normally in plain text.\n\nAvailable tools:\n" + tool_list
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        full_system = system or ""
        if tools:
            full_system = f"{full_system}\n\n{self._build_tool_instruction(tools)}".strip()

        chat_messages = []
        if full_system:
            chat_messages.append({"role": "system", "content": full_system})
        chat_messages.extend({"role": m.role, "content": m.content} for m in messages)

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = await self._post(HF_ROUTER_CHAT_URL, payload)
        choice = data["choices"][0]
        text = choice["message"]["content"] or ""

        # Use the robust JSON scanner instead of a regex
        text, tool_calls = _scan_tool_call(text)

        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            model=data.get("model", self.model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            stop_reason=choice.get("finish_reason"),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        chat_messages = []
        if system:
            chat_messages.append({"role": "system", "content": system})
        chat_messages.extend({"role": m.role, "content": m.content} for m in messages)

        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", HF_ROUTER_CHAT_URL, headers=self._headers(), json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if raw == "[DONE]" or not raw:
                        continue
                    event = json.loads(raw)
                    delta = event["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield delta["content"]

    async def embeddings(self, texts: list[str]) -> list[list[float]]:
        url = HF_EMBEDDINGS_URL_TEMPLATE.format(model=self.embedding_model)
        data = await self._post(url, {"inputs": texts})
        if data and isinstance(data[0][0], list):
            return [[sum(dim) / len(dim) for dim in zip(*sentence)] for sentence in data]
        return data

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

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()
        idx = 0
        while True:
            start = cleaned.find("{", idx)
            if start == -1:
                break
            try:
                parsed, _ = decoder.raw_decode(cleaned, start)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                idx = start + 1
                continue

        return {"note": "fallback_parsed", "raw": cleaned[:200]}