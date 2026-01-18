"""
Application entry point for FastAPI server.

Run with:
    python run.py
    python -m app          # preferred: uses PORT from app/.env
    python -m uvicorn app.main:app --reload   # app loads app/.env; uvicorn default port 8000

The application loads app/.env via python-dotenv.
"""
import logging
import os
import uvicorn
from pathlib import Path

from dotenv import load_dotenv

from app.core.config import settings

# Load app/.env first
env_file = Path(__file__).parent / 'app' / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f'✓ Loaded environment variables from {env_file}')

# Get environment (default to development) - check system env first, then .env
# Note: Settings already loads from .env, but we load here for environment-specific files
env = os.environ.get('ENVIRONMENT', settings.ENVIRONMENT)

# Load environment-specific .env file if it exists (e.g., app/.env.development)
env_specific_file = Path(__file__).parent / 'app' / f'.env.{env}'
if env_specific_file.exists():
    load_dotenv(env_specific_file, override=True)
    print(f'✓ Loaded environment-specific variables from {env_specific_file} (overrides app/.env)')

# Get port from Settings (loads from .env file automatically via Pydantic)
port = settings.PORT

if __name__ == '__main__':
    logging.info(f'Starting FastAPI server in {env} mode')
    logging.info(f'Server will bind to 0.0.0.0:{port} (PORT from .env: {port})')
    print(f'🚀 Starting server on http://0.0.0.0:{port}')
    print(f'📝 PORT loaded from .env: {port}')
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=env == 'development',
        log_level="info"
    )
