"""
LLM Gateway factory.

This is the single place that decides *which* provider implementation
to hand out, based on config. Nothing else in the app should import
MockLLMProvider or AnthropicProvider directly -- always go through
`get_llm_provider()`. This is what makes fallback (spec section 11 /37)
possible later: we can wrap this in try/except and fall back to a
secondary provider or a deterministic response.
"""

from functools import lru_cache

from app.ai.llm.base import LLMProvider
from app.core.config import settings


@lru_cache
def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "anthropic":
        from app.ai.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    from app.ai.llm.mock_provider import MockLLMProvider
    return MockLLMProvider()
