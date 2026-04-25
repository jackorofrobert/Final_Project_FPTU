"""
EmailAttachment model — file metadata + on-disk blob path per email attachment.
"""

from app.db.session import get_db


class EmailAttachment:
    """Model for the email_attachments table."""

    @staticmethod
    def upsert(
        email_id: int,
        filename: str,
        mime_type: str,
        size: int,
        sha256: str,
        storage_path: str | None,
    ) -> dict:
        """Insert or update (keyed on email_id + sha256) and return the row."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO email_attachments
                       (email_id, filename, mime_type, size, sha256, storage_path)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(email_id, sha256) DO UPDATE SET
                     filename     = excluded.filename,
                     mime_type    = excluded.mime_type,
                     size         = excluded.size,
                     storage_path = COALESCE(excluded.storage_path, email_attachments.storage_path)""",
                (email_id, filename, mime_type, size, sha256, storage_path),
            )
            cursor.execute(
                "SELECT * FROM email_attachments WHERE email_id = ? AND sha256 = ?",
                (email_id, sha256),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(attachment_id: int) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM email_attachments WHERE id = ?", (attachment_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_email_id(email_id: int) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM email_attachments
                   WHERE email_id = ?
                   ORDER BY id ASC""",
                (email_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def count_by_email_id(email_id: int) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM email_attachments WHERE email_id = ?",
                (email_id,),
            )
            return cursor.fetchone()[0]

    @staticmethod
    def get_unscanned_for_user(user_id: int, limit: int = 100) -> list[dict]:
        """Return attachments for *user_id* that have no successful VT scan yet.

        Pending/error rows are returned so the scheduler can retry.
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT a.*
                   FROM email_attachments a
                   JOIN emails e ON a.email_id = e.id
                   LEFT JOIN vt_attachment_checks v
                     ON v.attachment_id = a.id AND v.status = 'success'
                   WHERE e.user_id = ? AND v.id IS NULL
                   ORDER BY a.created_at ASC
                   LIMIT ?""",
                (user_id, limit),
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_summaries_for_emails(email_ids: list[int]) -> dict[int, dict]:
        """Batch summary {email_id: {total, malicious, suspicious, has_pending}}."""
        if not email_ids:
            return {}
        placeholders = ",".join("?" * len(email_ids))
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT a.email_id,
                           COUNT(a.id)                           AS total,
                           COALESCE(SUM(v.malicious), 0)          AS total_malicious,
                           COALESCE(SUM(v.suspicious), 0)         AS total_suspicious,
                           SUM(CASE WHEN v.status = 'pending_scan' THEN 1 ELSE 0 END) AS pending_count,
                           SUM(CASE WHEN v.id IS NULL THEN 1 ELSE 0 END)              AS unscanned_count
                    FROM email_attachments a
                    LEFT JOIN vt_attachment_checks v ON v.attachment_id = a.id
                    WHERE a.email_id IN ({placeholders})
                    GROUP BY a.email_id""",
                email_ids,
            )
            result = {}
            for row in cursor.fetchall():
                result[row["email_id"]] = {
                    "total": int(row["total"] or 0),
                    "total_malicious": int(row["total_malicious"] or 0),
                    "total_suspicious": int(row["total_suspicious"] or 0),
                    "has_pending": (row["pending_count"] or 0) > 0
                    or (row["unscanned_count"] or 0) > 0,
                }
            return result
