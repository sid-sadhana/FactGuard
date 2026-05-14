import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str:
    app_env = os.getenv("APP_ENV", "local").lower()
    candidate = Path(f".env.{app_env}")
    if candidate.exists():
        return str(candidate)
    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FactGuard API"
    environment: str = "development"
    log_level: str = "INFO"

    cors_origins: list[str] = ["http://localhost:3000"]

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen3-vl"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_api_key: str | None = None

    tavily_api_key: str | None = None
    tavily_search_depth: str = "advanced"
    tavily_max_results: int = 5

    storage_dir: Path = Path("./.factguard-storage")
    max_upload_mb: int = 500

    rag_chunk_size: int = 900
    rag_chunk_overlap: int = 150
    rag_top_k: int = 4
    context_budget_chars: int = 6000

    enable_ragas: bool = False
    use_web_base_loader: bool = True

    use_qdrant: bool = False
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "factguard"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
