from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinkedIn Pulse Monitor"
    database_url: str = "sqlite:///./linkedin_pulse.db"
    app_base_url: str = "http://localhost:8000"
    timezone: str = "America/New_York"
    apify_token: str | None = None
    apify_actor_id: str | None = None
    apify_task_id: str | None = None
    apify_default_dataset_id: str | None = None
    ai_provider: str = "mock"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    ai_summary_model: str | None = None
    scrape_interval_hours: int = 12
    daily_report_hour_local: int = 7
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
