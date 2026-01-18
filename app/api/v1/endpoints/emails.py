"""
Email endpoints for email API routes.
"""
from fastapi import APIRouter, Request, Depends, Query

from app.core.dependencies import get_current_user_dependency
from app.models import Email, Prediction
from app.schemas.email import EmailFetchRequest
from app.services.email_service import EmailService
from app.services.gmail_service import GmailService
from app.utils.api_response import success_response, error_response, unauthorized_response, not_found_response
from app.utils.logger import get_logger

router = APIRouter(prefix="/emails")
logger = get_logger(__name__)


@router.post(
    "/fetch",
    summary="Fetch emails from Gmail",
    description="Fetch emails from the authenticated user's Gmail account using the Gmail API. Emails are fetched and stored in the database for analysis. Requires authentication.",
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
                                    "recipient": "recipient@example.com"
                                }
                            ]
                        },
                        "message": "Successfully fetched and stored 3 emails"
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
        },
        500: {
            "description": "Error fetching emails",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Gmail API error",
                        "message": "Error fetching emails"
                    }
                }
            }
        }
    },
    tags=["Emails"]
)
async def fetch(
    request: Request,
    fetch_request: EmailFetchRequest = EmailFetchRequest(),
    user_id: int = Depends(get_current_user_dependency)
):
    """
    Fetch emails from Gmail API.
    
    Retrieves emails from the user's Gmail inbox and stores them in the database.
    The number of emails fetched is limited by the max_results parameter (default: 50, max: 500).
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        max_results = min(fetch_request.max_results, 500)  # Cap at 500
        logger.info(f'Email fetch requested [user_id={user_id}] [max_results={max_results}] [request_id={request_id}]')
        
        emails = GmailService.fetch_emails(user_id, max_results=max_results)
        
        # Store emails in database
        stored_count = 0
        stored_emails = []
        for email_data in emails:
            email = EmailService.create_email(
                user_id=user_id,
                gmail_message_id=email_data['gmail_message_id'],
                subject=email_data['subject'],
                sender=email_data['sender'],
                recipient=email_data['recipient'],
                body=email_data['body'],
                received_at=email_data['received_at']
            )
            stored_emails.append(email)
            stored_count += 1
        
        logger.info(f'Email fetch completed: {stored_count} emails stored [user_id={user_id}] [request_id={request_id}]')
        return success_response(data={
            'count': stored_count,
            'emails': stored_emails
        }, message=f'Successfully fetched and stored {stored_count} emails')
    except Exception as e:
        logger.error(f'Error fetching emails [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error fetching emails', status_code=500)


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
                                    "prediction": None
                                }
                            ],
                            "limit": 50,
                            "offset": 0
                        }
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
        },
        500: {
            "description": "Error retrieving email list",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving emails"
                    }
                }
            }
        }
    },
    tags=["Emails"]
)
async def list_emails(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Number of emails to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of emails to skip for pagination"),
    user_id: int = Depends(get_current_user_dependency)
):
    """
    Get list of stored emails.
    
    Returns a paginated list of emails for the authenticated user.
    Each email includes its latest prediction result if available.
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f'Email list requested [user_id={user_id}] [limit={limit}] [offset={offset}] [request_id={request_id}]')
        
        emails = EmailService.get_emails_by_user(user_id, limit=limit, offset=offset)
        
        # Get latest prediction for each email
        for email in emails:
            email_with_pred = EmailService.get_email_with_prediction(email['id'])
            if email_with_pred and email_with_pred.get('prediction'):
                email['prediction'] = email_with_pred['prediction']
            else:
                email['prediction'] = None
        
        logger.info(f'Email list retrieved: {len(emails)} emails [user_id={user_id}] [request_id={request_id}]')
        return success_response(data={
            'emails': emails,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f'Error retrieving email list [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error retrieving emails', status_code=500)


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
                                "is_phishing": True
                            }
                        }
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
        },
        404: {
            "description": "Email not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Email not found"
                    }
                }
            }
        },
        500: {
            "description": "Error retrieving email",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving email"
                    }
                }
            }
        }
    },
    tags=["Emails"]
)
async def get_email(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency)
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
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f'Email detail requested [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
        email = EmailService.get_email_with_prediction(email_id)
        
        if not email:
            logger.warning(f'Email not found [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
            return not_found_response('Email not found')
        
        if email['user_id'] != user_id:
            logger.warning(f'Email access denied [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
            return unauthorized_response('Access denied')
        
        logger.info(f'Email detail retrieved [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
        return success_response(data=email)
    except Exception as e:
        logger.error(f'Error retrieving email [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error retrieving email', status_code=500)


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
                                    "created_at": "2024-01-15T10:40:00Z"
                                }
                            ]
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication required or access denied",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Access denied"
                    }
                }
            }
        },
        500: {
            "description": "Error retrieving predictions",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving predictions"
                    }
                }
            }
        }
    },
    tags=["Emails"]
)
async def get_predictions(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency)
):
    """
    Get all predictions for an email.
    
    Returns the complete prediction history for a specific email.
    Useful for tracking how predictions may have changed over time
    or comparing different model versions.
    
    **Path Parameters:**
    - `email_id`: The ID of the email to get predictions for
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f'Email predictions requested [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
        
        # Verify email belongs to user
        email = Email.get_by_id(email_id)
        if not email or email['user_id'] != user_id:
            logger.warning(f'Email predictions access denied [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
            return unauthorized_response('Access denied')
        
        predictions = Prediction.get_by_email_id(email_id)
        logger.info(f'Email predictions retrieved: {len(predictions)} predictions [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
        return success_response(data={'predictions': predictions})
    except Exception as e:
        logger.error(f'Error retrieving email predictions [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error retrieving predictions', status_code=500)
