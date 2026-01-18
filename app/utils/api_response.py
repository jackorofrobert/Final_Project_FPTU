"""
API response utility functions for consistent JSON responses.
"""
from fastapi.responses import JSONResponse

def success_response(data=None, message=None, status_code=200):
    """
    Create a successful API response.
    
    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code
        
    Returns:
        FastAPI JSONResponse
    """
    response = {
        'success': True,
        'data': data
    }
    if message:
        response['message'] = message
    return JSONResponse(content=response, status_code=status_code)

def error_response(error=None, message=None, status_code=400):
    """
    Create an error API response.
    
    Args:
        error: Error details
        message: User-friendly error message
        status_code: HTTP status code
        
    Returns:
        FastAPI JSONResponse
    """
    response = {
        'success': False
    }
    if error:
        response['error'] = error
    if message:
        response['message'] = message
    return JSONResponse(content=response, status_code=status_code)

def unauthorized_response(message='Authentication required'):
    """Create an unauthorized (401) response."""
    return error_response(message=message, status_code=401)

def not_found_response(message='Resource not found'):
    """Create a not found (404) response."""
    return error_response(message=message, status_code=404)

def server_error_response(message='Internal server error', error=None):
    """Create a server error (500) response."""
    return error_response(error=error, message=message, status_code=500)
