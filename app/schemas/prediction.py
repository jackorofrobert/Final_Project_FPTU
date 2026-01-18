"""
Pydantic schemas for prediction endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class PredictionRequest(BaseModel):
    """Prediction request schema."""
    email_text: str = Field(..., description="Email content to analyze for phishing detection", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "email_text": "Dear customer, please verify your account by clicking this link: http://suspicious-site.com/verify"
            }
        }


class PredictionResponse(BaseModel):
    """Prediction response schema."""
    prediction: int = Field(..., description="Prediction result: 0 for benign, 1 for phishing", ge=0, le=1)
    probability: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    threshold: float = Field(..., description="Threshold value used for classification", ge=0.0, le=1.0)
    email_id: Optional[int] = Field(None, description="ID of the email record if saved")
    is_phishing: bool = Field(..., description="Boolean indicating if email is classified as phishing")

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 1,
                "probability": 0.95,
                "threshold": 0.5,
                "email_id": 123,
                "is_phishing": True
            }
        }


class PredictionDetailResponse(BaseModel):
    """Detailed prediction response schema."""
    prediction: Dict[str, Any] = Field(..., description="Prediction record with metadata")
    result: Dict[str, Any] = Field(..., description="Prediction result details")
    is_phishing: bool = Field(..., description="Boolean indicating if email is classified as phishing")

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": {
                    "id": 1,
                    "email_id": 123,
                    "prediction": 1,
                    "probability": 0.95,
                    "model_version": "1.0.0",
                    "created_at": "2024-01-15T10:40:00Z"
                },
                "result": {
                    "prediction": 1,
                    "probability": 0.95,
                    "threshold": 0.5
                },
                "is_phishing": True
            }
        }
