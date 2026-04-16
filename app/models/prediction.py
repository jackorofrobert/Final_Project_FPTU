"""
Prediction model for database operations.
"""

from app.utils.database import get_db


class Prediction:
    """Prediction model representing the predictions table."""

    @staticmethod
    def create(
        email_id: int,
        prediction: int,
        probability: float,
        model_version: str = None,
        ensemble_score: float = None,
        classification: str = None,
        threshold: float = None,
        suspicious_margin: float = None,
        input_source: str = "original",
    ) -> dict:
        """Create a new prediction record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO predictions 
                   (email_id, prediction, probability, ensemble_score, classification, 
                    threshold, suspicious_margin, model_version, input_source) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email_id,
                    prediction,
                    probability,
                    ensemble_score,
                    classification,
                    threshold,
                    suspicious_margin,
                    model_version,
                    input_source,
                ),
            )
            prediction_id = cursor.lastrowid
            # Fetch the created record in the same connection
            cursor.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(prediction_id: int) -> dict | None:
        """Get prediction by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_email_id(email_id: int) -> list[dict]:
        """Get all predictions for an email, ordered by created_at descending."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM predictions 
                   WHERE email_id = ? 
                   ORDER BY created_at DESC""",
                (email_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_latest_by_email_id(email_id: int) -> dict | None:
        """Get the latest prediction for an email."""
        predictions = Prediction.get_by_email_id(email_id)
        return predictions[0] if predictions else None

    @staticmethod
    def get_latest_original_by_email_id(email_id: int) -> dict | None:
        """Get the latest prediction for an email that is NOT a translation result.

        Returns the most recent prediction where input_source is not 'translated_body'.
        This is used in the email list to always show the original-body score.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM predictions
                   WHERE email_id = ? AND input_source != 'translated_body'
                   ORDER BY created_at DESC
                   LIMIT 1""",
                (email_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get predictions for all emails of a user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT p.* FROM predictions p
                   JOIN emails e ON p.email_id = e.id
                   WHERE e.user_id = ?
                   ORDER BY p.created_at DESC
                   LIMIT ? OFFSET ?""",
                (user_id, limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]
