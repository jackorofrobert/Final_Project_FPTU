"""
Translation endpoints (English via Google AI Studio / Gemini).
"""
from fastapi import APIRouter, Depends, Request

from app.core.dependencies import get_current_user_dependency
from app.models import Email
from app.schemas.translation import TranslateTextRequest
from app.services.translation_service import translate_to_english
from app.utils.api_response import success_response, error_response, unauthorized_response
from app.utils.logger import get_logger

router = APIRouter(prefix="/translate")
logger = get_logger(__name__)


@router.post(
    "/to-english",
    summary="Translate text to English (AI)",
    description="Translate arbitrary text to English using Gemini. Long text is split into chunks server-side.",
    tags=["Translation"],
)
async def translate_text_to_english(
    request: Request,
    body: TranslateTextRequest,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        result = await translate_to_english(body.text)
        return success_response(
            data=result,
            message="Translation completed",
        )
    except ValueError as e:
        logger.warning(
            "Translation validation error [user_id=%s] [request_id=%s]: %s",
            user_id,
            request_id,
            e,
        )
        return error_response(error=str(e), message=str(e), status_code=400)
    except Exception as e:
        logger.error(
            "Translation failed [user_id=%s] [request_id=%s]: %s",
            user_id,
            request_id,
            e,
            exc_info=True,
        )
        return error_response(
            error=str(e),
            message="Translation failed",
            status_code=500,
        )


@router.post(
    "/email/{email_id}/to-english",
    summary="Translate stored email body to English (AI)",
    description="Loads the email body for the authenticated user and translates it to English using chunked Gemini calls.",
    tags=["Translation"],
)
async def translate_email_to_english(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        email = Email.get_by_id(email_id)
        if not email or email.get("user_id") != user_id:
            return unauthorized_response("Access denied")

        body_text = email.get("body") or ""
        result = await translate_to_english(body_text)
        result["email_id"] = email_id
        return success_response(data=result, message="Translation completed")
    except ValueError as e:
        logger.warning(
            "Email translation validation [email_id=%s] [user_id=%s] [request_id=%s]: %s",
            email_id,
            user_id,
            request_id,
            e,
        )
        return error_response(error=str(e), message=str(e), status_code=400)
    except Exception as e:
        logger.error(
            "Email translation failed [email_id=%s] [user_id=%s] [request_id=%s]: %s",
            email_id,
            user_id,
            request_id,
            e,
            exc_info=True,
        )
        return error_response(
            error=str(e),
            message="Translation failed",
            status_code=500,
        )
