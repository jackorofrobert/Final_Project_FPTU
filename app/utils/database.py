"""
Database connection and initialization utilities.
DEPRECATED: Use app.db.session instead.
This file is kept for backward compatibility but redirects to the new location.
"""
from app.db.session import get_db, init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Re-export for backward compatibility
__all__ = ['get_db', 'init_db']
