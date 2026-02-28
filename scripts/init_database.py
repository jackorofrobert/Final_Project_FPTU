#!/usr/bin/env python3
"""
Database initialization and migration script.
Run this to set up or update the database schema.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import init_db
from app.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
    """Initialize or migrate database."""
    try:
        logger.info("Starting database initialization...")
        init_db()
        logger.info("Database initialization completed successfully!")
        print("✓ Database initialized successfully")
        return 0
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        print(f"✗ Database initialization failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
