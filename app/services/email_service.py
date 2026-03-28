"""
Email service for email CRUD operations.
"""
from app.models import Email, Prediction, PredictionFeature, PredictionLink, SuspiciousSegment
from app.services.prediction_service import PredictionService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class EmailService:
    """Service for email storage and retrieval operations."""
    
    @staticmethod
    def create_email(user_id: int, gmail_message_id: str, subject: str, 
                    sender: str, recipient: str, body: str, received_at: str) -> dict:
        """Create a new email record."""
        logger.debug(f'Creating email record [user_id={user_id}] [gmail_message_id={gmail_message_id}] [subject={subject[:50]}...]')
        email = Email.create(user_id, gmail_message_id, subject, sender, recipient, body, received_at)
        logger.debug(f'Email record created [email_id={email["id"]}] [user_id={user_id}]')
        return email
    
    @staticmethod
    def get_email_by_gmail_id(user_id: int, gmail_message_id: str) -> dict | None:
        """Get email by user ID and Gmail message ID."""
        return Email.get_by_gmail_id(user_id, gmail_message_id)

    @staticmethod
    def get_email_by_id(email_id: int) -> dict | None:
        """Get email by ID."""
        logger.debug(f'Retrieving email by ID [email_id={email_id}]')
        email = Email.get_by_id(email_id)
        if email:
            logger.debug(f'Email retrieved [email_id={email_id}]')
        else:
            logger.debug(f'Email not found [email_id={email_id}]')
        return email
    
    @staticmethod
    def get_emails_by_user(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get emails for a user."""
        logger.debug(f'Retrieving emails for user [user_id={user_id}] [limit={limit}] [offset={offset}]')
        emails = Email.get_by_user_id(user_id, limit, offset)
        logger.debug(f'Retrieved {len(emails)} emails for user [user_id={user_id}]')
        return emails
    
    @staticmethod
    def get_email_with_prediction(email_id: int) -> dict | None:
        """Get email with its latest prediction."""
        email = Email.get_by_id(email_id)
        if not email:
            return None
        
        prediction = Prediction.get_latest_by_email_id(email_id)
        email['prediction'] = prediction
        return email
    
    @staticmethod
    def create_prediction(email_id: int, prediction: int, probability: float, 
                         model_version: str = None, result: dict = None) -> dict:
        """Create a prediction record with full details."""
        logger.debug(f'Creating prediction record [email_id={email_id}] [prediction={prediction}] [probability={probability:.4f}]')
        
        # Create main prediction record
        pred = Prediction.create(
            email_id=email_id,
            prediction=prediction,
            probability=probability,
            model_version=model_version,
            ensemble_score=result.get('ensemble_score') if result else None,
            classification=result.get('classification') if result else None,
            threshold=result.get('threshold') if result else None,
            suspicious_margin=result.get('suspicious_margin') if result else None
        )
        
        if not pred:
            logger.error(f'Failed to create prediction record [email_id={email_id}]')
            return None
        
        prediction_id = pred['id']
        logger.debug(f'Prediction record created [prediction_id={prediction_id}]')
        
        # Store detailed analysis if available
        if result:
            # Store features
            features = result.get('features', {})
            formula_details = result.get('formula_details', {})
            
            if features:
                sender_risk = formula_details.get('sender_classification', 'UNKNOWN')
                PredictionFeature.create(
                    prediction_id=prediction_id,
                    links_count=features.get('links_count', 0),
                    has_attachment=features.get('has_attachment', 0),
                    urgent_keywords=features.get('urgent_keywords', 0),
                    sender_domain=features.get('sender_domain', ''),
                    sender_risk=sender_risk
                )
                logger.debug(f'Features stored [prediction_id={prediction_id}]')
            
            # Store links analysis
            links_details = formula_details.get('links_details', [])
            if links_details:
                PredictionLink.create_batch(prediction_id, links_details)
                logger.debug(f'Links stored: {len(links_details)} links [prediction_id={prediction_id}]')
            
            # Store suspicious segments
            suspicious_segments = result.get('suspicious_segments', [])
            if suspicious_segments:
                SuspiciousSegment.create_batch(prediction_id, suspicious_segments)
                logger.debug(f'Suspicious segments stored: {len(suspicious_segments)} segments [prediction_id={prediction_id}]')
        
        return pred
    
    @staticmethod
    def get_prediction_details(prediction_id: int) -> dict:
        """Get full prediction details including features, links, and segments."""
        prediction = Prediction.get_by_id(prediction_id)
        if not prediction:
            return None
        
        # Get related details
        features = PredictionFeature.get_by_prediction_id(prediction_id)
        links = PredictionLink.get_by_prediction_id(prediction_id)
        segments = SuspiciousSegment.get_by_prediction_id(prediction_id)
        
        return {
            'prediction': prediction,
            'features': features,
            'links': links,
            'suspicious_segments': segments
        }
    
    @staticmethod
    def analyze_and_save(email_id: int, email_text: str, model_version: str = None) -> dict:
        """Analyze email and save prediction with full details."""
        # Get prediction
        result = PredictionService.predict(email_text)
        
        # Save prediction with details
        prediction = EmailService.create_prediction(
            email_id,
            result['prediction'],
            result['probability'],
            model_version or PredictionService.get_model_version(),
            result
        )
        
        return {
            'prediction': prediction,
            'result': result
        }
