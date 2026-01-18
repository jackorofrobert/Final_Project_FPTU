"""
Authentication endpoints for OAuth2 API routes.
"""
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.core.config import settings
from app.core.dependencies import get_optional_user_dependency, get_current_user_dependency
from app.core.security import get_current_user_id
from app.services.auth_service import AuthService
from app.schemas.auth import AuthStatus, OAuthConnect
from app.schemas.common import SuccessResponse, ErrorResponse
from app.utils.api_response import success_response, error_response, unauthorized_response
from app.utils.logger import get_logger

router = APIRouter(prefix="/auth")
logger = get_logger(__name__)

# OAuth2 flow configuration
# OpenID Connect scopes for userinfo endpoint access
# Gmail scope for Gmail API access
# Using full scope URLs to match Google's normalization and prevent scope mismatch errors
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/gmail.readonly'
]

# Google userinfo endpoint
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'


async def fetch_user_email(access_token: str) -> Optional[str]:
    """
    Fetch user email from Google's userinfo endpoint.
    
    Args:
        access_token: OAuth2 access token
        
    Returns:
        User email address if successful, None otherwise
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            user_info = response.json()
            email = user_info.get('email')
            if not email:
                logger.warning(f'Userinfo response missing email field: {user_info}')
                return None
            logger.debug(f'Successfully fetched user email from userinfo endpoint')
            return email
    except httpx.HTTPStatusError as e:
        logger.error(f'HTTP error fetching user info: {e.response.status_code} - {e.response.text}', exc_info=True)
        return None
    except httpx.RequestError as e:
        logger.error(f'Request error fetching user info: {str(e)}', exc_info=True)
        return None
    except Exception as e:
        logger.error(f'Unexpected error fetching user info: {str(e)}', exc_info=True)
        return None


def get_flow():
    """Create OAuth2 flow instance."""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GMAIL_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.GMAIL_REDIRECT_URI
    )


@router.get(
    "/status",
    summary="Check authentication status",
    description="Check if the current user is authenticated. Returns authentication status including user ID and email if authenticated.",
    responses={
        200: {
            "description": "Authentication status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "authenticated": True,
                            "user_id": 1,
                            "user_email": "user@example.com"
                        }
                    }
                }
            }
        }
    },
    tags=["Authentication"]
)
async def status(request: Request):
    """
    Check authentication status.
    
    Returns the current authentication status of the user session.
    - If authenticated: returns user_id and user_email
    - If not authenticated: returns authenticated=False
    """
    user_id = get_current_user_id(request)
    user_email = request.session.get('user_email') if hasattr(request, 'session') else None
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    if user_id:
        logger.info(f'Authentication status check: authenticated [user_id={user_id}] [request_id={request_id}]')
        return success_response(data={
            'authenticated': True,
            'user_id': user_id,
            'user_email': user_email
        })
    else:
        logger.info(f'Authentication status check: not authenticated [request_id={request_id}]')
        return success_response(data={
            'authenticated': False
        })


@router.post(
    "/connect",
    summary="Initiate OAuth2 flow",
    description="Start the OAuth2 authentication flow with Gmail. Returns an authorization URL that the user should visit to grant access.",
    responses={
        200: {
            "description": "OAuth2 flow initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "authorization_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
                            "state": "random_state_string_12345"
                        },
                        "message": "OAuth2 flow initiated"
                    }
                }
            }
        },
        500: {
            "description": "Failed to initiate OAuth2 flow",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "OAuth2 configuration error",
                        "message": "Failed to initiate OAuth2 flow"
                    }
                }
            }
        }
    },
    tags=["Authentication"]
)
async def connect(request: Request):
    """
    Initiate OAuth2 flow - returns authorization URL.
    
    This endpoint starts the OAuth2 authentication process. The client should:
    1. Call this endpoint to get the authorization_url
    2. Redirect the user to the authorization_url
    3. User grants permission on Google's OAuth page
    4. Google redirects to /auth/callback with an authorization code
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.info(f'OAuth2 flow initiation requested [request_id={request_id}]')
    
    try:
        flow = get_flow()
        logger.debug(f'OAuth2 scopes requested: {SCOPES} [request_id={request_id}]')
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',  # Force consent screen to ensure refresh_token is returned
            include_granted_scopes='true'
        )
        request.session['oauth_state'] = state
        logger.info(f'OAuth2 flow initiated successfully [state={state[:8]}...] [scopes={len(SCOPES)}] [prompt=consent] [request_id={request_id}]')
        return success_response(data={
            'authorization_url': authorization_url,
            'state': state
        }, message='OAuth2 flow initiated')
    except Exception as e:
        logger.error(f'Failed to initiate OAuth2 flow [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Failed to initiate OAuth2 flow', status_code=500)


@router.get(
    "/callback",
    summary="OAuth2 callback handler",
    description="Handle the OAuth2 callback from Google. This endpoint processes the authorization code and completes the authentication flow. Redirects to the frontend with success or error status.",
    responses={
        302: {
            "description": "Redirect to frontend with authentication result",
            "headers": {
                "Location": {
                    "description": "Frontend URL with auth-success or auth-error parameter",
                    "schema": {"type": "string", "example": "http://localhost:8000/#auth-success"}
                }
            }
        }
    },
    tags=["Authentication"]
)
async def callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None
):
    """
    Handle OAuth2 callback - redirects to frontend with success.
    
    This endpoint is called by Google after the user grants permission.
    It processes the authorization code, stores OAuth tokens, and redirects
    the user back to the frontend application.
    
    **Query Parameters:**
    - `code`: Authorization code from Google (required if no error)
    - `state`: OAuth state parameter for CSRF protection (required if no error)
    - `error`: Error code if OAuth flow failed (optional)
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Handle OAuth errors
    if error:
        logger.warning(f'OAuth2 callback error: {error} [request_id={request_id}]')
        base_url = str(request.base_url).rstrip('/')
        return RedirectResponse(url=f'{base_url}/#auth-error={error}')
    
    if not code or not state:
        logger.warning(f'OAuth2 callback missing code or state [request_id={request_id}]')
        base_url = str(request.base_url).rstrip('/')
        return RedirectResponse(url=f'{base_url}/#auth-error=Missing authorization code or state')
    
    stored_state = request.session.get('oauth_state')
    if not stored_state or stored_state != state:
        logger.warning(f'OAuth2 callback failed: Invalid OAuth state [request_id={request_id}]')
        base_url = str(request.base_url).rstrip('/')
        return RedirectResponse(url=f'{base_url}/#auth-error=Invalid OAuth state')
    
    try:
        logger.info(f'OAuth2 callback received [request_id={request_id}]')
        
        # Explicitly extract authorization code from query parameters
        authorization_code = code  # Already extracted from query params in function signature
        
        # Debug logging: Check if authorization code exists
        if authorization_code:
            code_masked = f'{authorization_code[:8]}...{authorization_code[-4:]}' if len(authorization_code) > 12 else '***'
            logger.debug(f'Authorization code present in callback [code={code_masked}] [length={len(authorization_code)}] [request_id={request_id}]')
        else:
            logger.warning(f'Authorization code is None in callback [request_id={request_id}]')
        
        if not authorization_code or not authorization_code.strip():
            logger.error(f'Authorization code is missing or empty [request_id={request_id}]')
            base_url = str(request.base_url).rstrip('/')
            return RedirectResponse(url=f'{base_url}/#auth-error=Missing authorization code')
        
        # Log authorization code (masked for security)
        code_masked = f'{authorization_code[:8]}...{authorization_code[-4:]}' if len(authorization_code) > 12 else '***'
        logger.debug(f'Authorization code extracted [code={code_masked}] [request_id={request_id}]')
        
        flow = get_flow()
        
        # Build the full callback URL
        callback_url = str(request.url)
        
        # Exchange authorization code for tokens
        # flow.fetch_token() extracts the code from the callback URL and exchanges it
        try:
            flow.fetch_token(authorization_response=callback_url)
        except Exception as token_exchange_error:
            logger.error(f'Token exchange failed: {str(token_exchange_error)} [request_id={request_id}]', exc_info=True)
            base_url = str(request.base_url).rstrip('/')
            return RedirectResponse(url=f'{base_url}/#auth-error=Token exchange failed: {str(token_exchange_error)}')
        
        # Verify credentials were obtained
        credentials = flow.credentials
        if not credentials:
            logger.error(f'Token exchange failed: No credentials object returned [request_id={request_id}]')
            base_url = str(request.base_url).rstrip('/')
            return RedirectResponse(url=f'{base_url}/#auth-error=Token exchange failed: No credentials')
        
        # Validate access token exists and is not empty
        access_token = credentials.token
        
        # Debug logging: Check if access token exists
        if access_token:
            token_masked = f'{access_token[:10]}...{access_token[-4:]}' if len(access_token) > 14 else '***'
            logger.debug(f'Access token present after exchange [token={token_masked}] [length={len(access_token)}] [request_id={request_id}]')
        else:
            logger.warning(f'Access token is None after exchange [request_id={request_id}]')
        
        if not access_token or not access_token.strip():
            logger.error(f'Token exchange failed: Access token is None or empty [request_id={request_id}]')
            base_url = str(request.base_url).rstrip('/')
            return RedirectResponse(url=f'{base_url}/#auth-error=Token exchange failed: Invalid access token')
        
        # Log access token (masked for security)
        token_masked = f'{access_token[:10]}...{access_token[-4:]}' if len(access_token) > 14 else '***'
        logger.info(f'Access token obtained successfully [token={token_masked}] [length={len(access_token)}] [request_id={request_id}]')
        
        # Extract all token fields
        refresh_token = credentials.refresh_token
        token_type = getattr(credentials, 'token_type', 'Bearer')
        expiry = credentials.expiry
        
        # Log scopes if available in credentials
        granted_scopes = getattr(credentials, 'scopes', None)
        if granted_scopes:
            logger.debug(f'Token scopes granted: {granted_scopes} [request_id={request_id}]')
        logger.info(f'Token exchange successful [token_type={token_type}] [has_refresh_token={bool(refresh_token)}] [expiry={expiry}] [request_id={request_id}]')
        
        # Fetch user email from Google userinfo endpoint
        user_email = await fetch_user_email(access_token)
        if not user_email:
            logger.error(f'Failed to fetch user email from userinfo endpoint [request_id={request_id}]')
            base_url = str(request.base_url).rstrip('/')
            return RedirectResponse(url=f'{base_url}/#auth-error=Failed to fetch user information')
        
        logger.info(f'User email fetched successfully [email={user_email}] [request_id={request_id}]')
        
        # Calculate token expiration time
        expires_in = int(expiry.timestamp() - time.time()) if expiry else 3600
        
        # Store tokens with all fields
        user = AuthService.store_tokens(
            user_email,
            access_token,
            refresh_token,
            expires_in
        )
        
        request.session['user_id'] = user['id']
        request.session['user_email'] = user['email']
        
        logger.info(f'OAuth2 callback successful: User authenticated [user_id={user["id"]}] [user_email={user["email"]}] [request_id={request_id}]')
        base_url = str(request.base_url).rstrip('/')
        return RedirectResponse(url=f'{base_url}/#auth-success')
    except Exception as e:
        logger.error(f'OAuth2 callback failed [request_id={request_id}]: {str(e)}', exc_info=True)
        base_url = str(request.base_url).rstrip('/')
        return RedirectResponse(url=f'{base_url}/#auth-error={str(e)}')


@router.post(
    "/disconnect",
    summary="Disconnect Gmail account",
    description="Disconnect the authenticated Gmail account by removing stored OAuth tokens and clearing the user session. Requires authentication.",
    responses={
        200: {
            "description": "Gmail account disconnected successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Gmail account disconnected"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Authentication required"
                    }
                }
            }
        }
    },
    tags=["Authentication"]
)
async def disconnect(request: Request, user_id: int = Depends(get_current_user_dependency)):
    """
    Disconnect Gmail account.
    
    Removes the OAuth tokens for the authenticated user and clears the session.
    After disconnecting, the user will need to authenticate again to use Gmail features.
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.info(f'Gmail account disconnect requested [user_id={user_id}] [request_id={request_id}]')
    AuthService.delete_tokens(user_id)
    request.session.pop('user_id', None)
    request.session.pop('user_email', None)
    logger.info(f'Gmail account disconnected successfully [user_id={user_id}] [request_id={request_id}]')
    return success_response(message='Gmail account disconnected')
