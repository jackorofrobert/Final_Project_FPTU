"""
Model for VirusTotal scheduler run logs.
"""
from app.db.session import get_db


class VTScanLog:
    """Model for vt_scan_logs table."""

    @staticmethod
    def create(
        user_id: int,
        source: str,
        checked: int,
        skipped: int,
        errors: int,
        quota_remaining: int,
    ) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO vt_scan_logs
                   (user_id, source, checked, skipped, errors, quota_remaining)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, source, checked, skipped, errors, quota_remaining),
            )
            row_id = cursor.lastrowid
            cursor.execute('SELECT * FROM vt_scan_logs WHERE id = ?', (row_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get VT scheduler/manual scan history for a user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM vt_scan_logs
                   WHERE user_id = ?
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?''',
                (user_id, limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]
