"""
Prediction endpoints for ML prediction API routes.
"""
import time
from datetime import datetime

from fastapi import APIRouter, Request, Depends

from app.core.dependencies import get_current_user_dependency, get_optional_user_dependency
from app.models import Email
from app.schemas.prediction import PredictionRequest
from app.services.email_service import EmailService
from app.services.prediction_service import PredictionService
from app.utils.api_response import success_response, error_response, unauthorized_response, not_found_response
from app.utils.logger import get_logger

router = APIRouter(prefix="/predictions")
logger = get_logger(__name__)


@router.post(
    "/analyze",
    summary="Analyze email text",
    description="Analyze email text for phishing detection using the ML model. This endpoint accepts raw email text and returns a prediction result. Authentication is optional - if authenticated, the prediction is saved to the database.",
    responses={
        200: {
            "description": "Email analyzed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "prediction": 1,
                            "probability": 0.95,
                            "threshold": 0.5,
                            "email_id": 123,
                            "is_phishing": True
                        },
                        "message": "Email analyzed successfully"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request - missing email text",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Email text is required"
                    }
                }
            }
        },
        500: {
            "description": "Error analyzing email",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Prediction service error",
                        "message": "Error analyzing email"
                    }
                }
            }
        }
    },
    tags=["Predictions"]
)
async def analyze(
    request: Request,
    prediction_request: PredictionRequest,
    user_id: int = Depends(get_optional_user_dependency)
):
    """
    Analyze email text (manual input).
    
    Performs phishing detection analysis on the provided email text.
    The ML model analyzes the content and returns:
    - Prediction: 0 (benign) or 1 (phishing)
    - Probability: Confidence score (0.0 to 1.0)
    - Threshold: Classification threshold used
    
    If the user is authenticated, the prediction is saved to the database.
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        email_text = prediction_request.email_text.strip()
        
        if not email_text:
            logger.warning(f'Prediction request missing email_text [request_id={request_id}]')
            return error_response(message='Email text is required', status_code=400)
        
        logger.info(f'Prediction requested (manual input) [user_id={user_id}] [text_length={len(email_text)}] [request_id={request_id}]')
        
        # Get prediction with additional features
        result = PredictionService.predict(
            email_text=email_text,
            subject=prediction_request.subject,
            has_attachment=prediction_request.has_attachment,
            links_count=prediction_request.links_count,
            sender_domain=prediction_request.sender_domain,
            urgent_keywords=prediction_request.urgent_keywords
        )
        
        logger.info(
            f'Prediction completed: prediction={result["prediction"]} '
            f'probability={result["probability"]:.4f} threshold={result["threshold"]} '
            f'[user_id={user_id}] [request_id={request_id}]'
        )
        
        # Optionally save to database if user is logged in
        email_id = None
        if user_id:
            # Create a temporary email record for manual analysis
            email_record = Email.create(
                user_id=user_id,
                gmail_message_id=f'manual_{int(time.time())}',
                subject='Manual Analysis',
                sender='',
                recipient='',
                body=email_text,
                received_at=datetime.now().isoformat()
            )
            email_id = email_record['id']
            
            # Save prediction
            EmailService.create_prediction(
                email_id,
                result['prediction'],
                result['probability'],
                PredictionService.get_model_version()
            )
            logger.info(f'Prediction saved to database [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
        
        return success_response(data={
            'prediction': result['prediction'],
            'probability': result['probability'],
            'ensemble_score': result.get('ensemble_score', result['probability']),
            'threshold': result['threshold'],
            'email_id': email_id,
            'is_phishing': result['prediction'] == 1,
            'features': result.get('features', {})
        }, message='Email analyzed successfully')
    except Exception as e:
        logger.error(f'Error analyzing email [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error analyzing email', status_code=500)


@router.post(
    "/analyze-email/{email_id}",
    summary="Analyze stored email",
    description="Analyze a stored email from the database for phishing detection. The email must belong to the authenticated user. The prediction result is saved to the database.",
    responses={
        200: {
            "description": "Email analyzed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "prediction": {
                                "id": 1,
                                "email_id": 123,
                                "prediction": 1,
                                "probability": 0.95,
                                "model_version": "1.0.0",
                                "created_at": "2024-01-15T10:40:00Z"
                            },
                            "result": {
                                "prediction": 1,
                                "probability": 0.95,
                                "threshold": 0.5
                            },
                            "is_phishing": True
                        },
                        "message": "Email analyzed successfully"
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
            "description": "Error analyzing email",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Prediction service error",
                        "message": "Error analyzing email"
                    }
                }
            }
        }
    },
    tags=["Predictions"]
)
async def analyze_email(
    request: Request,
    email_id: int,
    user_id: int = Depends(get_current_user_dependency)
):
    """
    Analyze a stored email.
    
    Performs phishing detection analysis on an email that has been stored in the database.
    The email must belong to the authenticated user.
    
    **Path Parameters:**
    - `email_id`: The ID of the stored email to analyze
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f'Email prediction requested [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
        email = EmailService.get_email_by_id(email_id)
        
        if not email:
            logger.warning(f'Email not found for prediction [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
            return not_found_response('Email not found')
        
        if email['user_id'] != user_id:
            logger.warning(f'Email prediction access denied [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]')
            return unauthorized_response('Access denied')
        
        # Get prediction
        result = PredictionService.predict(email['body'])
        
        logger.info(
            f'Email prediction completed: prediction={result["prediction"]} '
            f'probability={result["probability"]:.4f} threshold={result["threshold"]} '
            f'[email_id={email_id}] [user_id={user_id}] [request_id={request_id}]'
        )
        
        # Save prediction
        prediction = EmailService.create_prediction(
            email_id,
            result['prediction'],
            result['probability'],
            PredictionService.get_model_version()
        )
        
        logger.info(f'Email prediction saved [email_id={email_id}] [prediction_id={prediction["id"]}] [user_id={user_id}] [request_id={request_id}]')
        
        return success_response(data={
            'prediction': prediction,
            'result': result,
            'is_phishing': result['prediction'] == 1
        }, message='Email analyzed successfully')
    except Exception as e:
        logger.error(f'Error analyzing email [email_id={email_id}] [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error analyzing email', status_code=500)
