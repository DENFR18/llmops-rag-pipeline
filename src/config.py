from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # LLM
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 1024

    # Embeddings
    embeddings_provider: Literal["voyage", "openai"] = "voyage"
    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Vector store
    neon_database_url: str = ""
    pgvector_table: str = "rag_chunks"
    pgvector_dim: int = 1024

    # Retrieval
    rag_top_k: int = Field(default=5, ge=1, le=50)
    rag_chunk_size: int = Field(default=512, ge=64, le=4096)
    rag_chunk_overlap: int = Field(default=64, ge=0, le=512)

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
