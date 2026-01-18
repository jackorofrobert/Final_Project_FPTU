"""
Email service for email CRUD operations.
"""
from app.models import Email, Prediction
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
    def create_prediction(email_id: int, prediction: int, probability: float, model_version: str = None) -> dict:
        """Create a prediction record for an email."""
        logger.debug(f'Creating prediction record [email_id={email_id}] [prediction={prediction}] [probability={probability:.4f}] [model_version={model_version}]')
        pred = Prediction.create(email_id, prediction, probability, model_version)
        logger.debug(f'Prediction record created [prediction_id={pred["id"]}] [email_id={email_id}]')
        return pred
    
    @staticmethod
    def analyze_and_save(email_id: int, email_text: str, model_version: str = None) -> dict:
        """Analyze email and save prediction."""
        # Get prediction
        result = PredictionService.predict(email_text)
        
        # Save prediction
        prediction = EmailService.create_prediction(
            email_id,
            result['prediction'],
            result['probability'],
            model_version or PredictionService.get_model_version()
        )
        
        return {
            'prediction': prediction,
            'result': result
        }
