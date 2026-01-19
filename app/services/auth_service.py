"""
Authentication service for OAuth2 and token management.
"""
import json
from datetime import datetime, timedelta
from app.models import User, OAuthToken
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AuthService:
    """Service for OAuth2 authentication and token management."""
    
    @staticmethod
    def store_tokens(user_email: str, access_token: str, refresh_token: str, expires_in: int = 3600):
        """
        Store OAuth tokens for a user.
        
        Args:
            user_email: User's Gmail email address
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration time in seconds
        """
        logger.info(f"Full info: {user_email} {access_token} {refresh_token} {expires_in}")
        logger.info(f'Storing tokens for user [user_email={user_email}] [expires_in={expires_in}]')
        
        # Validate and log refresh_token availability
        if refresh_token and refresh_token.strip():
            refresh_token_masked = f'{refresh_token[:10]}...{refresh_token[-4:]}' if len(refresh_token) > 14 else '***'
            logger.info(f'Refresh token available [token={refresh_token_masked}] [length={len(refresh_token)}] [user_email={user_email}]')
        else:
            logger.warning(f'Refresh token is None or empty - user will need to re-authorize when token expires [user_email={user_email}]')
        
        # Validate expiration time
        if expires_in <= 0:
            logger.warning(f'Invalid expiration time: {expires_in} seconds. Using default 3600 seconds [user_email={user_email}]')
            expires_in = 3600
        
        # Get or create user
        user = User.get_or_create(user_email)
        if not user:
            error_msg = f'Failed to create or retrieve user account for {user_email}'
            logger.error(f'{error_msg} [user_email={user_email}]', exc_info=True)
            raise ValueError(error_msg)
        
        logger.debug(f'User retrieved/created [user_id={user["id"]}] [user_email={user_email}]')
        
        # Update last login
        User.update_last_login(user['id'])
        
        # Prepare token data as JSON string
        token_data = json.dumps({
            'access_token': access_token,
            'token_type': 'Bearer'
        })
        
        # Calculate expiration
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        # Store tokens as plain text strings
        OAuthToken.upsert(
            user['id'],
            token_data,
            refresh_token,
            expires_at
        )
        
        # Verify refresh_token was persisted
        stored_token = OAuthToken.get_by_user_id(user['id'])
        if stored_token:
            stored_refresh_token = stored_token.get('refresh_token')
            if stored_refresh_token:
                stored_refresh_masked = f'{stored_refresh_token[:10]}...{stored_refresh_token[-4:]}' if len(stored_refresh_token) > 14 else '***'
                logger.info(f'Refresh token persisted successfully [token={stored_refresh_masked}] [user_id={user["id"]}] [user_email={user_email}]')
            else:
                logger.warning(f'Refresh token not found in stored record [user_id={user["id"]}] [user_email={user_email}]')
        
        logger.info(f'Tokens stored successfully [user_id={user["id"]}] [user_email={user_email}]')
        return user
    
    @staticmethod
    def get_tokens(user_id: int) -> dict | None:
        """Get tokens for a user."""
        logger.debug(f'Retrieving tokens for user [user_id={user_id}]')
        token_record = OAuthToken.get_by_user_id(user_id)
        if not token_record:
            logger.debug(f'No tokens found for user [user_id={user_id}]')
            return None
        
        try:
            token_data = json.loads(token_record['token'])
            refresh_token = token_record['refresh_token']
            
            logger.debug(f'Tokens retrieved for user [user_id={user_id}]')
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': refresh_token,
                'expires_at': token_record['expires_at']
            }
        except Exception as e:
            logger.error(f'Error parsing tokens for user [user_id={user_id}]: {str(e)}', exc_info=True)
            return None
    
    @staticmethod
    def has_refresh_token(user_id: int) -> bool:
        """Check if user has a refresh token available for token refresh."""
        logger.debug(f'Checking refresh token availability for user [user_id={user_id}]')
        token_record = OAuthToken.get_by_user_id(user_id)
        if not token_record:
            logger.debug(f'No tokens found for user [user_id={user_id}]')
            return False
        
        refresh_token = token_record.get('refresh_token')
        has_token = bool(refresh_token and refresh_token.strip())
        logger.debug(f'Refresh token availability: {has_token} [user_id={user_id}]')
        return has_token
    
    @staticmethod
    def delete_tokens(user_id: int):
        """Delete tokens for a user (logout/disconnect)."""
        logger.info(f'Deleting tokens for user [user_id={user_id}]')
        OAuthToken.delete_by_user_id(user_id)
        logger.info(f'Tokens deleted for user [user_id={user_id}]')
