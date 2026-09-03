"""
Provider-agnostic LLM interface.

Spec ref: section 11.

Why this exists: we never want business logic calling "Anthropic" or
"OpenAI" directly. Every part of the app talks to this abstract
interface. Swapping providers, adding fallback, or mocking in tests
becomes trivial because nothing outside this folder knows which
provider is in use.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        """Non-streaming chat completion."""
        raise NotImplementedError

    @abstractmethod
    async def structured_output(self, messages: list[LLMMessage], schema: dict, **kwargs) -> dict:
        """Chat completion constrained to a JSON schema (for intent detection etc.)."""
        raise NotImplementedError
