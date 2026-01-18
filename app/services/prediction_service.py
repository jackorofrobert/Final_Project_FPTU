"""
Prediction service for ML model integration.
"""
import json
import sys
from pathlib import Path

from joblib import load

from app.core.config import settings
from app.utils.logger import get_logger

# Add src directory to path to import existing ML code
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from src.text_cleaning import normalize_text
from src.features import FeatureBuilder

logger = get_logger(__name__)

class PredictionService:
    """Service for ML model predictions."""
    
    _model = None
    _feature_builder = None
    _threshold = None
    
    @classmethod
    def _load_model(cls):
        """Lazy load the ML model."""
        if cls._model is None:
            model_path = settings.MODEL_PATH
            logger.info(f'Loading ML model from {model_path}')
            try:
                pkg = load(model_path)
                cls._feature_builder = pkg["feature_builder"]
                cls._model = pkg["model"]
                cls._threshold = float(pkg.get("threshold", 0.5))
                model_version = cls.get_model_version()
                logger.info(f'ML model loaded successfully [model_path={model_path}] [version={model_version}] [threshold={cls._threshold}]')
            except Exception as e:
                logger.error(f'Failed to load ML model [model_path={model_path}]: {str(e)}', exc_info=True)
                raise
    
    @classmethod
    def predict(cls, email_text: str) -> dict:
        """
        Predict if email is phishing.
        
        Args:
            email_text: Raw email text/body
            
        Returns:
            dict with keys: prediction (0 or 1), probability (float), threshold (float)
        """
        logger.debug(f'Starting prediction [text_length={len(email_text)}]')
        cls._load_model()
        
        try:
            # Normalize text
            normalized_text = normalize_text(email_text)
            logger.debug('Text normalized for prediction')
            
            # Extract features
            X = cls._feature_builder.transform([normalized_text])
            logger.debug('Features extracted for prediction')
            
            # Predict
            proba = float(cls._model.predict_proba(X)[:, 1][0])
            pred = int(proba >= cls._threshold)
            
            logger.debug(f'Prediction completed: prediction={pred} probability={proba:.4f} threshold={cls._threshold}')
            
            return {
                'prediction': pred,
                'probability': round(proba, 6),
                'threshold': cls._threshold
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
