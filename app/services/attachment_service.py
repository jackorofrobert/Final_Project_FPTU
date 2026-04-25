"""
Attachment storage service.

Persists email attachments to disk (under settings.ATTACHMENT_DIR) and writes
metadata to the email_attachments table. Bytes are saved keyed by sha256 so
two emails carrying the same file share one blob; the DB row references the
storage path.

Flow when ingesting an email:

    parsed_attachments = mail_api_service._parse_attachments(message)
    AttachmentService.persist_for_email(user_id, email_id, uid, parsed_attachments)
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from app.core.config import settings
from app.models import EmailAttachment
from app.services.mail_api_service import MailApiService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AttachmentService:
    """Persist + retrieve attachment blobs."""

    # ------------------------------------------------------------------ #
    # Disk helpers                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _root() -> Path:
        root = Path(settings.ATTACHMENT_DIR)
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _blob_path(email_id: int, sha256: str, filename: str) -> Path:
        # Keep the original extension to make manual triage easier; truncate
        # filename to avoid path-length issues.
        ext = Path(filename or "").suffix[:16]
        safe_name = f"{sha256}{ext}" if ext else sha256
        d = AttachmentService._root() / str(email_id)
        d.mkdir(parents=True, exist_ok=True)
        return d / safe_name

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def persist_for_email(
        user_id: int,
        email_id: int,
        message_uid,
        attachments: list[dict],
    ) -> list[dict]:
        """Save each attachment dict to disk + DB.

        Each entry should follow the shape returned by
        ``MailApiService._parse_attachments``. When ``content_b64`` is missing
        we fall back to ``MailApiService.fetch_attachment_content`` using the
        ``attachment_id`` (or message uid) so the parser can keep working with
        servers that don't inline attachment bytes.
        """
        if not attachments:
            return []

        saved: list[dict] = []
        for att in attachments:
            try:
                row = AttachmentService._persist_one(
                    user_id=user_id,
                    email_id=email_id,
                    message_uid=message_uid,
                    att=att,
                )
                if row:
                    saved.append(row)
            except Exception as exc:
                logger.warning(
                    f"Skip attachment [email_id={email_id}] "
                    f"[filename={att.get('filename')}]: {exc}"
                )
        return saved

    @staticmethod
    def reload_for_email(user_id: int, email: dict) -> dict:
        """Fetch the message again from mail API and persist attachment blobs."""
        message_uid = email.get("gmail_message_id")
        if message_uid is None:
            raise ValueError("Email does not have a mail UID")

        email_data = MailApiService.fetch_message(user_id, message_uid)
        attachments = email_data.get("attachments") or []
        saved = AttachmentService.persist_for_email(
            user_id=user_id,
            email_id=email["id"],
            message_uid=email_data.get("uid") or message_uid,
            attachments=attachments,
        )

        removed_placeholders = 0
        for row in saved:
            if row.get("storage_path"):
                removed_placeholders += EmailAttachment.delete_metadata_only_matches(
                    email_id=email["id"],
                    filename=row.get("filename") or "attachment.bin",
                    mime_type=row.get("mime_type") or "application/octet-stream",
                    size=int(row.get("size") or 0),
                    keep_id=row["id"],
                )

        stored = sum(1 for row in saved if row.get("storage_path"))
        metadata_only = len(saved) - stored
        return {
            "found": len(attachments),
            "saved": len(saved),
            "stored": stored,
            "metadata_only": metadata_only,
            "removed_placeholders": removed_placeholders,
        }

    @staticmethod
    def _persist_one(
        user_id: int, email_id: int, message_uid, att: dict
    ) -> dict | None:
        filename = att.get("filename") or "attachment.bin"
        mime_type = att.get("mime_type") or "application/octet-stream"
        declared_size = int(att.get("size") or 0)

        # 1. Resolve raw bytes — inline first, otherwise fetch.
        content_b64 = att.get("content_b64")
        raw: bytes | None = None
        if content_b64:
            try:
                raw = base64.b64decode(content_b64)
            except Exception:
                raw = None

        if raw is None and att.get("attachment_index") is not None:
            raw = MailApiService.fetch_attachment_content(
                user_id=user_id,
                message_uid=message_uid,
                attachment_index=att["attachment_index"],
                filename=filename,
            )

        # 2. Even with no bytes we keep metadata so the UI can show the
        #    attachment exists. Use a stable surrogate hash so the row is
        #    unique per-email.
        if raw is None:
            surrogate = f"{filename}:{mime_type}:{declared_size}:{message_uid}"
            sha256 = hashlib.sha256(surrogate.encode("utf-8")).hexdigest()
            return EmailAttachment.upsert(
                email_id=email_id,
                filename=filename,
                mime_type=mime_type,
                size=declared_size,
                sha256=sha256,
                storage_path=None,
            )

        # 3. We have bytes — write to disk under sha256.
        size = len(raw)
        if size > settings.ATTACHMENT_MAX_SIZE_BYTES:
            logger.info(
                f"Attachment exceeds max size, storing metadata only "
                f"[email_id={email_id}] [filename={filename}] [size={size}]"
            )
            sha256 = hashlib.sha256(raw).hexdigest()
            return EmailAttachment.upsert(
                email_id=email_id,
                filename=filename,
                mime_type=mime_type,
                size=size,
                sha256=sha256,
                storage_path=None,
            )

        sha256 = hashlib.sha256(raw).hexdigest()
        path = AttachmentService._blob_path(email_id, sha256, filename)
        if not path.exists():
            path.write_bytes(raw)

        return EmailAttachment.upsert(
            email_id=email_id,
            filename=filename,
            mime_type=mime_type,
            size=size,
            sha256=sha256,
            storage_path=str(path),
        )

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def read_blob(attachment_row: dict) -> bytes | None:
        path = attachment_row.get("storage_path")
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        return p.read_bytes()
