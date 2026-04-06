"""Database models for the application."""
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.models.email import Email
from app.models.prediction import Prediction
from app.models.prediction_detail import PredictionFeature, PredictionLink, SuspiciousSegment
from app.models.fetch_log import FetchLog
from app.models.analysis_log import AnalysisLog
from app.models.vt_link_check import VTLinkCheck, VTDailyUsage
from app.models.vt_scan_log import VTScanLog

__all__ = [
    'User', 
    'OAuthToken', 
    'Email', 
    'Prediction',
    'PredictionFeature',
    'PredictionLink',
    'SuspiciousSegment',
    'FetchLog',
    'AnalysisLog',
    'VTLinkCheck',
    'VTDailyUsage',
    'VTScanLog',
]
