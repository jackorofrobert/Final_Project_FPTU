"""
Mail API service — replaces Gmail API integration.

Connects to the custom mail-api server (port 8095) backed by Maddy IMAP.
Reads all mail from the archive journal mailbox (archive@spktfpt.online).

Auth flow:
  login()   → POST /api/auth/token   → accessToken + refreshToken + tokenId
  refresh() → POST /api/auth/refresh  → rotate tokens
  revoke()  → POST /api/auth/revoke   → logout

Email fetch flow:
  POST /api/mail/list    → list UIDs in INBOX
  POST /api/mail/message → fetch full message per UID
"""

import json
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

FOLDER = "INBOX"


class MailApiService:
    """Service for the custom mail-api (port 8095)."""

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _base_headers() -> dict:
        """Return the mandatory X-Mail-Api-Token app-level header."""
        return {"X-Mail-Api-Token": settings.MAIL_API_TOKEN}

    @staticmethod
    def _authed_headers(access_token: str) -> dict:
        """Return headers for endpoints that also require a mailbox token."""
        h = MailApiService._base_headers()
        h["X-Mail-Access-Token"] = access_token
        return h

    # ------------------------------------------------------------------ #
    # Token storage helpers (delegate to AuthService to avoid circular    #
    # imports; we import lazily here)                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_stored_tokens(user_id: int) -> dict | None:
        """Return stored token dict or None."""
        from app.services.auth_service import AuthService

        return AuthService.get_tokens(user_id)

    @staticmethod
    def _save_tokens(
        user_email: str,
        access_token: str,
        refresh_token: str,
        token_id: str,
        refresh_expires_at: str,
    ):
        """Persist tokens for *user_email* (upsert)."""
        from app.services.auth_service import AuthService

        AuthService.store_tokens(
            user_email=user_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_id=token_id,
            refresh_expires_at=refresh_expires_at,
        )

    # ------------------------------------------------------------------ #
    # Auth operations                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def login(email: str, password: str, label: str = "phishing-detector") -> dict:
        """
        Login to the mail API and return raw token data.

        Returns dict with keys: accessToken, refreshToken, tokenId,
                                accessTokenTtl, refreshExpiresAt
        Raises on failure.
        """
        url = f"{settings.MAIL_API_BASE_URL}/api/auth/token"
        payload = {"email": email, "password": password, "label": label}
        logger.info(f"Mail API login [email={email}] [label={label}]")

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url, headers=MailApiService._base_headers(), json=payload
            )

        if resp.status_code != 200:
            logger.error(f"Mail API login failed [{resp.status_code}]: {resp.text}")
            raise ValueError(f"Mail API login failed ({resp.status_code}): {resp.text}")

        body = resp.json()
        if body.get("error_code", -1) != 0:
            raise ValueError(f"Mail API login error: {body.get('message', 'unknown')}")

        data = body["data"]
        logger.info(
            f"Mail API login successful [email={email}] [tokenId={data.get('tokenId')}]"
        )
        return data

    @staticmethod
    def refresh_access_token(user_id: int) -> bool:
        """
        Refresh the stored access token for *user_id*.

        Returns True on success, False on failure (e.g. refresh token expired).
        On success the new tokens are persisted in the DB.
        """
        tokens = MailApiService._get_stored_tokens(user_id)
        if not tokens or not tokens.get("refresh_token"):
            logger.warning(f"No refresh token available for user [user_id={user_id}]")
            return False

        url = f"{settings.MAIL_API_BASE_URL}/api/auth/refresh"
        payload = {"refreshToken": tokens["refresh_token"]}
        logger.info(f"Refreshing mail API access token [user_id={user_id}]")

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    url, headers=MailApiService._base_headers(), json=payload
                )
        except httpx.RequestError as e:
            logger.error(f"Network error refreshing token [user_id={user_id}]: {e}")
            return False

        if resp.status_code != 200:
            logger.warning(
                f"Token refresh failed [{resp.status_code}] [user_id={user_id}]: {resp.text}"
            )
            return False

        body = resp.json()
        if body.get("error_code", -1) != 0:
            logger.warning(
                f"Token refresh API error [user_id={user_id}]: {body.get('message')}"
            )
            return False

        data = body["data"]

        # We need the user's email to call store_tokens. Retrieve from the DB user record.
        from app.models import User

        user = User.get_by_id(user_id)
        if not user:
            logger.error(f"User not found during token refresh [user_id={user_id}]")
            return False

        MailApiService._save_tokens(
            user_email=user["email"],
            access_token=data["accessToken"],
            refresh_token=data["refreshToken"],
            token_id=data["tokenId"],
            refresh_expires_at=data.get("refreshExpiresAt", ""),
        )
        logger.info(f"Token refreshed successfully [user_id={user_id}]")
        return True

    @staticmethod
    def revoke(user_id: int):
        """Revoke the stored refresh token for *user_id*."""
        tokens = MailApiService._get_stored_tokens(user_id)
        if not tokens or not tokens.get("refresh_token"):
            return

        url = f"{settings.MAIL_API_BASE_URL}/api/auth/revoke"
        payload = {"refreshToken": tokens["refresh_token"]}
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url, headers=MailApiService._base_headers(), json=payload
                )
            if resp.status_code == 200:
                logger.info(f"Mail API token revoked [user_id={user_id}]")
            else:
                logger.warning(
                    f"Mail API revoke returned {resp.status_code} [user_id={user_id}]"
                )
        except httpx.RequestError as e:
            logger.warning(f"Network error revoking token [user_id={user_id}]: {e}")

    # ------------------------------------------------------------------ #
    # Email fetching                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def fetch_emails(
        user_id: int, max_results: int = 50, after: str = None
    ) -> list[dict]:
        """
        Fetch emails from the mail API for *user_id*.

        Args:
            user_id:     Local user ID (used to look up stored tokens).
            max_results: Maximum number of emails to return.
            after:       ISO timestamp — only fetch emails received after this time.

        Returns:
            List of dicts with shape:
              {gmail_message_id, subject, sender, recipient, body, received_at}
        """
        tokens = MailApiService._get_stored_tokens(user_id)
        if not tokens or not tokens.get("access_token"):
            raise ValueError(f"No access token for user [user_id={user_id}]")

        access_token = tokens["access_token"]

        # ---- Step 1: list messages ----------------------------------------
        list_payload: dict = {"folder": FOLDER, "limit": max_results, "offset": 0}
        if after:
            try:
                dt = datetime.fromisoformat(after)
                # Ensure UTC-aware for formatting
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                list_payload["dateFrom"] = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                logger.info(
                    f"Incremental fetch from {list_payload['dateFrom']} [user_id={user_id}]"
                )
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid after timestamp '{after}', fetching all [user_id={user_id}]"
                )

        logger.info(
            f"Fetching mail list [user_id={user_id}] [limit={max_results}] [folder={FOLDER}]"
        )

        list_resp_data = MailApiService._post_with_refresh(
            user_id=user_id,
            url=f"{settings.MAIL_API_BASE_URL}/api/mail/list",
            payload=list_payload,
        )
        if list_resp_data is None:
            raise Exception("Failed to list emails from mail API (auth failed)")

        messages_summary = list_resp_data.get("messages", [])
        logger.info(
            f"Mail API returned {len(messages_summary)} messages [user_id={user_id}]"
        )

        # ---- Step 2: fetch full message per UID ---------------------------
        emails: list[dict] = []
        skipped = 0

        for summary in messages_summary:
            uid = summary.get("uid")
            if uid is None:
                skipped += 1
                continue

            try:
                msg_data = MailApiService._post_with_refresh(
                    user_id=user_id,
                    url=f"{settings.MAIL_API_BASE_URL}/api/mail/message",
                    payload={"folder": FOLDER, "uid": uid},
                )
                if msg_data is None:
                    skipped += 1
                    logger.warning(
                        f"Auth failed fetching message uid={uid} [user_id={user_id}]"
                    )
                    continue

                message = msg_data.get("message", {})
                emails.append(MailApiService._parse_message(message))

            except Exception as e:
                skipped += 1
                logger.warning(f"Skipped message uid={uid} [user_id={user_id}]: {e}")

        logger.info(
            f"Mail fetch complete: {len(emails)} parsed, {skipped} skipped [user_id={user_id}]"
        )
        return emails

    @staticmethod
    def fetch_message(user_id: int, message_uid) -> dict:
        """Fetch and parse one full message from the mail API by UID."""
        if message_uid is None:
            raise ValueError("message_uid is required")

        msg_data = MailApiService._post_with_refresh(
            user_id=user_id,
            url=f"{settings.MAIL_API_BASE_URL}/api/mail/message",
            payload={"folder": FOLDER, "uid": int(message_uid)},
        )
        if msg_data is None:
            raise Exception("Failed to fetch message from mail API (auth failed)")

        message = msg_data.get("message", {})
        return MailApiService._parse_message(message)

    # ------------------------------------------------------------------ #
    # Internal request helper with automatic token refresh                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _post_with_refresh(user_id: int, url: str, payload: dict) -> dict | None:
        """
        POST *url* with mailbox auth headers.

        On 401, attempts one token refresh then retries.
        Returns the response ``data`` dict, or None if auth ultimately fails.
        """
        tokens = MailApiService._get_stored_tokens(user_id)
        if not tokens:
            return None

        access_token = tokens["access_token"]

        def _do_post(token: str) -> httpx.Response:
            headers = {
                **MailApiService._base_headers(),
                "Content-Type": "application/json",
                "X-Mail-Access-Token": token,
            }
            with httpx.Client(timeout=30.0) as client:
                return client.post(url, headers=headers, json=payload)

        resp = _do_post(access_token)

        if resp.status_code == 401:
            logger.info(f"Access token expired, refreshing [user_id={user_id}]")
            if not MailApiService.refresh_access_token(user_id):
                logger.error(
                    f"Token refresh failed, cannot proceed [user_id={user_id}]"
                )
                return None
            # Get fresh token
            new_tokens = MailApiService._get_stored_tokens(user_id)
            if not new_tokens:
                return None
            resp = _do_post(new_tokens["access_token"])

        if resp.status_code != 200:
            logger.error(f"Mail API error {resp.status_code} for {url}: {resp.text}")
            raise Exception(f"Mail API error {resp.status_code}: {resp.text}")

        body = resp.json()
        if body.get("error_code", -1) != 0:
            raise Exception(
                f"Mail API error response: {body.get('message', 'unknown')}"
            )

        return body.get("data", {})

    # ------------------------------------------------------------------ #
    # Message parsing                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_message(message: dict) -> dict:
        """
        Convert a mail API message dict to the shape expected by EmailService.create_email().

        gmail_message_id → str(uid)
        subject          → subject
        sender           → "Name <address>" or just address
        recipient        → first to address
        body             → text body (falls back to html)
        received_at      → ISO datetime string
        attachments      → list of {filename, mime_type, size, content_b64?, attachment_id?}
        """
        uid = message.get("uid", "")

        # Sender
        from_info = message.get("from", {})
        if isinstance(from_info, dict):
            name = from_info.get("name", "").strip()
            addr = from_info.get("address", "").strip()
            sender = f"{name} <{addr}>" if name else addr
        else:
            sender = str(from_info)

        # Recipient
        to_list = message.get("to", [])
        if to_list and isinstance(to_list[0], dict):
            recipient = to_list[0].get("address", "")
        else:
            recipient = ""

        # Body — prefer plain text, fall back to HTML
        body = message.get("text") or message.get("html") or ""

        # Date
        date_raw = message.get("date", "")
        received_at = MailApiService._parse_date(date_raw)

        attachments = MailApiService._parse_attachments(message)

        return {
            "gmail_message_id": str(uid),  # reuse existing DB column name
            "uid": uid,  # original uid kept for follow-up attachment fetches
            "subject": message.get("subject", ""),
            "sender": sender,
            "recipient": recipient,
            "body": body,
            "received_at": received_at,
            "attachments": attachments,
        }

    @staticmethod
    def _parse_attachments(message: dict) -> list[dict]:
        """Normalize the attachments array from a mail-api message.

        The mail-api may inline content as base64 (`content` / `contentBase64` /
        `data`) or only return metadata + an identifier the caller must use to
        download the blob. We keep both shapes — the persistence layer fetches
        on-demand if no inline content is present.
        """
        raw = message.get("attachments") or message.get("attachment") or []
        if not isinstance(raw, list):
            return []

        normalized: list[dict] = []
        for index, att in enumerate(raw):
            if not isinstance(att, dict):
                continue

            filename = (
                att.get("filename")
                or att.get("name")
                or att.get("fileName")
                or "attachment.bin"
            )
            mime_type = (
                att.get("contentType")
                or att.get("mimeType")
                or att.get("mime")
                or "application/octet-stream"
            )
            size = int(
                att.get("size") or att.get("contentLength") or att.get("length") or 0
            )

            # Inline base64 content (some mail-api implementations include it).
            # The server we're integrated with returns binary via a separate
            # endpoint instead, but we still try inline first.
            content_b64 = (
                att.get("contentBase64")
                or att.get("content")
                or att.get("data")
                or att.get("base64")
            )

            # The custom mail-api expects `attachmentIndex` (0-based position)
            # to fetch the blob — it doesn't expose individual attachment IDs.
            normalized.append(
                {
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": size,
                    "content_b64": content_b64,
                    "attachment_index": index,
                }
            )

        return normalized

    @staticmethod
    def fetch_attachment_content(
        user_id: int,
        message_uid,
        attachment_index: int | None = None,
        filename: str | None = None,
        folder: str = FOLDER,
    ) -> bytes | None:
        """Fetch raw attachment bytes from the mail API.

        Endpoint shape (per mail-api OpenAPI spec):

            POST /api/mail/attachment
                { "folder": "INBOX",
                  "uid": <int>,
                  "attachmentIndex": <int>,
                  "filename": <str?> }
            → response 200 with raw binary body.

        Returns None when the server doesn't have content for the index, or
        when authentication ultimately fails. Refreshes the access token once
        on 401 before giving up.
        """
        if message_uid is None or attachment_index is None:
            return None

        url = f"{settings.MAIL_API_BASE_URL}/api/mail/attachment"
        payload: dict = {
            "folder": folder,
            "uid": int(message_uid) if not isinstance(message_uid, int) else message_uid,
            "attachmentIndex": int(attachment_index),
        }
        if filename:
            payload["filename"] = filename

        tokens = MailApiService._get_stored_tokens(user_id)
        if not tokens or not tokens.get("access_token"):
            return None

        def _do_post(token: str) -> httpx.Response:
            headers = {
                **MailApiService._base_headers(),
                "Content-Type": "application/json",
                "X-Mail-Access-Token": token,
            }
            with httpx.Client(timeout=60.0) as client:
                return client.post(url, headers=headers, json=payload)

        try:
            resp = _do_post(tokens["access_token"])
            if resp.status_code == 401:
                logger.info(
                    f"Mail API attachment 401 — refreshing token [user_id={user_id}]"
                )
                if not MailApiService.refresh_access_token(user_id):
                    return None
                refreshed = MailApiService._get_stored_tokens(user_id)
                if not refreshed:
                    return None
                resp = _do_post(refreshed["access_token"])

            if resp.status_code != 200:
                logger.warning(
                    f"Mail API attachment fetch HTTP {resp.status_code} "
                    f"[user_id={user_id}] [uid={message_uid}] "
                    f"[index={attachment_index}]: {resp.text[:200]}"
                )
                return None

            content_type = (resp.headers.get("content-type") or "").lower()
            # Some servers wrap binary inside JSON ({error_code, data:{contentBase64}})
            # so handle both shapes.
            if "application/json" in content_type:
                try:
                    body = resp.json()
                except Exception:
                    return None
                inner = body.get("data") if isinstance(body, dict) else None
                if isinstance(inner, dict):
                    import base64

                    b64 = (
                        inner.get("contentBase64")
                        or inner.get("content")
                        or inner.get("data")
                        or inner.get("base64")
                    )
                    if b64:
                        try:
                            return base64.b64decode(b64)
                        except Exception:
                            return None
                # JSON with no content → treat as "no body"
                return None

            # Default path — server streamed raw bytes
            return resp.content or None
        except Exception as e:
            logger.warning(
                f"Mail API attachment fetch failed [user_id={user_id}] "
                f"[uid={message_uid}] [index={attachment_index}]: {e}"
            )
            return None

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse ISO date string from mail API to ISO format."""
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        try:
            # Mail API returns ISO 8601 strings like "2026-04-13T10:00:00.000Z"
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
