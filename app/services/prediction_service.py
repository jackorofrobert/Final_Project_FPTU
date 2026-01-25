"""
Prediction service for ML model integration.
"""
import json
import sys
from pathlib import Path

import pandas as pd
from joblib import load

from app.core.config import settings
from app.utils.logger import get_logger

# Add src directory to path to import existing ML code
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from src.text_cleaning import normalize_text, count_urls, detect_urgent_keywords, extract_sender_domain
from src.features import prepare_features, calculate_ensemble_score

logger = get_logger(__name__)

class PredictionService:
    """Service for ML model predictions."""
    
    _model = None
    _threshold = None
    _feature_cols = None
    
    @classmethod
    def _load_model(cls):
        """Lazy load the ML model."""
        if cls._model is None:
            model_path = settings.MODEL_PATH
            logger.info(f'Loading ML model from {model_path}')
            try:
                pkg = load(model_path)
                # The model is a full Pipeline (vectorizer + classifier)
                cls._model = pkg["model"]
                cls._threshold = float(pkg.get("threshold", 0.5))
                cls._feature_cols = pkg.get("feature_cols", [])
                model_version = cls.get_model_version()
                logger.info(f'ML model loaded successfully [model_path={model_path}] [version={model_version}] [threshold={cls._threshold}]')
            except Exception as e:
                logger.error(f'Failed to load ML model [model_path={model_path}]: {str(e)}', exc_info=True)
                raise
    
    @classmethod
    def predict(
        cls, 
        email_text: str,
        subject: str = None,
        has_attachment: int = None,
        links_count: int = None,
        sender_domain: str = None,
        urgent_keywords: int = None
    ) -> dict:
        """
        Predict if email is phishing.
        
        Args:
            email_text: Raw email text/body
            subject: Email subject (optional, combined with body)
            has_attachment: 0 or 1 (auto-detected if None)
            links_count: Number of links (auto-extracted if None)
            sender_domain: Sender's domain (auto-extracted if None)
            urgent_keywords: 0 or 1 (auto-detected if None)
            
        Returns:
            dict with keys: prediction (0 or 1), probability (float), threshold (float), features (dict)
        """
        logger.debug(f'Starting prediction [text_length={len(email_text)}]')
        cls._load_model()
        
        try:
            # Combine subject and body if subject provided
            raw_text = email_text
            if subject:
                raw_text = f"{subject} {email_text}"
            
            # Normalize text
            normalized_text = normalize_text(raw_text)
            logger.debug('Text normalized for prediction')
            
            # Auto-extract features if not provided
            if links_count is None:
                links_count = count_urls(raw_text)
                logger.debug(f'Auto-extracted links_count: {links_count}')
            
            if urgent_keywords is None:
                urgent_keywords = detect_urgent_keywords(raw_text)
                logger.debug(f'Auto-detected urgent_keywords: {urgent_keywords}')
            
            if sender_domain is None:
                sender_domain = extract_sender_domain(raw_text)
                logger.debug(f'Auto-extracted sender_domain: {sender_domain}')
            
            if has_attachment is None:
                has_attachment = 0  # Cannot detect from text
            
            # Prepare features DataFrame
            X = prepare_features(
                text=normalized_text,
                has_attachment=has_attachment,
                links_count=links_count,
                sender_domain=sender_domain,
                urgent_keywords=urgent_keywords
            )
            
            # Predict using pipeline
            proba = float(cls._model.predict_proba(X)[:, 1][0])
            
            # Calculate ensemble score
            ensemble_score = calculate_ensemble_score(
                model_proba=proba,
                urgent_keywords=urgent_keywords,
                links_count=links_count,
                sender_domain=sender_domain,
                has_attachment=has_attachment
            )
            
            # Use ensemble_score for final prediction
            pred = int(ensemble_score >= cls._threshold)
            
            logger.debug(f'Prediction completed: prediction={pred} probability={proba:.4f} ensemble_score={ensemble_score:.4f} threshold={cls._threshold}')
            
            return {
                'prediction': pred,
                'probability': round(proba, 6),
                'ensemble_score': round(ensemble_score, 6),
                'threshold': cls._threshold,
                'features': {
                    'links_count': links_count,
                    'has_attachment': has_attachment,
                    'urgent_keywords': urgent_keywords,
                    'sender_domain': sender_domain
                }
            }
        except Exception as e:
            logger.error(f'Error during prediction: {str(e)}', exc_info=True)
            raise
    
    @classmethod
    def get_model_version(cls) -> str:
        """Get model version from metadata if available."""
        try:
            metadata_path = Path(settings.MODEL_PATH).parent / 'metadata.json'
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    return metadata.get('version', 'unknown')
        except Exception:
            pass
        return 'unknown'
