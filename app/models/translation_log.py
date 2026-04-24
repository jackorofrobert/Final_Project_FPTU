"""
TranslationLog model for AI translation analytics.
"""

from app.db.session import get_db


class TranslationLog:
    """translation_logs table — per-request translation metrics."""

    @staticmethod
    def create(
        user_id: int,
        source: str,
        *,
        email_id: int | None = None,
        success: bool = True,
        chunk_count: int = 0,
        source_chars: int = 0,
        translated_chars: int = 0,
        model: str = "",
        duration_ms: int = 0,
        urls_preserved: int = 0,
        error_message: str | None = None,
        translated_text: str | None = None,
    ) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO translation_logs (
                    user_id, source, email_id, success, chunk_count,
                    source_chars, translated_chars, model, duration_ms,
                    urls_preserved, error_message, translated_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    source,
                    email_id,
                    1 if success else 0,
                    chunk_count,
                    source_chars,
                    translated_chars,
                    model,
                    duration_ms,
                    urls_preserved,
                    error_message,
                    translated_text,
                ),
            )
            log_id = cursor.lastrowid
            cursor.execute("SELECT * FROM translation_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_latest_for_email(email_id: int) -> dict | None:
        """Return the most recent successful translation for a stored email."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, email_id, chunk_count, source_chars, translated_chars,
                       model, duration_ms, translated_text, created_at
                FROM translation_logs
                WHERE email_id = ? AND success = 1 AND translated_text IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (email_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM translation_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_stats_for_user(user_id: int) -> dict:
        """Aggregate stats for Sync Log / analytics cards."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_runs,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS success_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failure_count,
                    SUM(CASE WHEN success = 1 THEN source_chars ELSE 0 END) AS total_source_chars_ok,
                    SUM(CASE WHEN success = 1 THEN chunk_count ELSE 0 END) AS total_chunks_ok,
                    SUM(CASE WHEN success = 1 THEN urls_preserved ELSE 0 END) AS total_urls_preserved_ok,
                    MAX(created_at) AS last_translation_at
                FROM translation_logs
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {
                    "total_runs": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_source_chars_ok": 0,
                    "total_chunks_ok": 0,
                    "total_urls_preserved_ok": 0,
                    "last_translation_at": None,
                }
            d = dict(row)
            for key in (
                "total_runs",
                "success_count",
                "failure_count",
                "total_source_chars_ok",
                "total_chunks_ok",
                "total_urls_preserved_ok",
            ):
                if d.get(key) is None:
                    d[key] = 0
            return d
