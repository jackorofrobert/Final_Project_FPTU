"""
Authentication service for mail API token management.
"""

import json
from datetime import datetime, timedelta
from app.models import User, OAuthToken
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for mail API authentication and token management."""

    @staticmethod
    def store_tokens(
        user_email: str,
        access_token: str,
        refresh_token: str,
        expires_in: int = 604800,  # 7 days default (mail API accessTokenTtl)
        token_id: str = "",
        refresh_expires_at: str = "",
    ):
        """
        Store mail API tokens for a user.

        Args:
            user_email:          Mailbox email address.
            access_token:        JWT access token from mail API.
            refresh_token:       Opaque refresh token from mail API.
            expires_in:          Access token lifetime in seconds (default 7 days).
            token_id:            UUID returned by mail API (stored in token JSON).
            refresh_expires_at:  ISO datetime when refresh token expires.
        """
        logger.info(
            f"Storing mail API tokens [user_email={user_email}] [expires_in={expires_in}]"
        )

        if refresh_token and refresh_token.strip():
            masked = (
                f"{refresh_token[:10]}...{refresh_token[-4:]}"
                if len(refresh_token) > 14
                else "***"
            )
            logger.info(
                f"Refresh token available [token={masked}] [user_email={user_email}]"
            )
        else:
            logger.warning(f"Refresh token is None or empty [user_email={user_email}]")

        if expires_in <= 0:
            logger.warning(
                f"Invalid expires_in {expires_in}, using 604800 [user_email={user_email}]"
            )
            expires_in = 604800

        # Get or create user
        user = User.get_or_create(user_email)
        if not user:
            raise ValueError(f"Failed to create/retrieve user for {user_email}")

        User.update_last_login(user["id"])

        # Pack access token + mail API metadata into the token JSON blob
        token_data = json.dumps(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "token_id": token_id,
                "refresh_expires_at": refresh_expires_at,
            }
        )

        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()

        OAuthToken.upsert(user["id"], token_data, refresh_token, expires_at)

        logger.info(f"Tokens stored [user_id={user['id']}] [user_email={user_email}]")
        return user

    @staticmethod
    def get_tokens(user_id: int) -> dict | None:
        """
        Return stored tokens for *user_id*.

        Returns dict with keys:
          access_token, refresh_token, expires_at,
          token_id, refresh_expires_at
        """
        logger.debug(f"Retrieving tokens [user_id={user_id}]")
        record = OAuthToken.get_by_user_id(user_id)
        if not record:
            return None

        try:
            token_data = json.loads(record["token"])
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": record["refresh_token"],
                "expires_at": record["expires_at"],
                "token_id": token_data.get("token_id", ""),
                "refresh_expires_at": token_data.get("refresh_expires_at", ""),
            }
        except Exception as e:
            logger.error(
                f"Error parsing tokens [user_id={user_id}]: {e}", exc_info=True
            )
            return None

    @staticmethod
    def has_refresh_token(user_id: int) -> bool:
        """Return True if user has a non-empty refresh token."""
        record = OAuthToken.get_by_user_id(user_id)
        if not record:
            return False
        rt = record.get("refresh_token")
        return bool(rt and rt.strip())

    @staticmethod
    def delete_tokens(user_id: int):
        """Delete tokens for a user (logout/disconnect)."""
        logger.info(f"Deleting tokens [user_id={user_id}]")
        OAuthToken.delete_by_user_id(user_id)
        logger.info(f"Tokens deleted [user_id={user_id}]")
