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
                "user_email": "archive@spktfpt.online",
            }
        }


class MailConnect(BaseModel):
    """Request schema for mail API login."""

    email: str = Field(..., description="Mailbox email address")
    password: str = Field(..., description="Mailbox password")
    label: str = Field(
        "phishing-detector", description="Token label (e.g. device name)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "archive@spktfpt.online",
                "password": "your-mailbox-password",
                "label": "phishing-detector",
            }
        }


# Keep OAuthConnect/OAuthCallback as aliases so existing imports don't break
# (they are not used by the new auth endpoints but may be imported elsewhere)
class OAuthConnect(BaseModel):
    """Deprecated – kept for backwards-compat only."""

    authorization_url: str = Field(..., description="OAuth2 authorization URL")
    state: str = Field(..., description="OAuth2 state parameter")


class OAuthCallback(BaseModel):
    """Deprecated – kept for backwards-compat only."""

    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter")
