"""
Pydantic schemas for history endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class HistoryListResponse(BaseModel):
    """History list response schema."""
    predictions: List[Dict[str, Any]] = Field(..., description="List of prediction history records")
    limit: int = Field(..., description="Maximum number of predictions returned")
    offset: int = Field(..., description="Number of predictions skipped")

    class Config:
        json_schema_extra = {
            "example": {
                "predictions": [
                    {
                        "id": 1,
                        "email_id": 123,
                        "prediction": 1,
                        "probability": 0.95,
                        "model_version": "1.0.0",
                        "created_at": "2024-01-15T10:40:00Z",
                        "email": {
                            "id": 123,
                            "subject": "Verify Your Account",
                            "sender": "noreply@example.com"
                        }
                    }
                ],
                "limit": 100,
                "offset": 0
            }
        }


class HistoryDetail(BaseModel):
    """History detail response schema."""
    id: int = Field(..., description="Prediction record ID")
    email_id: int = Field(..., description="ID of the email that was analyzed")
    prediction: int = Field(..., description="Prediction result: 0 for benign, 1 for phishing", ge=0, le=1)
    probability: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    model_version: Optional[str] = Field(None, description="Version of the ML model used")
    created_at: str = Field(..., description="ISO timestamp when prediction was created")
    email: Optional[Dict[str, Any]] = Field(None, description="Email details associated with this prediction")
