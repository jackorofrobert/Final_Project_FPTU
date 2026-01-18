"""
Pydantic schemas for authentication endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional


class AuthStatus(BaseModel):
    """Authentication status response schema."""
    authenticated: bool = Field(..., description="Whether the user is authenticated")
    user_id: Optional[int] = Field(None, description="User ID if authenticated")
    user_email: Optional[str] = Field(None, description="User email if authenticated")

    class Config:
        json_schema_extra = {
            "example": {
                "authenticated": True,
                "user_id": 1,
                "user_email": "user@example.com"
            }
        }


class OAuthConnect(BaseModel):
    """OAuth2 connection initiation response schema."""
    authorization_url: str = Field(..., description="URL to redirect user for OAuth2 authorization")
    state: str = Field(..., description="OAuth2 state parameter for CSRF protection")

    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
                "state": "random_state_string_12345"
            }
        }


class OAuthCallback(BaseModel):
    """OAuth2 callback request schema."""
    code: str = Field(..., description="Authorization code from OAuth2 provider")
    state: str = Field(..., description="State parameter to verify CSRF protection")
