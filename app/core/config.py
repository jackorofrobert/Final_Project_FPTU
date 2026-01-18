"""
Configuration classes using Pydantic BaseSettings.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


def get_env_file_path() -> str:
    """Get the absolute path to the .env file in app/ (app/.env)."""
    # This file is at: app/core/config.py -> parent.parent = app/
    env_file = Path(__file__).parent.parent / '.env'
    return str(env_file.resolve())


class Settings(BaseSettings):
    """Base configuration settings."""
    
    # Application settings
    SECRET_KEY: str = 'dev-secret-key-change-in-production'
    ENVIRONMENT: str = 'development'
    DEBUG: bool = True
    PORT: int = 5000
    
    # Database settings
    DATABASE_PATH: str = str(Path(__file__).parent.parent.parent / 'data' / 'app.db')
    
    # Gmail API settings
    GMAIL_CLIENT_ID: str = ''
    GMAIL_CLIENT_SECRET: str = ''
    GMAIL_REDIRECT_URI: str = 'http://localhost:5000/api/v1/auth/callback'
    
    # ML Model settings
    MODEL_PATH: str = str(Path(__file__).parent.parent.parent / 'models' / 'model.joblib')
    
    # Session settings
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    
    # CORS settings (specific origins required when allow_credentials=True; wildcard "*" is invalid)
    CORS_ORIGINS: List[str] = [
        'http://localhost:5001',
        'http://0.0.0.0:5001',
        'http://127.0.0.1:5001',
        'http://localhost:5000',
        'http://0.0.0.0:5000',
        'http://127.0.0.1:5000',
        'http://localhost:3000',
        'http://localhost:8080',
        'http://127.0.0.1:5500',
    ]
    
    # Logging settings
    LOG_LEVEL: str = 'INFO'
    LOG_FILE: str | None = None
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB default
    LOG_BACKUP_COUNT: int = 5
    
    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
