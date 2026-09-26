"""Application configuration settings using pydantic-settings."""

import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for IP-SAKTI Sahayak."""

    # Project Information
    PROJECT_NAME: str = "IP-SAKTI Sahayak"
    PROJECT_DESCRIPTION: str = (
        "A multilingual, RAG-based, source-cited AI decision support assistant "
        "for Intellectual Property Rights (IPR) and regulatory guidance related to Ayurveda."
    )
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database Configuration
    # Supports PostgreSQL (production/docker) or automatic SQLite fallback for zero-config local runs
    DATABASE_URL: str = "sqlite:///./ip_sakti.db"
    DB_ECHO: bool = False

    # Qdrant Vector Store Configuration
    # If running Docker or Qdrant Cloud: http://localhost:6333
    # If no server is running: defaults to local directory "./qdrant_storage" or ":memory:"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "ayurveda_ipr_documents"
    QDRANT_LOCAL_PATH: str = "./qdrant_storage"

    # LLM Service Configuration
    # Supported providers: 'mock', 'gemini', 'openai'
    # 'mock' provides fully grounded, deterministic responses using retrieved chunks without any external API keys
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1

    # Embedding Service Configuration
    # Supported providers: 'mock', 'local', 'openai'
    # 'mock' produces deterministic 384-dimension embeddings for zero-dependency local testing
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 384

    # Security & CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    SECRET_KEY: str = "ipsakti_temporary_dev_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # RAG Retrieval Settings
    DEFAULT_RETRIEVAL_LIMIT: int = 5
    SIMILARITY_THRESHOLD: float = 0.35

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


# Singleton instance of application settings
settings = Settings()
