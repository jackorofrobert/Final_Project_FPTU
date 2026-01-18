"""
Common Pydantic schemas for API responses.
"""
from pydantic import BaseModel, Field
from typing import Any, Optional, Generic, TypeVar

T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """Base success response schema."""
    success: bool = Field(True, description="Indicates the request was successful")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Optional success message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "message": "Operation completed successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Base error response schema."""
    success: bool = Field(False, description="Indicates the request failed")
    error: Optional[str] = Field(None, description="Error details or error code")
    message: Optional[str] = Field(None, description="User-friendly error message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "Invalid input provided"
            }
        }
