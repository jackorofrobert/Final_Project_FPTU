"""
Prediction model for database operations.
"""
from app.utils.database import get_db

class Prediction:
    """Prediction model representing the predictions table."""
    
    @staticmethod
    def create(email_id: int, prediction: int, probability: float, model_version: str = None) -> dict:
        """Create a new prediction record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO predictions 
                   (email_id, prediction, probability, model_version) 
                   VALUES (?, ?, ?, ?)''',
                (email_id, prediction, probability, model_version)
            )
            return Prediction.get_by_id(cursor.lastrowid)
    
    @staticmethod
    def get_by_id(prediction_id: int) -> dict | None:
        """Get prediction by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM predictions WHERE id = ?', (prediction_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_email_id(email_id: int) -> list[dict]:
        """Get all predictions for an email, ordered by created_at descending."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM predictions 
                   WHERE email_id = ? 
                   ORDER BY created_at DESC''',
                (email_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_latest_by_email_id(email_id: int) -> dict | None:
        """Get the latest prediction for an email."""
        predictions = Prediction.get_by_email_id(email_id)
        return predictions[0] if predictions else None
    
    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get predictions for all emails of a user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT p.* FROM predictions p
                   JOIN emails e ON p.email_id = e.id
                   WHERE e.user_id = ?
                   ORDER BY p.created_at DESC
                   LIMIT ? OFFSET ?''',
                (user_id, limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
