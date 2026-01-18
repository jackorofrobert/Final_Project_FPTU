"""
Database connection and session management.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def get_db():
    """
    Context manager for database connections.
    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    db_path = settings.DATABASE_PATH
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        logger.debug(f'Database connection established [db_path={db_path}]')
        try:
            yield conn
            conn.commit()
            logger.debug('Database transaction committed')
        except Exception as e:
            conn.rollback()
            logger.error(f'Database transaction rolled back: {str(e)}', exc_info=True)
            raise
    except sqlite3.Error as e:
        logger.error(f'Database connection error [db_path={db_path}]: {str(e)}', exc_info=True)
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            logger.debug('Database connection closed')


def init_db():
    """Initialize database with schema if it doesn't exist."""
    db_path = settings.DATABASE_PATH
    logger.info(f'Initializing database [db_path={db_path}]')
    
    # Create data directory if it doesn't exist
    if db_path != ':memory:':
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f'Database directory created/verified [db_path={db_path}]')
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Create users table
            logger.debug('Creating users table')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Create oauth_tokens table
            logger.debug('Creating oauth_tokens table')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Create emails table
            logger.debug('Creating emails table')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    gmail_message_id TEXT NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    recipient TEXT,
                    body TEXT,
                    received_at TIMESTAMP,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, gmail_message_id)
                )
            ''')
            
            # Create predictions table
            logger.debug('Creating predictions table')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER NOT NULL,
                    prediction INTEGER NOT NULL,
                    probability REAL NOT NULL,
                    model_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            logger.debug('Creating database indexes')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_user_id ON emails(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_gmail_id ON emails(gmail_message_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_email_id ON predictions(email_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_id ON oauth_tokens(user_id)')
            
        logger.info(f'Database initialization completed [db_path={db_path}]')
    except Exception as e:
        logger.error(f'Database initialization failed [db_path={db_path}]: {str(e)}', exc_info=True)
        raise
