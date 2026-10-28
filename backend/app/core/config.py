"""Application settings and environment variable configuration."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Central configuration for SaagarDrishti application."""

    # Application settings
    APP_NAME: str = "SaagarDrishti"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Data Source Placeholders (INCOIS, NOAA, etc.)
    INCOIS_API_BASE_URL: Optional[str] = None
    INCOIS_API_KEY: Optional[str] = None

    # LLM / Multi-Agent Placeholders
    AGENT_MODEL_NAME: Optional[str] = None
    AGENT_API_KEY: Optional[str] = None

    # Storage and paths
    DATA_DIR: str = "data/"
    DATABASE_URL: Optional[str] = None

    # Copernicus Marine Data Store (CMEMS)
    COPERNICUSMARINE_SERVICE_USERNAME: Optional[str] = None
    COPERNICUSMARINE_SERVICE_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
