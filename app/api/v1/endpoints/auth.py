"""
Authentication endpoints — mail API login/logout flow.

Replaces the previous Google OAuth2 flow.
Connect:    POST /api/v1/auth/connect  (email + password)
Status:     GET  /api/v1/auth/status
Disconnect: POST /api/v1/auth/disconnect
"""

from fastapi import APIRouter, Request, Depends

from app.core.dependencies import get_current_user_dependency
from app.core.security import get_current_user_id
from app.services.auth_service import AuthService
from app.services.mail_api_service import MailApiService
from app.schemas.auth import AuthStatus, MailConnect
from app.schemas.common import SuccessResponse, ErrorResponse
from app.utils.api_response import (
    success_response,
    error_response,
    unauthorized_response,
)
from app.utils.logger import get_logger

router = APIRouter(prefix="/auth")
logger = get_logger(__name__)


@router.get(
    "/status",
    summary="Check authentication status",
    description="Returns whether the current session is authenticated, and the user ID / email if so.",
    tags=["Authentication"],
)
async def status(request: Request):
    """Check authentication status."""
    user_id = get_current_user_id(request)
    user_email = (
        request.session.get("user_email") if hasattr(request, "session") else None
    )
    request_id = getattr(request.state, "request_id", "unknown")

    if user_id:
        logger.info(
            f"Auth status: authenticated [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(
            data={
                "authenticated": True,
                "user_id": user_id,
                "user_email": user_email,
            }
        )
    else:
        logger.info(f"Auth status: not authenticated [request_id={request_id}]")
        return success_response(data={"authenticated": False})


@router.post(
    "/connect",
    summary="Connect mail account",
    description=(
        "Login to the custom mail API using email + password. "
        "Obtains an access token and refresh token from the mail API server, "
        "stores them, and establishes a server-side session."
    ),
    responses={
        200: {
            "description": "Connected successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"user_id": 1, "user_email": "archive@spktfpt.online"},
                        "message": "Mail account connected",
                    }
                }
            },
        },
        401: {"description": "Invalid credentials"},
        500: {"description": "Mail API unreachable or server error"},
    },
    tags=["Authentication"],
)
async def connect(request: Request, body: MailConnect):
    """
    Connect to the custom mail API with email + password.

    1. Calls POST /api/auth/token on the mail API server.
    2. Stores the returned access + refresh tokens in the local DB.
    3. Sets the user session so subsequent requests are authenticated.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"Mail API connect requested [email={body.email}] [request_id={request_id}]"
    )

    try:
        token_data = MailApiService.login(
            email=body.email,
            password=body.password,
            label=body.label,
        )
    except ValueError as e:
        logger.warning(f"Mail API login failed [email={body.email}]: {e}")
        return error_response(
            error=str(e),
            message="Invalid credentials or mail API error",
            status_code=401,
        )
    except Exception as e:
        logger.error(f"Mail API connect error [email={body.email}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Failed to connect to mail API", status_code=500
        )

    try:
        user = AuthService.store_tokens(
            user_email=body.email,
            access_token=token_data["accessToken"],
            refresh_token=token_data["refreshToken"],
            token_id=token_data.get("tokenId", ""),
            refresh_expires_at=token_data.get("refreshExpiresAt", ""),
        )
    except Exception as e:
        logger.error(f"Failed to store tokens [email={body.email}]: {e}", exc_info=True)
        return error_response(
            error=str(e), message="Failed to store tokens", status_code=500
        )

    request.session["user_id"] = user["id"]
    request.session["user_email"] = user["email"]

    logger.info(
        f"Mail account connected [user_id={user['id']}] [user_email={user['email']}] "
        f"[request_id={request_id}]"
    )
    return success_response(
        data={"user_id": user["id"], "user_email": user["email"]},
        message="Mail account connected",
    )


@router.post(
    "/disconnect",
    summary="Disconnect mail account",
    description=(
        "Revoke the current refresh token on the mail API server, "
        "delete local tokens, and clear the session."
    ),
    responses={
        200: {"description": "Disconnected successfully"},
        401: {"description": "Authentication required"},
    },
    tags=["Authentication"],
)
async def disconnect(
    request: Request, user_id: int = Depends(get_current_user_dependency)
):
    """Disconnect the mail account and clear session."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"Disconnect requested [user_id={user_id}] [request_id={request_id}]")

    # Best-effort revoke on the mail API side
    try:
        MailApiService.revoke(user_id)
    except Exception as e:
        logger.warning(f"Mail API revoke error (continuing) [user_id={user_id}]: {e}")

    AuthService.delete_tokens(user_id)
    request.session.pop("user_id", None)
    request.session.pop("user_email", None)

    logger.info(f"Disconnected [user_id={user_id}] [request_id={request_id}]")
    return success_response(message="Mail account disconnected")
