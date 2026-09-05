"""
<<<<<<< HEAD
Centralized, typed application configuration.
All values are read from environment variables (.env in local dev).
Never hardcode secrets here.
"""
=======
Central application configuration.

Why this exists:
NestJS uses a ConfigModule that validates env vars at startup and injects
a typed config object everywhere. We do the same thing here with
pydantic-settings: it reads environment variables (or a .env file),
validates their types, and gives us a single typed `settings` object
to import anywhere in the app. If a required env var is missing or the
wrong type, the app refuses to start -- which is exactly what we want
for production safety.
"""

>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
<<<<<<< HEAD
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
=======
    # --- App ---
    APP_NAME: str = "GoRush AI Chatbot Backend"
    ENV: str = "development"  # development | staging | production
    API_V1_PREFIX: str = "/v1"
    DEBUG: bool = True

    # --- Security ---
    JWT_SECRET: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Database (Postgres) ---
    DATABASE_URL: str = (
        "postgresql+asyncpg://gorush:gorush@localhost:5432/gorush"
    )

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- LLM Gateway ---
    LLM_PROVIDER: str = "mock"  # mock | anthropic | openai
    LLM_MODEL: str = "claude-sonnet-4-6"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd


@lru_cache
def get_settings() -> Settings:
<<<<<<< HEAD
    return Settings()
=======
    """
    Cached so we don't re-read/re-validate env vars on every import.
    Equivalent to NestJS's singleton-scoped ConfigService.
    """
    return Settings()


settings = get_settings()
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
