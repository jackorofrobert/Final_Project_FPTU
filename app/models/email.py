"""
Email model for database operations.
"""
import sqlite3
from datetime import datetime
from app.utils.database import get_db

class Email:
    """Email model representing the emails table."""
    
    @staticmethod
    def create(user_id: int, gmail_message_id: str, subject: str, sender: str, 
               recipient: str, body: str, received_at: str) -> dict:
        """Create a new email record."""
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    '''INSERT INTO emails 
                       (user_id, gmail_message_id, subject, sender, recipient, body, received_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, gmail_message_id, subject, sender, recipient, body, received_at)
                )
                return Email.get_by_id(cursor.lastrowid)
            except sqlite3.IntegrityError:
                # Email already exists (duplicate gmail_message_id for same user)
                return Email.get_by_gmail_id(user_id, gmail_message_id)
    
    @staticmethod
    def get_by_id(email_id: int) -> dict | None:
        """Get email by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emails WHERE id = ?', (email_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_gmail_id(user_id: int, gmail_message_id: str) -> dict | None:
        """Get email by user ID and Gmail message ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM emails WHERE user_id = ? AND gmail_message_id = ?',
                (user_id, gmail_message_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get emails for a user, ordered by received_at descending."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT * FROM emails 
                   WHERE user_id = ? 
                   ORDER BY received_at DESC 
                   LIMIT ? OFFSET ?''',
                (user_id, limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def count_by_user_id(user_id: int) -> int:
        """Count emails for a user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM emails WHERE user_id = ?', (user_id,))
            return cursor.fetchone()[0]
