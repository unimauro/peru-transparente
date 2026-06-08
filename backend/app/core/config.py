"""Configuración central de la API."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PT_", extra="ignore")

    app_name: str = "Perú Transparente API"
    environment: str = "dev"
    debug: bool = True

    # Postgres
    database_url: str = "postgresql+asyncpg://pt:pt@localhost:5432/peru_transparente"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "peru_transparente"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS — GitHub Pages + dev
    cors_origins: list[str] = [
        "http://localhost:5173",
        "https://unimauro.github.io",
    ]

    # IA (intercambiable). Las claves se inyectan por entorno.
    llm_provider: str = "claude"  # claude | openai | gemini
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # OAuth GitHub
    github_client_id: str | None = None
    github_client_secret: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
