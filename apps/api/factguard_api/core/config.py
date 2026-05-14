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
    ollama_llm_model: str = "gemma4:e4b"
    ollama_api_key: str | None = None

    # Qdrant Cloud Inference embedding model (server-side, no local Ollama embed).
    embed_model: str = "sentence-transformers/all-minilm-l6-v2"
    embed_dim: int = 384

    # Web search: DuckDuckGo via the `ddgs` library — free, no API key.
    # Set DDGS_PROXY to a single proxy URL (http://user:pass@host:port or
    # socks5://host:port) if you hit rate limits.
    ddgs_proxy: str | None = None
    search_max_results: int = 5
    search_region: str = "wt-wt"  # "worldwide" — see ddgs docs for codes

    storage_dir: Path = Path("./.factguard-storage")
    max_upload_mb: int = 500

    rag_chunk_size: int = 900
    rag_chunk_overlap: int = 150
    rag_top_k: int = 4
    context_budget_chars: int = 6000

    enable_ragas: bool = False
    use_web_base_loader: bool = True

    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_prefix: str = "factguard"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
