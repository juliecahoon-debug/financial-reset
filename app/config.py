from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
import sys

load_dotenv()


def _require_env(key: str, default: str | None = None) -> str:
    """Return env var value, or default in development. Warn loudly if using insecure default."""
    value = os.getenv(key, default)
    if value == default and default is not None:
        print(
            f"WARNING: {key} is not set in environment. Using insecure default. "
            f"Set {key} in your .env file before deploying to production.",
            file=sys.stderr,
        )
    return value or ""


class Settings(BaseSettings):
    """Application settings — all values should come from environment variables."""

    # Database — required; no safe default
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./financial_reset.db")

    # JWT — insecure default triggers a startup warning
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE-THIS-SECRET-KEY-BEFORE-PRODUCTION")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))

    # CORS — comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8081,http://localhost:19006"
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Warn on startup if using insecure JWT secret
if settings.JWT_SECRET_KEY in ("CHANGE-THIS-SECRET-KEY-BEFORE-PRODUCTION", "secret-key-change-this", ""):
    print(
        "SECURITY WARNING: JWT_SECRET_KEY is not set or is using an insecure default. "
        "Set a strong random secret in your .env file before deploying.",
        file=sys.stderr,
    )
