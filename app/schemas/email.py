"""
Pydantic schemas for email endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class EmailFetchRequest(BaseModel):
    """Email fetch request schema."""
    max_results: int = Field(
        50,
        ge=1,
        le=500,
        description="Maximum number of emails to fetch from Gmail (1-500)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_results": 50
            }
        }


class EmailFetchResponse(BaseModel):
    """Email fetch response schema."""
    count: int = Field(..., description="Number of emails fetched and stored")
    emails: List[Dict[str, Any]] = Field(..., description="List of fetched email objects")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 3,
                "emails": [
                    {
                        "id": 1,
                        "gmail_message_id": "abc123",
                        "subject": "Test Email",
                        "sender": "sender@example.com",
                        "recipient": "recipient@example.com"
                    }
                ]
            }
        }


class EmailListResponse(BaseModel):
    """Email list response schema."""
    emails: List[Dict[str, Any]] = Field(..., description="List of email objects")
    limit: int = Field(..., description="Maximum number of emails returned")
    offset: int = Field(..., description="Number of emails skipped")

    class Config:
        json_schema_extra = {
            "example": {
                "emails": [
                    {
                        "id": 1,
                        "subject": "Test Email",
                        "sender": "sender@example.com",
                        "prediction": None
                    }
                ],
                "limit": 50,
                "offset": 0
            }
        }


class EmailDetail(BaseModel):
    """Email detail response schema."""
    id: int = Field(..., description="Email record ID")
    user_id: int = Field(..., description="ID of the user who owns this email")
    gmail_message_id: str = Field(..., description="Gmail message ID")
    subject: Optional[str] = Field(None, description="Email subject line")
    sender: Optional[str] = Field(None, description="Email sender address")
    recipient: Optional[str] = Field(None, description="Email recipient address")
    body: Optional[str] = Field(None, description="Email body content")
    received_at: Optional[str] = Field(None, description="ISO timestamp when email was received")
    fetched_at: Optional[str] = Field(None, description="ISO timestamp when email was fetched")
    created_at: Optional[str] = Field(None, description="ISO timestamp when email record was created")
    prediction: Optional[Dict[str, Any]] = Field(None, description="Latest prediction result for this email")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "gmail_message_id": "abc123",
                "subject": "Important: Verify Your Account",
                "sender": "noreply@example.com",
                "recipient": "user@example.com",
                "body": "Please verify your account...",
                "received_at": "2024-01-15T10:30:00Z",
                "fetched_at": "2024-01-15T10:35:00Z",
                "created_at": "2024-01-15T10:35:00Z",
                "prediction": {
                    "id": 1,
                    "prediction": 1,
                    "probability": 0.95,
                    "is_phishing": True
                }
            }
        }
