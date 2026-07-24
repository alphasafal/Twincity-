"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    demo_mode: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./twinpilot.db"
    redis_url: str = "redis://localhost:6379/0"
    run_control_loop_in_api: bool = True
    worker_mode: bool = False
    jwt_secret: str = "twinpilot-dev-access-secret-change-me"
    jwt_refresh_secret: str = "twinpilot-dev-refresh-secret-change-me"
    jwt_access_minutes: int = 60
    jwt_refresh_days: int = 7
    validation_token_secret: str = "twinpilot-validation-token-secret-change-me"
    validation_token_ttl_seconds: int = 900
    web_origin: str = "http://localhost:3000"
    telemetry_ingest_token: str = "demo-telemetry-token"
    agent_provider: str = "deterministic"
    simulator_provider: str = "mock"
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
    # Stripe (optional — billing endpoints degrade gracefully when unset)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_starter: str | None = None
    stripe_price_optimize: str | None = None
    stripe_price_autonomy: str | None = None
    stripe_price_enterprise: str | None = None
    billing_success_url: str = "http://localhost:3000/settings/billing?status=success"
    billing_cancel_url: str = "http://localhost:3000/settings/billing?status=cancel"
    # Connector secret vault prefix (KMS/env backed refs)
    connector_secret_prefix: str = "env:"
    require_ws_auth: bool = True
    seed_on_startup: bool = True
    metrics_enabled: bool = True

    @field_validator("jwt_secret", "jwt_refresh_secret", "validation_token_secret")
    @classmethod
    def reject_default_secrets_in_production(cls, value: str, info) -> str:  # type: ignore[no-untyped-def]
        # Validated after full model via model_validator below when app_env known
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_production_secrets(self) -> None:
        if not self.is_production:
            return
        defaults = {
            "twinpilot-dev-access-secret-change-me",
            "twinpilot-dev-refresh-secret-change-me",
            "twinpilot-validation-token-secret-change-me",
            "demo-telemetry-token",
        }
        if self.jwt_secret in defaults or self.jwt_refresh_secret in defaults:
            raise RuntimeError("Default JWT secrets are not allowed when APP_ENV=production")
        if self.validation_token_secret in defaults:
            raise RuntimeError("Default validation token secret is not allowed in production")
        if self.demo_mode:
            raise RuntimeError("DEMO_MODE must be false when APP_ENV=production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production_secrets()
    return settings
