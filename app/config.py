"""
Configuration classes for different environments.
"""

import os
from pathlib import Path


class Config:
    """Base configuration class."""

    # Application settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # Database settings
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or str(
        Path(__file__).parent.parent / "data" / "app.db"
    )

    # Mail API settings (replaces Gmail)
    MAIL_API_BASE_URL = os.environ.get("MAIL_API_BASE_URL") or "http://localhost:8095"
    MAIL_API_TOKEN = os.environ.get("MAIL_API_TOKEN") or ""

    # ML Model settings
    MODEL_PATH = os.environ.get("MODEL_PATH") or str(
        Path(__file__).parent.parent / "models" / "model.joblib"
    )

    # Session settings
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # CORS settings
    CORS_ORIGINS = []

    # Logging settings
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE") or None  # None for console only
    LOG_MAX_BYTES = int(
        os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024)
    )  # 10MB default
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    LOG_LEVEL = "DEBUG"
    LOG_FILE = None  # Console logging in development


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    DATABASE_PATH = ":memory:"  # Use in-memory database for testing


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    LOG_LEVEL = "INFO"
    LOG_FILE = os.environ.get("LOG_FILE") or str(
        Path(__file__).parent.parent / "logs" / "app.log"
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
