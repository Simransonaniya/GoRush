from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class LLMResponse(BaseModel):
    text: str
    tool_calls: list[dict[str, Any]] = []
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None


class LLMProvider(ABC):
    """All LLM providers (Anthropic, OpenAI, local, etc.) implement this
    interface. Application code must depend only on this abstraction so the
    backend is never tightly coupled to one vendor."""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def embeddings(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def structured_output(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any],
        system: str | None = None,
    ) -> dict[str, Any]: ...
