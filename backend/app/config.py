from functools import lru_cache
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = "AI-Powered Placement Intelligence System"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "dev_secret_key_antigravity_placement_system_2026_super_secure_key"
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        import json
        try:
            return json.loads(v)
        except Exception:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]

    # PostgreSQL Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "placement_db"
    DB_SCHEMA: str = "placement_app_v2"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/placement_db"

    # Database Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 15

    # File Storage Settings
    RESUME_STORAGE_DIR: str = "backend/uploads/resumes"
    REPORT_STORAGE_DIR: str = "backend/uploads/reports"
    MAX_UPLOAD_SIZE_BYTES: int = 5242880  # 5 MB

    # AI Configuration (Dynamic & Independently Configurable)
    AI_PROVIDER: str = "mock"  # "mock", "gemini", or "openai"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_TIMEOUT_SECONDS: int = 45
    AI_MAX_OUTPUT_TOKENS: int = 8192
    AI_TEMPERATURE: float = 0.0
    AI_MOCK_DELAY_MS: int = 250

    # Sandboxed Code Execution Configuration
    CODE_SANDBOX_MODE: str = "isolated_subprocess"  # "isolated_subprocess", "piston", or "judge0"
    CODE_SANDBOX_API_URL: str = ""
    CODE_SANDBOX_TIMEOUT_SECONDS: float = 3.0
    CODE_SANDBOX_MEMORY_MB: int = 128
    CODE_SANDBOX_MAX_OUTPUT_BYTES: int = 65536


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()

