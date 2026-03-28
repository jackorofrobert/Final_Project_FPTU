"""
User model for database operations.
"""
from datetime import datetime
from app.utils.database import get_db

class User:
    """User model representing the users table."""
    
    @staticmethod
    def create(email: str) -> dict:
        """Create a new user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (email) VALUES (?)',
                (email,)
            )
            user_id = cursor.lastrowid
            # Fetch the created record in the same connection
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_id(user_id: int) -> dict | None:
        """Get user by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_email(email: str) -> dict | None:
        """Get user by email."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def update_last_login(user_id: int):
        """Update last login timestamp."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now().isoformat(), user_id)
            )
    
    @staticmethod
    def get_or_create(email: str) -> dict:
        """Get existing user or create new one."""
        user = User.get_by_email(email)
        if not user:
            user = User.create(email)
        return user
    
    @staticmethod
    def update_last_fetch(user_id: int):
        """Update last email fetch timestamp."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_fetch_at = ? WHERE id = ?',
                (datetime.now().isoformat(), user_id)
            )
    
    @staticmethod
    def update_last_analysis(user_id: int):
        """Update last auto-analysis timestamp."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_analysis_at = ? WHERE id = ?',
                (datetime.now().isoformat(), user_id)
            )

    @staticmethod
    def get_all_with_tokens() -> list[dict]:
        """Get all users who have valid OAuth tokens (for scheduled fetching)."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.* FROM users u
                INNER JOIN oauth_tokens ot ON u.id = ot.user_id
                WHERE ot.refresh_token IS NOT NULL AND ot.refresh_token != ''
            ''')
            return [dict(row) for row in cursor.fetchall()]
