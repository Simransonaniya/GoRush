from app.ai.llm.provider import LLMProvider
from app.core.config import Settings, get_settings


def build_llm_provider(*, model: str | None = None, settings: Settings | None = None) -> LLMProvider:
    """Single switch point for LLM vendor selection. Set LLM_PROVIDER in
    .env to 'anthropic', 'huggingface', or 'mock' and everything else
    (gateway, orchestrator, RAG) picks it up automatically -- no other
    code changes."""
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        from app.ai.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model or settings.llm_model_primary)

    if provider == "huggingface":
        from app.ai.llm.huggingface_provider import HuggingFaceProvider

        return HuggingFaceProvider(model=model or settings.llm_model_primary)

    if provider == "mock":
        from app.ai.llm.mock_provider import MockLLMProvider

        return MockLLMProvider(model=model or settings.llm_model_primary)

    raise ValueError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use 'anthropic', 'huggingface', or 'mock'.")