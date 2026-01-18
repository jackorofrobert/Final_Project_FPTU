"""
Dependency injection for FastAPI routes.
"""
from fastapi import Depends, HTTPException, status, Request
from app.core.security import get_current_user_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_current_user_dependency(request: Request):
    """Get current authenticated user ID from session."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_id


def get_optional_user_dependency(request: Request):
    """Get current user ID if authenticated, otherwise None."""
    return get_current_user_id(request)
