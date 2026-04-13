"""
Translation endpoints (English via Google AI Studio / Gemini).
"""

import time

from fastapi import APIRouter, Depends, Query, Request

from app.core.dependencies import get_current_user_dependency
from app.models import Email, TranslationLog
from app.schemas.translation import TranslateTextRequest
from app.services.translation_service import translate_to_english
from app.utils.api_response import (
    success_response,
    error_response,
    unauthorized_response,
)
from app.utils.logger import get_logger

router = APIRouter(prefix="/translate")
logger = get_logger(__name__)


@router.get(
    "/status",
    summary="Translation analytics summary",
    description="Aggregated stats for the current user's AI translations.",
    tags=["Translation"],
)
async def translation_status(
    request: Request,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        stats = TranslationLog.get_stats_for_user(user_id)
        return success_response(data=stats)
    except Exception as e:
        logger.error(
            "Translation status error [user_id=%s] [request_id=%s]: %s",
            user_id,
            request_id,
            e,
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error loading translation stats", status_code=500
        )


@router.get(
    "/history",
    summary="Translation request history",
    description="Recent translation attempts (success and failure) for analytics.",
    tags=["Translation"],
)
async def translation_history(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        logs = TranslationLog.get_by_user_id(user_id, limit=limit, offset=offset)
        return success_response(data={"logs": logs, "limit": limit, "offset": offset})
    except Exception as e:
        logger.error(
            "Translation history error [user_id=%s] [request_id=%s]: %s",
            user_id,
            request_id,
            e,
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error loading translation history", status_code=500
        )


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
    source_chars = len(body.text or "")
    t0 = time.monotonic()
    try:
        result = await translate_to_english(body.text)
        duration_ms = int((time.monotonic() - t0) * 1000)
        translated = result.get("translated_text") or ""
        TranslationLog.create(
            user_id,
            "paste",
            success=True,
            chunk_count=int(result.get("chunk_count") or 0),
            source_chars=int(result.get("source_chars") or source_chars),
            translated_chars=len(translated),
            model=str(result.get("model") or ""),
            duration_ms=duration_ms,
            urls_preserved=int(result.get("urls_preserved_count") or 0),
            translated_text=translated,
        )
        result["duration_ms"] = duration_ms
        return success_response(
            data=result,
            message="Translation completed",
        )
    except ValueError as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        TranslationLog.create(
            user_id,
            "paste",
            success=False,
            chunk_count=0,
            source_chars=source_chars,
            translated_chars=0,
            model="",
            duration_ms=duration_ms,
            urls_preserved=0,
            error_message=str(e),
        )
        logger.warning(
            "Translation validation error [user_id=%s] [request_id=%s]: %s",
            user_id,
            request_id,
            e,
        )
        return error_response(error=str(e), message=str(e), status_code=400)
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        TranslationLog.create(
            user_id,
            "paste",
            success=False,
            chunk_count=0,
            source_chars=source_chars,
            translated_chars=0,
            model="",
            duration_ms=duration_ms,
            urls_preserved=0,
            error_message=str(e),
        )
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
    t0 = time.monotonic()
    try:
        email = Email.get_by_id(email_id)
        if not email or email.get("user_id") != user_id:
            return unauthorized_response("Access denied")

        body_text = email.get("body") or ""
        source_chars = len(body_text)
        result = await translate_to_english(body_text)
        duration_ms = int((time.monotonic() - t0) * 1000)
        translated = result.get("translated_text") or ""
        TranslationLog.create(
            user_id,
            "email",
            email_id=email_id,
            success=True,
            chunk_count=int(result.get("chunk_count") or 0),
            source_chars=int(result.get("source_chars") or source_chars),
            translated_chars=len(translated),
            model=str(result.get("model") or ""),
            duration_ms=duration_ms,
            urls_preserved=int(result.get("urls_preserved_count") or 0),
            translated_text=translated,
        )
        result["email_id"] = email_id
        result["duration_ms"] = duration_ms
        return success_response(data=result, message="Translation completed")
    except ValueError as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        email = Email.get_by_id(email_id)
        sc = (
            len((email or {}).get("body") or "")
            if email and email.get("user_id") == user_id
            else 0
        )
        TranslationLog.create(
            user_id,
            "email",
            email_id=email_id if email and email.get("user_id") == user_id else None,
            success=False,
            chunk_count=0,
            source_chars=sc,
            translated_chars=0,
            model="",
            duration_ms=duration_ms,
            urls_preserved=0,
            error_message=str(e),
        )
        logger.warning(
            "Email translation validation [email_id=%s] [user_id=%s] [request_id=%s]: %s",
            email_id,
            user_id,
            request_id,
            e,
        )
        return error_response(error=str(e), message=str(e), status_code=400)
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        email = Email.get_by_id(email_id)
        sc = (
            len((email or {}).get("body") or "")
            if email and email.get("user_id") == user_id
            else 0
        )
        TranslationLog.create(
            user_id,
            "email",
            email_id=email_id if email and email.get("user_id") == user_id else None,
            success=False,
            chunk_count=0,
            source_chars=sc,
            translated_chars=0,
            model="",
            duration_ms=duration_ms,
            urls_preserved=0,
            error_message=str(e),
        )
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


@router.get(
    "/email/{email_id}/latest",
    summary="Get latest saved translation for an email",
    description="Returns the most recent successful translation stored for the given email, or 404 if none exists.",
    tags=["Translation"],
)
async def get_email_latest_translation(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        email = Email.get_by_id(email_id)
        if not email or email.get("user_id") != user_id:
            return unauthorized_response("Access denied")
        record = TranslationLog.get_latest_for_email(email_id)
        if not record:
            from app.utils.api_response import not_found_response

            return not_found_response("No saved translation found for this email")
        return success_response(data=record)
    except Exception as e:
        logger.error(
            "Get latest translation error [email_id=%s] [user_id=%s] [request_id=%s]: %s",
            email_id,
            user_id,
            request_id,
            e,
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error loading translation", status_code=500
        )
