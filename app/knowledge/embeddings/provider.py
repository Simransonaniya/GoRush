"""
Embeddings are resolved separately from the chat LLM_PROVIDER because
Anthropic has no first-party embeddings endpoint. By default this uses a
free Hugging Face sentence-transformers model, which works whether your
chat model is Anthropic or Hugging Face.

To point at a different embedding model/provider, change EMBEDDING_* in
.env -- nothing else in the ingestion/retrieval code needs to change.
"""
from app.ai.llm.provider import LLMProvider
from app.core.config import get_settings


def get_embedding_provider() -> LLMProvider:
    settings = get_settings()

    if settings.embedding_provider.lower() in ("mock", "none") or settings.llm_provider.lower() == "mock":
        from app.ai.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()

    if settings.embedding_provider.lower() == "huggingface":
        from app.ai.llm.huggingface_provider import HuggingFaceProvider

        api_key = settings.embedding_api_key or (
            settings.llm_api_key if settings.llm_provider.lower() == "huggingface" else ""
        )
        if not api_key:
            from app.ai.llm.mock_provider import MockLLMProvider
            return MockLLMProvider()

        provider = HuggingFaceProvider(embedding_model=settings.embedding_model)
        provider.api_key = api_key
        return provider

    from app.ai.llm.mock_provider import MockLLMProvider
    return MockLLMProvider()