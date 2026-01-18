"""
Logging utility module for FastAPI application.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings


def setup_logging():
    """
    Configure logging for the FastAPI application.
    """
    # Get logging configuration from settings
    log_level = settings.LOG_LEVEL
    log_file = settings.LOG_FILE
    log_max_bytes = settings.LOG_MAX_BYTES
    log_backup_count = settings.LOG_BACKUP_COUNT
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add console handler (always)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Prevent duplicate logs from uvicorn
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)


def get_logger(name):
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
