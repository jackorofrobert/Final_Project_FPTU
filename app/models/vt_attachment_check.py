"""
VTAttachmentCheck — VirusTotal verdicts per email attachment.

Mirrors the design of VTLinkCheck. Keyed on attachment_id (UNIQUE).
"""

from datetime import datetime

from app.db.session import get_db


class VTAttachmentCheck:
    """Model for the vt_attachment_checks table."""

    @staticmethod
    def exists_success(attachment_id: int) -> bool:
        """True only when the attachment already has a completed successful scan."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM vt_attachment_checks WHERE attachment_id = ? AND status = 'success' LIMIT 1",
                (attachment_id,),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def upsert(
        user_id: int,
        email_id: int,
        attachment_id: int,
        sha256: str,
        status: str,
        malicious: int = 0,
        suspicious: int = 0,
        harmless: int = 0,
        undetected: int = 0,
        error_message: str | None = None,
    ) -> None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO vt_attachment_checks
                       (user_id, email_id, attachment_id, sha256, status,
                        malicious, suspicious, harmless, undetected,
                        last_checked_at, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(attachment_id) DO UPDATE SET
                     status          = excluded.status,
                     malicious       = excluded.malicious,
                     suspicious      = excluded.suspicious,
                     harmless        = excluded.harmless,
                     undetected      = excluded.undetected,
                     last_checked_at = excluded.last_checked_at,
                     error_message   = excluded.error_message""",
                (
                    user_id,
                    email_id,
                    attachment_id,
                    sha256,
                    status,
                    malicious,
                    suspicious,
                    harmless,
                    undetected,
                    datetime.now().isoformat(),
                    error_message,
                ),
            )

    @staticmethod
    def get_by_attachment_id(attachment_id: int) -> dict | None:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM vt_attachment_checks WHERE attachment_id = ?",
                (attachment_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_email_id(email_id: int) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM vt_attachment_checks
                   WHERE email_id = ?
                   ORDER BY last_checked_at DESC""",
                (email_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_user_overview(user_id: int) -> dict:
        """Aggregate {total_attachments, scanned, malicious, suspicious, pending}."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT
                       COUNT(a.id)                                                AS total_attachments,
                       COUNT(v.id)                                                AS total_scanned,
                       COALESCE(SUM(v.malicious), 0)                              AS malicious_attachments,
                       COALESCE(SUM(v.suspicious), 0)                             AS suspicious_attachments,
                       SUM(CASE WHEN v.malicious > 0 THEN 1 ELSE 0 END)           AS malicious_files,
                       SUM(CASE WHEN v.suspicious > 0 AND v.malicious = 0 THEN 1 ELSE 0 END) AS suspicious_files,
                       SUM(CASE WHEN v.status = 'pending_scan' THEN 1 ELSE 0 END) AS pending_files
                   FROM email_attachments a
                   JOIN emails e ON a.email_id = e.id
                   LEFT JOIN vt_attachment_checks v ON v.attachment_id = a.id
                   WHERE e.user_id = ?""",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {}
            return {
                "total_attachments": int(row["total_attachments"] or 0),
                "scanned_attachments": int(row["total_scanned"] or 0),
                "malicious_files": int(row["malicious_files"] or 0),
                "suspicious_files": int(row["suspicious_files"] or 0),
                "pending_files": int(row["pending_files"] or 0),
                "total_malicious_votes": int(row["malicious_attachments"] or 0),
                "total_suspicious_votes": int(row["suspicious_attachments"] or 0),
            }
