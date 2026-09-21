"""SolutionBridge Core Configuration Module."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    APP_NAME: str = "SolutionBridge"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Explicit Database Configuration (Primary: MySQL 8, Optional: SQLite)
    DATABASE_URL: str = "mysql+pymysql://root:rootpassword@localhost:3306/solutionbridge"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Security
    SECRET_KEY: str = "solutionbridge-dev-secret-key-32-chars-minimum-hash"
    API_KEY_HEADER: str = "X-API-Key"

    # Machine Learning paths
    ML_ARTIFACTS_DIR: str = str(BASE_DIR / "ml" / "artifacts")

    # Optional OpenAI configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Dashboard & Service URLs
    STREAMLIT_PORT: int = 8501
    BACKEND_API_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_sqlite(self) -> bool:
        """Check if explicitly configured to use SQLite."""
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
