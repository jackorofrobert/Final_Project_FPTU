"""
Pydantic schemas for prediction endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal


class PredictionRequest(BaseModel):
    """Prediction request schema."""
    email_text: str = Field(..., description="Email content to analyze for phishing detection", min_length=1)
    subject: Optional[str] = Field(None, description="Email subject line (combined with body for analysis)")
    has_attachment: Optional[int] = Field(None, description="Whether email has attachment (0 or 1)", ge=0, le=1)
    links_count: Optional[int] = Field(None, description="Number of links in email (auto-extracted if not provided)", ge=0)
    sender_domain: Optional[str] = Field(None, description="Sender's email domain (auto-extracted if not provided)")
    urgent_keywords: Optional[int] = Field(None, description="Whether email contains urgent keywords (0 or 1, auto-detected if not provided)", ge=0, le=1)

    class Config:
        json_schema_extra = {
            "example": {
                "email_text": "Dear customer, please verify your account by clicking this link: http://suspicious-site.com/verify",
                "subject": "Urgent: Account Verification Required",
                "has_attachment": 0,
                "links_count": 1,
                "sender_domain": "suspicious-site.com",
                "urgent_keywords": 1
            }
        }


class PredictionResponse(BaseModel):
    """Prediction response schema."""
    prediction: int = Field(..., description="Prediction result: 0 for benign, 1 for phishing/suspicious", ge=0, le=1)
    classification: str = Field(..., description="Classification level: LEGITIMATE, SUSPICIOUS, or PHISHING")
    probability: float = Field(..., description="Model confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    ensemble_score: Optional[float] = Field(None, description="Ensemble score combining model + feature risks (0.0 to 1.0)", ge=0.0, le=1.0)
    threshold: float = Field(..., description="Threshold value used for classification", ge=0.0, le=1.0)
    suspicious_margin: Optional[float] = Field(None, description="Margin above threshold for suspicious classification", ge=0.0, le=1.0)
    email_id: Optional[int] = Field(None, description="ID of the email record if saved")
    is_phishing: bool = Field(..., description="Boolean indicating if email is classified as phishing (PHISHING level)")
    is_suspicious: Optional[bool] = Field(None, description="Boolean indicating if email is classified as suspicious (SUSPICIOUS level)")
    features: Optional[Dict[str, Any]] = Field(None, description="Features used for prediction")

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 1,
                "classification": "SUSPICIOUS",
                "probability": 0.85,
                "ensemble_score": 0.42,
                "threshold": 0.3,
                "suspicious_margin": 0.2,
                "email_id": 123,
                "is_phishing": False,
                "is_suspicious": True,
                "features": {
                    "links_count": 2,
                    "has_attachment": 0,
                    "urgent_keywords": 1,
                    "sender_domain": "suspicious-site.com"
                }
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
