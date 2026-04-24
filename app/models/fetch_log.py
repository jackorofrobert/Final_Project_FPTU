"""
FetchLog model for tracking email fetch events.
"""
from app.db.session import get_db


class FetchLog:
    """FetchLog model representing the fetch_logs table."""

    @staticmethod
    def create(user_id: int, source: str, emails_fetched: int, new_emails: int) -> dict:
        """Record a fetch event."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO fetch_logs (user_id, source, emails_fetched, new_emails)
                   VALUES (?, ?, ?, ?)''',
                (user_id, source, emails_fetched, new_emails)
            )
            log_id = cursor.lastrowid
            cursor.execute('SELECT * FROM fetch_logs WHERE id = ?', (log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        """Get fetch logs for a user, most recent first."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM fetch_logs
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?''',
                (user_id, limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
