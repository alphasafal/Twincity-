"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    demo_mode: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./twinpilot.db"
    jwt_secret: str = "twinpilot-dev-access-secret-change-me"
    jwt_refresh_secret: str = "twinpilot-dev-refresh-secret-change-me"
    jwt_access_minutes: int = 60
    jwt_refresh_days: int = 7
    web_origin: str = "http://localhost:3000"
    telemetry_ingest_token: str = "demo-telemetry-token"
    agent_provider: str = "deterministic"
    simulator_provider: str = "mock"
    # Hackathon default: show real EnergyPlus experiment artifacts on the dashboard.
    # mock = legacy synthetic twin KPIs (never selected silently in hackathon .env).
    data_mode: str = "energyplus"
    hackathon_mode: bool = True
    results_dir: str | None = None
    experiment_scenario: str = "default"
    control_loop_enabled: bool = True
    control_interval_seconds: int = 5
    default_building_timezone: str = "Asia/Kolkata"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    energyplus_home: str | None = None
    energyplus_model_path: str | None = None
    energyplus_weather_path: str | None = None
    rate_limit_auth_per_minute: int = 30
    rate_limit_assistant_per_minute: int = 20
    cors_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
