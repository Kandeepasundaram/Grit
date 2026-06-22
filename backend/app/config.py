"""Backend configuration via environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg://grit:grit@localhost:5432/grit"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT signing (license)
    license_private_key_path: str = str(Path(__file__).parent.parent / "license_private.pem")

    # OAuth proxy (GitHub)
    github_client_id: str = ""
    github_client_secret: str = ""

    # OAuth proxy (Google)
    google_client_id: str = ""
    google_client_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # App
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    license_expire_days: int = 365

    # License tiers
    free_profile_limit: int = 5

    class Config:
        env_file = ".env"
        env_prefix = "GRIT_"


settings = Settings()
