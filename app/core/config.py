"""
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

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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


@lru_cache
def get_settings() -> Settings:
    """
    Cached so we don't re-read/re-validate env vars on every import.
    Equivalent to NestJS's singleton-scoped ConfigService.
    """
    return Settings()


settings = get_settings()
