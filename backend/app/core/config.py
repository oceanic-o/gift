import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Gift Recommendation System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://giftuser:giftpassword@localhost:5432/giftdb"
    DATABASE_URL_SYNC: str = "postgresql://giftuser:giftpassword@localhost:5432/giftdb"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_RAG_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_RAG_CHAT_MODEL: str = "gpt-4o"

    # Web search (optional for RAG fallback)
    WEB_SEARCH_PROVIDER: str = ""
    WEB_SEARCH_API_KEY: str = ""
    WEB_SEARCH_ENDPOINT: str = ""
    WEB_SEARCH_LIMIT: int = 5

    # Recommendation Engine
    CONTENT_WEIGHT: float = 0.6
    COLLABORATIVE_WEIGHT: float = 0.4
    KNOWLEDGE_WEIGHT: float = 0.15
    TOP_N_RECOMMENDATIONS: int = 10

    # Feature Boost Weights (default values)
    BOOST_WEIGHT_HOBBIES: float = 0.35
    BOOST_WEIGHT_OCCASION: float = 0.18
    BOOST_WEIGHT_RELATIONSHIP: float = 0.12
    BOOST_WEIGHT_AGE: float = 0.08
    BOOST_WEIGHT_GENDER: float = 0.06
    BOOST_WEIGHT_PRICE: float = 0.05

    # Evaluation / metrics
    # If enabled, the backend will compute and store an evaluation run at startup.
    # Good for demoing charts in the frontend without manual admin actions.
    AUTO_EVALUATE_ON_STARTUP: bool = False

    # Admin
    ADMIN_EMAIL: str = "admin@giftapp.com"
    ADMIN_PASSWORD: str = "AdminSecurePass123!"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    @field_validator("CONTENT_WEIGHT", "COLLABORATIVE_WEIGHT", mode="before")
    @classmethod
    def validate_weights(cls, v: float) -> float:
        v = float(v)
        if not 0.0 <= v <= 1.0:
            raise ValueError("Weights must be between 0 and 1")
        return v

    @field_validator("OPENAI_CHAT_MODEL", "OPENAI_RAG_CHAT_MODEL", mode="before")
    @classmethod
    def normalize_chat_model(cls, v: str) -> str:
        if v is None:
            return "gpt-4o"
        raw = str(v).strip()
        lowered = raw.lower()
        aliases = {
            "gpt-40": "gpt-4o",
            "gpt4o": "gpt-4o",
            "gpt_4o": "gpt-4o",
        }
        return aliases.get(lowered, raw)

    @field_validator("OPENAI_EMBEDDING_MODEL", "OPENAI_RAG_EMBEDDING_MODEL", mode="before")
    @classmethod
    def normalize_embedding_model(cls, v: str) -> str:
        if v is None:
            return "text-embedding-3-small"
        raw = str(v).strip()
        lowered = raw.lower()
        aliases = {
            "embedding-3-small": "text-embedding-3-small",
            "embedding-3-large": "text-embedding-3-large",
        }
        return aliases.get(lowered, raw)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
