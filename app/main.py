"""
FastAPI Application Factory
Creates and configures the FastAPI application instance.
"""
from pathlib import Path
import uuid
import time

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse

from app.api.v1.endpoints import auth, emails, predictions, history
from app.core.config import settings
from app.db.session import init_db
from app.utils.api_response import not_found_response, server_error_response
from app.utils.logger import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Application factory pattern for creating FastAPI app instances."""
    
    app = FastAPI(
        title="Phishing Email Detection API",
        description="""
        REST API for phishing email detection system with ML-based analysis.
        
        ## Features
        
        * **Email Management**: Fetch emails from Gmail and store them for analysis
        * **Phishing Detection**: Analyze emails using XGBoost ML model to detect phishing attempts
        * **Prediction History**: Track and review past predictions
        * **OAuth2 Authentication**: Secure authentication via Gmail OAuth2
        
        ## Authentication
        
        Most endpoints require authentication via OAuth2. Start by calling `/api/v1/auth/connect` to initiate the OAuth2 flow.
        
        ## API Documentation
        
        * **Swagger UI**: Available at `/docs` - Interactive API documentation
        * **ReDoc**: Available at `/redoc` - Alternative API documentation
        * **OpenAPI Schema**: Available at `/openapi.json` - Machine-readable API specification
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "API Support",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
        },
        tags_metadata=[
            {
                "name": "Authentication",
                "description": "OAuth2 authentication endpoints for Gmail integration. Handles user authentication and session management.",
            },
            {
                "name": "Emails",
                "description": "Email management endpoints. Fetch emails from Gmail, list stored emails, and retrieve email details.",
            },
            {
                "name": "Predictions",
                "description": "Phishing detection endpoints. Analyze email text or stored emails using the ML model to detect phishing attempts.",
            },
            {
                "name": "History",
                "description": "Prediction history endpoints. Retrieve past predictions and analysis results.",
            },
        ],
    )
    
    logger.info(f'Application starting in {settings.ENVIRONMENT} mode')
    
    # Configure CORS: use explicit origins from config (wildcard "*" is invalid with allow_credentials=True and credentials: 'include')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Configure session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=86400,  # 24 hours
        same_site=settings.SESSION_COOKIE_SAMESITE,
        https_only=settings.SESSION_COOKIE_SECURE
    )
    
    # Request/Response logging middleware
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        """Log incoming requests and responses."""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Store request ID in state for use in routes
        request.state.request_id = request_id
        
        # Safely get user_id from session if available
        user_id = None
        if "session" in request.scope:
            user_id = request.session.get('user_id')
        client_ip = request.client.host if request.client else 'unknown'
        
        logger.info(
            f'Request received: {request.method} {request.url.path} '
            f'[request_id={request_id}] [user_id={user_id}] [ip={client_ip}]'
        )
        
        try:
            response = await call_next(request)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Safely get user_id from session if available
            user_id = None
            if "session" in request.scope:
                user_id = request.session.get('user_id')
            
            logger.info(
                f'Response sent: {request.method} {request.url.path} '
                f'Status: {response.status_code} Time: {response_time:.2f}ms '
                f'[request_id={request_id}] [user_id={user_id}]'
            )
            
            return response
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(
                f'Request error: {request.method} {request.url.path} '
                f'Error: {str(e)} Time: {response_time:.2f}ms '
                f'[request_id={request_id}]',
                exc_info=True
            )
            raise
    
    # Initialize database
    logger.info('Initializing database')
    try:
        init_db()
        logger.info('Database initialized')
    except Exception as e:
        logger.error(f'Database initialization failed: {str(e)}', exc_info=True)
        raise
    
    # Register API routers
    app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(emails.router, prefix="/api/v1", tags=["Emails"])
    app.include_router(predictions.router, prefix="/api/v1", tags=["Predictions"])
    app.include_router(history.router, prefix="/api/v1", tags=["History"])
    
    logger.info('API routers registered')
    
    # Serve frontend static files (only for non-API routes)
    frontend_path = Path(__file__).parent.parent / 'frontend'
    
    @app.get("/", include_in_schema=False)
    async def serve_frontend_root():
        """Serve frontend index.html."""
        index_path = frontend_path / 'index.html'
        if index_path.exists():
            return FileResponse(str(index_path))
        return JSONResponse(content={"error": "Frontend not found"}, status_code=404)
    
    # Serve frontend static files (CSS, JS, etc.)
    if frontend_path.exists():
        @app.get("/{path:path}", include_in_schema=False)
        async def serve_frontend(path: str):
            """Serve frontend static files (fallback for SPA routing)."""
            # Don't serve API routes or docs
            if (path.startswith("api/") or path.startswith("docs") or 
                path.startswith("openapi.json") or path.startswith("redoc") or
                path.startswith("static/")):
                return JSONResponse(content={"error": "Not found"}, status_code=404)
            
            # Try to serve the requested file
            file_path = frontend_path / path
            if file_path.exists() and file_path.is_file():
                # Security check: ensure file is within frontend directory
                try:
                    file_path.resolve().relative_to(frontend_path.resolve())
                    return FileResponse(str(file_path))
                except ValueError:
                    # Path outside frontend directory - security issue
                    return JSONResponse(content={"error": "Not found"}, status_code=404)
            
            # Fallback to index.html for SPA routing
            index_path = frontend_path / 'index.html'
            if index_path.exists():
                return FileResponse(str(index_path))
            return JSONResponse(content={"error": "Not found"}, status_code=404)
    
    # Error handlers
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        logger.warning(f'404 Not Found: {request.url.path} [request_id={request_id}]')
        return not_found_response()
    
    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        """Handle 500 errors."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        logger.error(
            f'500 Internal Server Error: {request.url.path} '
            f'[request_id={request_id}] Error: {str(exc)}',
            exc_info=True
        )
        return server_error_response()
    
    logger.info('Application initialization complete')
    return app


# Create app instance for uvicorn
app = create_app()
