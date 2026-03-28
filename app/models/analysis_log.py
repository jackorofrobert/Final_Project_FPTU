"""
AnalysisLog model for tracking auto-analysis events.
"""
from app.utils.database import get_db


class AnalysisLog:
    """AnalysisLog model representing the analysis_logs table."""

    @staticmethod
    def create(user_id: int, source: str, emails_analyzed: int, emails_skipped: int) -> dict:
        """Record an analysis event."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO analysis_logs (user_id, source, emails_analyzed, emails_skipped)
                   VALUES (?, ?, ?, ?)''',
                (user_id, source, emails_analyzed, emails_skipped)
            )
            log_id = cursor.lastrowid
            cursor.execute('SELECT * FROM analysis_logs WHERE id = ?', (log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        """Get analysis logs for a user, most recent first."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM analysis_logs
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?''',
                (user_id, limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
