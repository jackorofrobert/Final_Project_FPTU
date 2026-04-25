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
        logger.debug(f"Database connection established [db_path={db_path}]")
        try:
            yield conn
            conn.commit()
            logger.debug("Database transaction committed")
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction rolled back: {str(e)}", exc_info=True)
            raise
    except sqlite3.Error as e:
        logger.error(
            f"Database connection error [db_path={db_path}]: {str(e)}", exc_info=True
        )
        raise
    finally:
        if "conn" in locals():
            conn.close()
            logger.debug("Database connection closed")


def init_db():
    """Initialize database with schema if it doesn't exist."""
    db_path = settings.DATABASE_PATH
    logger.info(f"Initializing database [db_path={db_path}]")

    # Create data directory if it doesn't exist
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Database directory created/verified [db_path={db_path}]")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Create users table
            logger.debug("Creating users table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    last_fetch_at TIMESTAMP,
                    last_analysis_at TIMESTAMP
                )
            """)

            # Migration: add new columns if missing (existing DBs)
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            if "last_fetch_at" not in columns:
                logger.info("Migrating users table: adding last_fetch_at column")
                cursor.execute("ALTER TABLE users ADD COLUMN last_fetch_at TIMESTAMP")
            if "last_analysis_at" not in columns:
                logger.info("Migrating users table: adding last_analysis_at column")
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN last_analysis_at TIMESTAMP"
                )

            # Create oauth_tokens table
            logger.debug("Creating oauth_tokens table")
            cursor.execute("""
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
            """)

            # Create emails table
            logger.debug("Creating emails table")
            cursor.execute("""
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
            """)

            # Create predictions table
            logger.debug("Creating predictions table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER NOT NULL,
                    prediction INTEGER NOT NULL,
                    probability REAL NOT NULL,
                    ensemble_score REAL,
                    classification TEXT,
                    threshold REAL,
                    suspicious_margin REAL,
                    model_version TEXT,
                    input_source TEXT NOT NULL DEFAULT 'original',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("PRAGMA table_info(predictions)")
            pred_columns = [col[1] for col in cursor.fetchall()]
            if "input_source" not in pred_columns:
                logger.info("Migrating predictions table: adding input_source column")
                cursor.execute(
                    "ALTER TABLE predictions ADD COLUMN input_source TEXT NOT NULL DEFAULT 'original'"
                )

            # Create prediction_features table (extracted features)
            logger.debug("Creating prediction_features table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER NOT NULL,
                    links_count INTEGER,
                    has_attachment INTEGER,
                    urgent_keywords INTEGER,
                    sender_domain TEXT,
                    sender_risk TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE
                )
            """)

            # Create prediction_links table (detailed link analysis)
            logger.debug("Creating prediction_links table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    domain TEXT,
                    link_type TEXT,
                    risk_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE
                )
            """)

            # Create suspicious_segments table (text segments analysis)
            logger.debug("Creating suspicious_segments table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suspicious_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    score REAL NOT NULL,
                    severity TEXT,
                    reasons TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE
                )
            """)

            # Create fetch_logs table (tracks each email fetch event)
            logger.debug("Creating fetch_logs table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fetch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    emails_fetched INTEGER NOT NULL DEFAULT 0,
                    new_emails INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create analysis_logs table (tracks each auto-analysis event)
            logger.debug("Creating analysis_logs table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    emails_analyzed INTEGER NOT NULL DEFAULT 0,
                    emails_skipped INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create email_attachments table (per-email attachment metadata + blob path)
            logger.debug("Creating email_attachments table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id INTEGER NOT NULL,
                    filename TEXT,
                    mime_type TEXT,
                    size INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL,
                    storage_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
                    UNIQUE(email_id, sha256)
                )
            """)

            # Create vt_attachment_checks table (per-attachment VT verdicts)
            logger.debug("Creating vt_attachment_checks table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vt_attachment_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email_id INTEGER NOT NULL,
                    attachment_id INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    malicious INTEGER DEFAULT 0,
                    suspicious INTEGER DEFAULT 0,
                    harmless INTEGER DEFAULT 0,
                    undetected INTEGER DEFAULT 0,
                    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
                    FOREIGN KEY (attachment_id) REFERENCES email_attachments(id) ON DELETE CASCADE,
                    UNIQUE(attachment_id)
                )
            """)

            # Create vt_link_checks table (tracks VirusTotal checks per email-link)
            logger.debug("Creating vt_link_checks table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vt_link_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    url_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    malicious INTEGER DEFAULT 0,
                    suspicious INTEGER DEFAULT 0,
                    harmless INTEGER DEFAULT 0,
                    undetected INTEGER DEFAULT 0,
                    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
                    UNIQUE(email_id, url_hash)
                )
            """)

            # Create vt_daily_usage table (global daily API quota tracking)
            logger.debug("Creating vt_daily_usage table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vt_daily_usage (
                    usage_date TEXT PRIMARY KEY,
                    request_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create vt_scan_logs table (tracks scheduler runs)
            logger.debug("Creating vt_scan_logs table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vt_scan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL DEFAULT 'scheduler',
                    checked INTEGER NOT NULL DEFAULT 0,
                    skipped INTEGER NOT NULL DEFAULT 0,
                    errors INTEGER NOT NULL DEFAULT 0,
                    quota_remaining INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("PRAGMA table_info(vt_scan_logs)")
            vt_log_columns = [col[1] for col in cursor.fetchall()]
            if "source" not in vt_log_columns:
                logger.info("Migrating vt_scan_logs table: adding source column")
                cursor.execute(
                    "ALTER TABLE vt_scan_logs ADD COLUMN source TEXT NOT NULL DEFAULT 'scheduler'"
                )

            # Translation analytics (Gemini / AI Studio)
            logger.debug("Creating translation_logs table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    email_id INTEGER,
                    success INTEGER NOT NULL DEFAULT 1,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    source_chars INTEGER NOT NULL DEFAULT 0,
                    translated_chars INTEGER NOT NULL DEFAULT 0,
                    model TEXT NOT NULL DEFAULT '',
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    urls_preserved INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    translated_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("PRAGMA table_info(translation_logs)")
            tl_cols = [col[1] for col in cursor.fetchall()]
            if "translated_text" not in tl_cols:
                logger.info(
                    "Migrating translation_logs table: adding translated_text column"
                )
                cursor.execute(
                    "ALTER TABLE translation_logs ADD COLUMN translated_text TEXT"
                )

            # Create indexes for better performance
            logger.debug("Creating database indexes")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_emails_user_id ON emails(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_emails_gmail_id ON emails(gmail_message_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_predictions_email_id ON predictions(email_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_id ON oauth_tokens(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_prediction_features_prediction_id ON prediction_features(prediction_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_prediction_links_prediction_id ON prediction_links(prediction_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_suspicious_segments_prediction_id ON suspicious_segments(prediction_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_fetch_logs_user_id ON fetch_logs(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_analysis_logs_user_id ON analysis_logs(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_link_checks_user_id ON vt_link_checks(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_link_checks_email_id ON vt_link_checks(email_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_link_checks_url_hash ON vt_link_checks(url_hash)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_scan_logs_user_id ON vt_scan_logs(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_translation_logs_user_id ON translation_logs(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_attachments_email_id ON email_attachments(email_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_attachments_sha256 ON email_attachments(sha256)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_attachment_checks_user_id ON vt_attachment_checks(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_attachment_checks_email_id ON vt_attachment_checks(email_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_vt_attachment_checks_sha256 ON vt_attachment_checks(sha256)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_translation_logs_user_created "
                "ON translation_logs(user_id, created_at DESC)"
            )

        logger.info(f"Database initialization completed [db_path={db_path}]")
    except Exception as e:
        logger.error(
            f"Database initialization failed [db_path={db_path}]: {str(e)}",
            exc_info=True,
        )
        raise
