"""
Email endpoints for email API routes.
"""

from fastapi import APIRouter, Request, Depends, Query

from app.core.dependencies import get_current_user_dependency
from app.models import (
    Email,
    EmailAttachment,
    Prediction,
    User,
    FetchLog,
    AnalysisLog,
    VTLinkCheck,
    VTAttachmentCheck,
    VTScanLog,
)
from app.schemas.email import EmailFetchRequest
from app.services.email_service import EmailService
from app.services.mail_api_service import MailApiService
from app.services.attachment_service import AttachmentService
from app.services.virustotal_service import VirusTotalService
from app.utils.api_response import (
    success_response,
    error_response,
    unauthorized_response,
    not_found_response,
)
from app.utils.logger import get_logger

router = APIRouter(prefix="/emails")
logger = get_logger(__name__)


@router.post(
    "/fetch",
    summary="Fetch emails from mail server",
    description="Fetch emails from the archive mailbox via the custom mail API. Emails are stored in the database for analysis. Requires authentication.",
    responses={
        200: {
            "description": "Emails fetched and stored successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "count": 3,
                            "emails": [
                                {
                                    "id": 1,
                                    "gmail_message_id": "abc123",
                                    "subject": "Test Email",
                                    "sender": "sender@example.com",
                                    "recipient": "recipient@example.com",
                                }
                            ],
                        },
                        "message": "Successfully fetched and stored 3 emails",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Authentication required"}
                }
            },
        },
        500: {
            "description": "Error fetching emails",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Gmail API error",
                        "message": "Error fetching emails",
                    }
                }
            },
        },
    },
    tags=["Emails"],
)
async def fetch(
    request: Request,
    fetch_request: EmailFetchRequest = EmailFetchRequest(),
    user_id: int = Depends(get_current_user_dependency),
):
    """
    Fetch emails from the mail API.

    Retrieves emails from the archive mailbox and stores them in the database.
    The number of emails fetched is limited by the max_results parameter (default: 50, max: 500).
    """
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        max_results = min(fetch_request.max_results, 500)  # Cap at 500

        user = User.get_by_id(user_id)
        logger.info(
            f"Email fetch requested [user_id={user_id}] [max_results={max_results}] [request_id={request_id}]"
        )

        # Always fetch the latest N emails without a date filter.
        # The DB UNIQUE(user_id, gmail_message_id) constraint deduplicates on insert,
        # so re-fetching already-stored emails is harmless.
        emails = MailApiService.fetch_emails(user_id, max_results=max_results)

        # Store emails in database
        stored_count = 0
        new_count = 0
        stored_emails = []
        for email_data in emails:
            existing = EmailService.get_email_by_gmail_id(
                user_id, email_data["gmail_message_id"]
            )
            email = EmailService.create_email(
                user_id=user_id,
                gmail_message_id=email_data["gmail_message_id"],
                subject=email_data["subject"],
                sender=email_data["sender"],
                recipient=email_data["recipient"],
                body=email_data["body"],
                received_at=email_data["received_at"],
            )
            stored_emails.append(email)
            stored_count += 1
            if not existing:
                new_count += 1

            if not existing and email and email_data.get("attachments"):
                AttachmentService.persist_for_email(
                    user_id=user_id,
                    email_id=email["id"],
                    message_uid=email_data.get("uid"),
                    attachments=email_data["attachments"],
                )

        User.update_last_fetch(user_id)
        FetchLog.create(
            user_id=user_id,
            source="manual",
            emails_fetched=len(emails),
            new_emails=new_count,
        )

        logger.info(
            f"Email fetch completed: {stored_count} total, {new_count} new [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(
            data={
                "count": stored_count,
                "new_count": new_count,
                "emails": stored_emails,
            },
            message=f"Fetched {stored_count} emails ({new_count} new)",
        )
    except Exception as e:
        logger.error(
            f"Error fetching emails [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error fetching emails", status_code=500
        )


@router.get(
    "/list",
    summary="List stored emails",
    description="Retrieve a paginated list of emails stored in the database for the authenticated user. Each email includes its latest prediction if available.",
    responses={
        200: {
            "description": "Email list retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "emails": [
                                {
                                    "id": 1,
                                    "subject": "Test Email",
                                    "sender": "sender@example.com",
                                    "prediction": None,
                                }
                            ],
                            "limit": 50,
                            "offset": 0,
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Authentication required"}
                }
            },
        },
        500: {
            "description": "Error retrieving email list",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving emails",
                    }
                }
            },
        },
    },
    tags=["Emails"],
)
async def list_emails(
    request: Request,
    limit: int = Query(
        50, ge=1, le=100, description="Number of emails to return (1-100)"
    ),
    offset: int = Query(0, ge=0, description="Number of emails to skip for pagination"),
    user_id: int = Depends(get_current_user_dependency),
):
    """
    Get list of stored emails.

    Returns a paginated list of emails for the authenticated user.
    Each email includes its latest prediction result if available.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        logger.info(
            f"Email list requested [user_id={user_id}] [limit={limit}] [offset={offset}] [request_id={request_id}]"
        )

        emails = EmailService.get_emails_by_user(user_id, limit=limit, offset=offset)

        # Get latest *original* prediction for each email (exclude translated_body results)
        for email in emails:
            pred = Prediction.get_latest_original_by_email_id(email["id"])
            email["prediction"] = pred  # None when not yet analyzed

        # Batch-fetch VT summaries to avoid N+1 queries
        email_ids = [e["id"] for e in emails]
        vt_summaries = VTLinkCheck.get_summaries_for_emails(email_ids)
        attachment_summaries = EmailAttachment.get_summaries_for_emails(email_ids)
        for email in emails:
            email["vt_summary"] = vt_summaries.get(email["id"], None)
            email["attachment_summary"] = attachment_summaries.get(email["id"], None)

        logger.info(
            f"Email list retrieved: {len(emails)} emails [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(
            data={"emails": emails, "limit": limit, "offset": offset}
        )
    except Exception as e:
        logger.error(
            f"Error retrieving email list [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error retrieving emails", status_code=500
        )


@router.get(
    "/fetch-status",
    summary="Get email fetch status",
    description="Get the current user's last fetch timestamp and total email count.",
    tags=["Emails"],
)
async def fetch_status(
    request: Request, user_id: int = Depends(get_current_user_dependency)
):
    """Return last_fetch_at and email count for the authenticated user."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        user = User.get_by_id(user_id)
        total_emails = Email.count_by_user_id(user_id)
        return success_response(
            data={
                "last_fetch_at": user.get("last_fetch_at") if user else None,
                "total_emails": total_emails,
            }
        )
    except Exception as e:
        logger.error(
            f"Error getting fetch status [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting fetch status", status_code=500
        )


@router.get(
    "/fetch-history",
    summary="Get email fetch history",
    description="Get a log of all past email fetch events (manual and scheduled) for the authenticated user.",
    tags=["Emails"],
)
async def fetch_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of log entries to return"),
    offset: int = Query(0, ge=0, description="Number of log entries to skip"),
    user_id: int = Depends(get_current_user_dependency),
):
    """Return paginated fetch history for the authenticated user."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        logs = FetchLog.get_by_user_id(user_id, limit=limit, offset=offset)
        return success_response(
            data={
                "logs": logs,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        logger.error(
            f"Error getting fetch history [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting fetch history", status_code=500
        )


@router.get(
    "/analysis-status",
    summary="Get auto-analysis status",
    description="Get the current user's last analysis timestamp and count of unanalyzed emails.",
    tags=["Emails"],
)
async def analysis_status(
    request: Request, user_id: int = Depends(get_current_user_dependency)
):
    """Return last_analysis_at and unanalyzed email count."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        user = User.get_by_id(user_id)
        unanalyzed = Email.get_unanalyzed_by_user_id(user_id, limit=1000)
        total_emails = Email.count_by_user_id(user_id)
        return success_response(
            data={
                "last_analysis_at": user.get("last_analysis_at") if user else None,
                "unanalyzed_count": len(unanalyzed),
                "total_emails": total_emails,
            }
        )
    except Exception as e:
        logger.error(
            f"Error getting analysis status [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting analysis status", status_code=500
        )


@router.get(
    "/analysis-history",
    summary="Get auto-analysis history",
    description="Get a log of all past auto-analysis events for the authenticated user.",
    tags=["Emails"],
)
async def analysis_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of log entries to return"),
    offset: int = Query(0, ge=0, description="Number of log entries to skip"),
    user_id: int = Depends(get_current_user_dependency),
):
    """Return paginated analysis history for the authenticated user."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        logs = AnalysisLog.get_by_user_id(user_id, limit=limit, offset=offset)
        return success_response(
            data={
                "logs": logs,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        logger.error(
            f"Error getting analysis history [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting analysis history", status_code=500
        )


@router.get(
    "/vt-status",
    summary="Get VirusTotal quota status",
    description="Get current VirusTotal daily usage and remaining requests.",
    tags=["Emails"],
)
async def vt_status(
    request: Request, user_id: int = Depends(get_current_user_dependency)
):
    """Return VirusTotal quota usage for today."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        usage = VirusTotalService.get_daily_usage()
        return success_response(data=usage)
    except Exception as e:
        logger.error(
            f"Error getting VT status [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting VirusTotal status", status_code=500
        )


@router.post(
    "/vt-scan-now",
    summary="Run VirusTotal scan now",
    description="Manually trigger VirusTotal scan immediately (does not wait for scheduler).",
    tags=["Emails"],
)
async def vt_scan_now(
    request: Request, user_id: int = Depends(get_current_user_dependency)
):
    """Trigger manual VirusTotal scan for current user."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        result = VirusTotalService.scan_user_email_links(user_id=user_id)
        VTScanLog.create(
            user_id=user_id,
            source="manual",
            checked=result["checked"],
            skipped=result["skipped"],
            errors=result["errors"],
            quota_remaining=result["quota_remaining"],
        )
        return success_response(data=result, message="VirusTotal scan completed")
    except Exception as e:
        logger.error(
            f"Error running VT scan now [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error running VirusTotal scan", status_code=500
        )


@router.get(
    "/vt-history",
    summary="Get VirusTotal scan history",
    description="Get history of scheduler/manual VirusTotal scan runs.",
    tags=["Emails"],
)
async def vt_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_dependency),
):
    """Return VT scan run logs for current user."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        logs = VTScanLog.get_by_user_id(user_id=user_id, limit=limit, offset=offset)
        return success_response(data={"logs": logs, "limit": limit, "offset": offset})
    except Exception as e:
        logger.error(
            f"Error getting VT history [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting VirusTotal history", status_code=500
        )


@router.get(
    "/vt-results",
    summary="Get VirusTotal link results",
    description="Get stored VirusTotal results for checked links.",
    tags=["Emails"],
)
async def vt_results(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_dependency),
):
    """Return stored VT link check results for current user."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        results = VTLinkCheck.get_by_user_id(
            user_id=user_id, limit=limit, offset=offset
        )
        return success_response(
            data={"results": results, "limit": limit, "offset": offset}
        )
    except Exception as e:
        logger.error(
            f"Error getting VT results [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error getting VirusTotal results", status_code=500
        )


@router.get(
    "/{email_id}/vt-results",
    summary="Get VirusTotal results for an email",
    description="Get stored VirusTotal link results for a specific email.",
    tags=["Emails"],
)
async def vt_results_by_email(
    request: Request,
    email_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_dependency),
):
    """Return VirusTotal link check results for one email, with ownership check."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        email = Email.get_by_id(email_id)
        if not email or email["user_id"] != user_id:
            return unauthorized_response("Access denied")
        results = VTLinkCheck.get_by_email_id(
            email_id=email_id, limit=limit, offset=offset
        )
        return success_response(
            data={"results": results, "limit": limit, "offset": offset}
        )
    except Exception as e:
        logger.error(
            f"Error getting VT results by email [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e),
            message="Error getting VirusTotal results for email",
            status_code=500,
        )


@router.post(
    "/{email_id}/vt-scan-now",
    summary="Run VirusTotal scan now for one email",
    description="Manually trigger VirusTotal scan immediately for a specific email.",
    tags=["Emails"],
)
async def vt_scan_now_by_email(
    request: Request, email_id: int, user_id: int = Depends(get_current_user_dependency)
):
    """Trigger manual VT scan for one email."""
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        email = Email.get_by_id(email_id)
        if not email or email["user_id"] != user_id:
            return unauthorized_response("Access denied")
        result = VirusTotalService.scan_single_email_links(
            user_id=user_id, email_id=email_id
        )
        VTScanLog.create(
            user_id=user_id,
            source="manual",
            checked=result["checked"],
            skipped=result["skipped"],
            errors=result["errors"],
            quota_remaining=result["quota_remaining"],
        )
        return success_response(
            data=result, message="VirusTotal scan completed for this email"
        )
    except Exception as e:
        logger.error(
            f"Error running VT scan now by email [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e),
            message="Error running VirusTotal scan for email",
            status_code=500,
        )


@router.get(
    "/{email_id}",
    summary="Get email details",
    description="Retrieve detailed information about a specific email, including its content and latest prediction result. Requires authentication and ownership of the email.",
    responses={
        200: {
            "description": "Email details retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": 1,
                            "user_id": 1,
                            "gmail_message_id": "abc123",
                            "subject": "Important: Verify Your Account",
                            "sender": "noreply@example.com",
                            "recipient": "user@example.com",
                            "body": "Please verify your account...",
                            "received_at": "2024-01-15T10:30:00Z",
                            "prediction": {
                                "id": 1,
                                "prediction": 1,
                                "probability": 0.95,
                                "is_phishing": True,
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Authentication required"}
                }
            },
        },
        404: {
            "description": "Email not found",
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Email not found"}
                }
            },
        },
        500: {
            "description": "Error retrieving email",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving email",
                    }
                }
            },
        },
    },
    tags=["Emails"],
)
async def get_email(
    request: Request, email_id: int, user_id: int = Depends(get_current_user_dependency)
):
    """
    Get email details.

    Returns complete information about a specific email including:
    - Email metadata (subject, sender, recipient, timestamps)
    - Email body content
    - Latest prediction result if available

    **Path Parameters:**
    - `email_id`: The ID of the email to retrieve
    """
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        logger.info(
            f"Email detail requested [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
        )
        email = EmailService.get_email_with_prediction(email_id)

        if not email:
            logger.warning(
                f"Email not found [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
            )
            return not_found_response("Email not found")

        if email["user_id"] != user_id:
            logger.warning(
                f"Email access denied [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
            )
            return unauthorized_response("Access denied")

        logger.info(
            f"Email detail retrieved [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data=email)
    except Exception as e:
        logger.error(
            f"Error retrieving email [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error retrieving email", status_code=500
        )


@router.get(
    "/{email_id}/predictions",
    summary="Get email predictions",
    description="Retrieve all prediction history for a specific email. Returns a list of all predictions made for the email, including historical predictions if the email was analyzed multiple times. Requires authentication and ownership of the email.",
    responses={
        200: {
            "description": "Email predictions retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "predictions": [
                                {
                                    "id": 1,
                                    "email_id": 123,
                                    "prediction": 1,
                                    "probability": 0.95,
                                    "model_version": "1.0.0",
                                    "created_at": "2024-01-15T10:40:00Z",
                                }
                            ]
                        },
                    }
                }
            },
        },
        401: {
            "description": "Authentication required or access denied",
            "content": {
                "application/json": {
                    "example": {"success": False, "message": "Access denied"}
                }
            },
        },
        500: {
            "description": "Error retrieving predictions",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving predictions",
                    }
                }
            },
        },
    },
    tags=["Emails"],
)
async def get_predictions(
    request: Request, email_id: int, user_id: int = Depends(get_current_user_dependency)
):
    """
    Get all predictions for an email.

    Returns the complete prediction history for a specific email.
    Useful for tracking how predictions may have changed over time
    or comparing different model versions.

    **Path Parameters:**
    - `email_id`: The ID of the email to get predictions for
    """
    request_id = getattr(request.state, "request_id", "unknown")

    try:
        logger.info(
            f"Email predictions requested [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
        )

        # Verify email belongs to user
        email = Email.get_by_id(email_id)
        if not email or email["user_id"] != user_id:
            logger.warning(
                f"Email predictions access denied [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
            )
            return unauthorized_response("Access denied")

        predictions = Prediction.get_by_email_id(email_id)
        logger.info(
            f"Email predictions retrieved: {len(predictions)} predictions [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]"
        )
        return success_response(data={"predictions": predictions})
    except Exception as e:
        logger.error(
            f"Error retrieving email predictions [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error retrieving predictions", status_code=500
        )


@router.get(
    "/{email_id}/attachments",
    summary="List attachments + VT scan results for an email",
    description=(
        "Returns each attachment row with its latest VirusTotal verdict (if any). "
        "Verdict is null for attachments not yet scanned."
    ),
    tags=["Emails"],
)
async def list_email_attachments(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        email = Email.get_by_id(email_id)
        if not email or email["user_id"] != user_id:
            return unauthorized_response("Access denied")

        attachments = EmailAttachment.get_by_email_id(email_id)
        result = []
        for att in attachments:
            scan = VTAttachmentCheck.get_by_attachment_id(att["id"])
            result.append(
                {
                    "id": att["id"],
                    "filename": att.get("filename"),
                    "mime_type": att.get("mime_type"),
                    "size": att.get("size"),
                    "sha256": att.get("sha256"),
                    "stored": bool(att.get("storage_path")),
                    "scan": scan,
                }
            )
        return success_response(data={"attachments": result})
    except Exception as e:
        logger.error(
            f"Error listing attachments [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error listing attachments", status_code=500
        )


@router.post(
    "/{email_id}/attachments/scan",
    summary="Trigger VirusTotal scan for an email's attachments",
    description=(
        "Submits each unscanned attachment to VirusTotal (hash lookup first; "
        "uploads files ≤32MB if VT has never seen them). Respects the daily quota."
    ),
    tags=["Emails"],
)
async def scan_email_attachments(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency),
):
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        result = VirusTotalService.scan_single_email_attachments(user_id, email_id)
        logger.info(
            f"Manual attachment scan [email_id={email_id}] [user_id={user_id}] "
            f"[request_id={request_id}] result={result}"
        )
        return success_response(data=result)
    except ValueError as e:
        return not_found_response(str(e))
    except Exception as e:
        logger.error(
            f"Error scanning attachments [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}",
            exc_info=True,
        )
        return error_response(
            error=str(e), message="Error scanning attachments", status_code=500
        )
