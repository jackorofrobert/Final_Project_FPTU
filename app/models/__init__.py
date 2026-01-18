"""Database models for the application."""
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.models.email import Email
from app.models.prediction import Prediction

__all__ = ['User', 'OAuthToken', 'Email', 'Prediction']
