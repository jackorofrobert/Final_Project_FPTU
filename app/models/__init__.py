"""Database models for the application."""
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.models.email import Email
from app.models.prediction import Prediction
from app.models.prediction_detail import PredictionFeature, PredictionLink, SuspiciousSegment

__all__ = [
    'User', 
    'OAuthToken', 
    'Email', 
    'Prediction',
    'PredictionFeature',
    'PredictionLink',
    'SuspiciousSegment'
]
