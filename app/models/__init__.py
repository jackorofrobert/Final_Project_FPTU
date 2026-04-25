"""Database models for the application."""
from app.models.user import User
from app.models.oauth_token import OAuthToken
from app.models.email import Email
from app.models.email_attachment import EmailAttachment
from app.models.prediction import Prediction
from app.models.prediction_detail import PredictionFeature, PredictionLink, SuspiciousSegment
from app.models.fetch_log import FetchLog
from app.models.analysis_log import AnalysisLog
from app.models.vt_link_check import VTLinkCheck, VTDailyUsage
from app.models.vt_attachment_check import VTAttachmentCheck
from app.models.vt_scan_log import VTScanLog
from app.models.translation_log import TranslationLog

__all__ = [
    'User',
    'OAuthToken',
    'Email',
    'EmailAttachment',
    'Prediction',
    'PredictionFeature',
    'PredictionLink',
    'SuspiciousSegment',
    'FetchLog',
    'AnalysisLog',
    'VTLinkCheck',
    'VTAttachmentCheck',
    'VTDailyUsage',
    'VTScanLog',
    'TranslationLog',
]
