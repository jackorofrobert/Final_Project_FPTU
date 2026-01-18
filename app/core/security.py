"""
Security utilities for session management.
"""
from fastapi import Request
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_current_user_id(request: Request) -> int | None:
    """
    Get current user ID from session.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID if authenticated, None otherwise
    """
    if "session" not in request.scope:
        return None
    session = request.session
    return session.get('user_id')


def get_current_user_email(request: Request) -> str | None:
    """
    Get current user email from session.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email if authenticated, None otherwise
    """
    if "session" not in request.scope:
        return None
    session = request.session
    return session.get('user_email')
