"""
Models for VirusTotal link checks and daily quota usage.
"""
from datetime import datetime

from app.utils.database import get_db


class VTLinkCheck:
    """Model for vt_link_checks table."""

    @staticmethod
    def exists(email_id: int, url_hash: str) -> bool:
        """Return True if this email-link has already been checked."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM vt_link_checks WHERE email_id = ? AND url_hash = ? LIMIT 1',
                (email_id, url_hash),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def create(
        user_id: int,
        email_id: int,
        url: str,
        url_hash: str,
        status: str,
        malicious: int = 0,
        suspicious: int = 0,
        harmless: int = 0,
        undetected: int = 0,
        error_message: str | None = None,
    ) -> dict | None:
        """Store a VirusTotal check result."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR IGNORE INTO vt_link_checks
                   (user_id, email_id, url, url_hash, status, malicious, suspicious, harmless, undetected, last_checked_at, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    user_id,
                    email_id,
                    url,
                    url_hash,
                    status,
                    malicious,
                    suspicious,
                    harmless,
                    undetected,
                    datetime.now().isoformat(),
                    error_message,
                ),
            )
            if cursor.rowcount == 0:
                return None
            row_id = cursor.lastrowid
            cursor.execute('SELECT * FROM vt_link_checks WHERE id = ?', (row_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
        """Get VirusTotal link results for one user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, user_id, email_id, url, status, malicious, suspicious, harmless, undetected,
                          last_checked_at, error_message, created_at
                   FROM vt_link_checks
                   WHERE user_id = ?
                   ORDER BY last_checked_at DESC
                   LIMIT ? OFFSET ?''',
                (user_id, limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_email_id(email_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
        """Get VirusTotal link results for one email."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, user_id, email_id, url, status, malicious, suspicious, harmless, undetected,
                          last_checked_at, error_message, created_at
                   FROM vt_link_checks
                   WHERE email_id = ?
                   ORDER BY last_checked_at DESC
                   LIMIT ? OFFSET ?''',
                (email_id, limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]


class VTDailyUsage:
    """Model for vt_daily_usage table."""

    @staticmethod
    def get_count(usage_date: str) -> int:
        """Get request count for a specific YYYY-MM-DD date."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT request_count FROM vt_daily_usage WHERE usage_date = ?',
                (usage_date,),
            )
            row = cursor.fetchone()
            return int(row['request_count']) if row else 0

    @staticmethod
    def increment(usage_date: str, delta: int = 1) -> int:
        """Increase request count for date and return new count."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO vt_daily_usage (usage_date, request_count, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(usage_date) DO UPDATE SET
                     request_count = request_count + excluded.request_count,
                     updated_at = excluded.updated_at''',
                (usage_date, delta, datetime.now().isoformat()),
            )
            cursor.execute(
                'SELECT request_count FROM vt_daily_usage WHERE usage_date = ?',
                (usage_date,),
            )
            row = cursor.fetchone()
            return int(row['request_count']) if row else 0
