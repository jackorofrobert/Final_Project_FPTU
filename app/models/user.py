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
            return User.get_by_id(cursor.lastrowid)
    
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
