from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "secret-key-change-this")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

