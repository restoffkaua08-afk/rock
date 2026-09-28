# ruff: isort: skip_file
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    perplexity_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    rock_mode: str = "mock"
    rock_db_path: str = ".rock/sessions.db"
    rock_max_retries: int = 2
    rock_timeout_seconds: float = 60
    rock_max_parallel: int = 5
    rock_max_cost: float | None = None
    rock_council_models: str | None = None
    rock_council_protocol: str = "parallel"
    rock_council_rounds: int = 1
    rock_council_critic_model: str | None = None
    rock_council_synthesizer_model: str | None = None
    rock_council_verifier_model: str | None = None

    rock_openai_model: str = "openai/gpt-5.3"
    rock_anthropic_model: str = "anthropic/claude-sonnet-5"
    rock_deepseek_model: str = "deepseek-chat"
    rock_perplexity_model: str = "perplexity/sonar"
    rock_gemini_model: str = "gemini/gemini-2.5-flash"
    rock_ollama_model: str = "ollama/llama3.2:3b"

    rock_superpowers_path: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
