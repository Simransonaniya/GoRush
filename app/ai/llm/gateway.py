from app.ai.llm.factory import build_llm_provider
from app.ai.llm.provider import ChatMessage, LLMProvider, LLMResponse, ToolSpec
from app.common.exceptions.base import UpstreamUnavailableError
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DETERMINISTIC_FALLBACK_TEXT = (
    "I'm having trouble reaching our AI system right now. "
    "I can connect you with a support agent, or you can try again shortly."
)


class LLMGateway:
    """Wraps a primary + fallback LLMProvider and guarantees the caller
    always gets *something* usable back: primary model -> secondary model
    -> deterministic fallback text."""

    def __init__(self, primary: LLMProvider | None = None, fallback: LLMProvider | None = None):
        settings = get_settings()
        self.primary = primary or build_llm_provider(model=settings.llm_model_primary, settings=settings)
        self.fallback = fallback or build_llm_provider(model=settings.llm_model_fallback, settings=settings)

    async def chat_with_fallback(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        try:
            return await self.primary.chat(
                messages, system=system, tools=tools, temperature=temperature, max_tokens=max_tokens
            )
        except UpstreamUnavailableError:
            logger.warning("llm_primary_failed_falling_back")

        try:
            return await self.fallback.chat(
                messages, system=system, tools=tools, temperature=temperature, max_tokens=max_tokens
            )
        except UpstreamUnavailableError:
            logger.error("llm_fallback_also_failed")
            return LLMResponse(text=DETERMINISTIC_FALLBACK_TEXT, model="deterministic-fallback")