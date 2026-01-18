"""
History endpoints for prediction history API routes.
"""
from fastapi import APIRouter, Request, Depends, Query
from app.core.dependencies import get_current_user_dependency
from app.models import Prediction, Email
from app.utils.api_response import success_response, error_response, unauthorized_response
from app.utils.logger import get_logger

router = APIRouter(prefix="/history")
logger = get_logger(__name__)


@router.get(
    "/predictions",
    summary="Get prediction history",
    description="Retrieve a paginated list of prediction history for the authenticated user. Each prediction includes the email details and prediction results. Useful for reviewing past analyses and tracking prediction trends.",
    responses={
        200: {
            "description": "Prediction history retrieved successfully",
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
                                    "email": {
                                        "id": 123,
                                        "subject": "Verify Your Account",
                                        "sender": "noreply@example.com"
                                    }
                                }
                            ],
                            "limit": 100,
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
            "description": "Error retrieving prediction history",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Database error",
                        "message": "Error retrieving prediction history"
                    }
                }
            }
        }
    },
    tags=["History"]
)
async def get_predictions(
    request: Request,
    limit: int = Query(100, ge=1, le=500, description="Number of predictions to return (1-500)"),
    offset: int = Query(0, ge=0, description="Number of predictions to skip for pagination"),
    user_id: int = Depends(get_current_user_dependency)
):
    """
    Get prediction history.
    
    Returns a paginated list of all predictions made by the authenticated user.
    Each prediction includes:
    - Prediction result and probability
    - Model version used
    - Associated email details
    - Timestamp of the prediction
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        logger.info(f'Prediction history requested [user_id={user_id}] [limit={limit}] [offset={offset}] [request_id={request_id}]')
        
        predictions_list = Prediction.get_by_user_id(user_id, limit=limit, offset=offset)
        
        # Enrich with email information
        for pred in predictions_list:
            email = Email.get_by_id(pred['email_id'])
            pred['email'] = email
        
        logger.info(f'Prediction history retrieved: {len(predictions_list)} predictions [user_id={user_id}] [request_id={request_id}]')
        return success_response(data={
            'predictions': predictions_list,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f'Error retrieving prediction history [user_id={user_id}] [request_id={request_id}]: {str(e)}', exc_info=True)
        return error_response(error=str(e), message='Error retrieving prediction history', status_code=500)
