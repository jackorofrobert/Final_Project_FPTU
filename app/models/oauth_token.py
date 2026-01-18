"""
OAuthToken model for database operations.
"""
from datetime import datetime
from app.utils.database import get_db

class OAuthToken:
    """OAuthToken model representing the oauth_tokens table."""
    
    @staticmethod
    def create(user_id: int, token: str, refresh_token: str, expires_at: str) -> dict:
        """Create a new OAuth token record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO oauth_tokens 
                   (user_id, token, refresh_token, expires_at) 
                   VALUES (?, ?, ?, ?)''',
                (user_id, token, refresh_token, expires_at)
            )
            return OAuthToken.get_by_id(cursor.lastrowid)
    
    @staticmethod
    def get_by_id(token_id: int) -> dict | None:
        """Get OAuth token by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM oauth_tokens WHERE id = ?', (token_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_user_id(user_id: int) -> dict | None:
        """Get OAuth token by user ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM oauth_tokens WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def update(user_id: int, token: str, refresh_token: str, expires_at: str):
        """Update OAuth token for a user.
        
        Preserves existing refresh_token if new refresh_token is None.
        This ensures refresh capability is maintained across token updates.
        """
        # Get existing token to preserve refresh_token if new one is None
        existing = OAuthToken.get_by_user_id(user_id)
        if existing and (not refresh_token or not refresh_token.strip()):
            # Preserve existing refresh_token if new one is None/empty
            refresh_token = existing.get('refresh_token') or refresh_token
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''UPDATE oauth_tokens 
                   SET token = ?, refresh_token = ?, expires_at = ?, updated_at = ?
                   WHERE user_id = ?''',
                (token, refresh_token, expires_at, datetime.now().isoformat(), user_id)
            )
    
    @staticmethod
    def upsert(user_id: int, token: str, refresh_token: str, expires_at: str) -> dict:
        """Create or update OAuth token for a user."""
        existing = OAuthToken.get_by_user_id(user_id)
        if existing:
            OAuthToken.update(user_id, token, refresh_token, expires_at)
            return OAuthToken.get_by_user_id(user_id)
        else:
            return OAuthToken.create(user_id, token, refresh_token, expires_at)
    
    @staticmethod
    def delete_by_user_id(user_id: int):
        """Delete OAuth token for a user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM oauth_tokens WHERE user_id = ?', (user_id,))
