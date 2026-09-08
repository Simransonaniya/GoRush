"""
Centralized, typed application configuration.
All values are read from environment variables (.env in local dev).
Never hardcode secrets here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "gorush-ai-backend"
    app_env: str = "development"
    api_version: str = "v1"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://gorush:gorush@localhost:5432/gorush_chat"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # LLM
    llm_provider: str = "anthropic"
    llm_api_key: str = ""
    llm_model_primary: str = "claude-sonnet-4-6"
    llm_model_fallback: str = "claude-haiku-4-5"
    llm_timeout_seconds: int = 20
    llm_max_retries: int = 2

    # GoRush upstream
    gorush_ride_api_base_url: str = "https://mock.gorush.internal/ride"
    gorush_payment_api_base_url: str = "https://mock.gorush.internal/payment"
    gorush_support_api_base_url: str = "https://mock.gorush.internal/support"
    gorush_safety_api_base_url: str = "https://mock.gorush.internal/safety"
    gorush_use_mocks: bool = True

    # Rate limiting
    rate_limit_per_user_per_min: int = 30
    rate_limit_per_ip_per_min: int = 60

    # Guardrails
    max_tool_calls_per_turn: int = 5
    max_orchestration_steps: int = 8

    # Set true to use an in-memory fake Redis (via the `fakeredis` package)
    # instead of a real Redis server -- useful for local dev when you don't
    # want to run Docker/Redis just to test the app. Rate limiting,
    # idempotency, and caching all still work, just non-persistent and
    # single-process only. Never use this in production.
    use_fake_redis: bool = False

    # Embeddings (used for RAG knowledge base regardless of chat LLM_PROVIDER,
    # since Anthropic has no first-party embeddings endpoint). Defaults to a
    # free Hugging Face sentence-transformers model.
    embedding_provider: str = "huggingface"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384  # must match embedding_model's output dimension
    embedding_api_key: str = ""  # falls back to llm_api_key if empty and provider is huggingface
    embedding_chunk_size_words: int = 220
    embedding_chunk_overlap_words: int = 40


@lru_cache
def get_settings() -> Settings:
    return Settings()