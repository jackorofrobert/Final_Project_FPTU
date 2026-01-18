"""
Run uvicorn with PORT from app/.env.

Usage: python -m app

Loads app/.env via python-dotenv, then starts uvicorn with port=settings.PORT and reload=True.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

import uvicorn

from app.core.config import settings

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=settings.PORT,
        reload=True,
    )
