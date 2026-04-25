"""
VirusTotal integration service with daily quota control.
"""

import base64
import hashlib
import re
from datetime import datetime
from pathlib import Path

import httpx

from app.core.config import settings
from app.models import (
    Email,
    EmailAttachment,
    VTAttachmentCheck,
    VTLinkCheck,
    VTDailyUsage,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)


class VirusTotalService:
    """Service for checking email links against VirusTotal."""

    @staticmethod
    def _today_key() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def get_daily_usage() -> dict:
        """Return current day's usage and limit."""
        today = VirusTotalService._today_key()
        used = VTDailyUsage.get_count(today)
        return {
            "date": today,
            "used": used,
            "limit": settings.VIRUSTOTAL_DAILY_LIMIT,
            "remaining": max(settings.VIRUSTOTAL_DAILY_LIMIT - used, 0),
        }

    @staticmethod
    def _normalize_url(url: str) -> str:
        value = (url or "").strip()
        value = value.rstrip(".,);'\"!?")
        if value.lower().startswith("www."):
            value = f"https://{value}"
        return value

    @staticmethod
    def _extract_urls(text: str) -> list[str]:
        if not text:
            return []
        seen = set()
        urls: list[str] = []
        for candidate in URL_PATTERN.findall(text):
            url = VirusTotalService._normalize_url(candidate)
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _vt_url_id(url: str) -> str:
        encoded = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
        return encoded.rstrip("=")

    @staticmethod
    def _check_single_url(url: str) -> dict:
        """Check a URL against VirusTotal.

        Flow:
        1. GET /api/v3/urls/{url_id} to retrieve an existing report.
        2. If 404 (URL never submitted), POST /api/v3/urls to queue analysis
           and return {'pending': True} — the scheduler will retry on the next run.
        3. Any other HTTP error is re-raised so the caller can record it.
        """
        api_key = settings.VIRUSTOTAL_API_KEY
        if not api_key:
            raise ValueError("VIRUSTOTAL_API_KEY is not configured")

        url_id = VirusTotalService._vt_url_id(url)
        headers = {"x-apikey": api_key}

        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers=headers,
            )

            if response.status_code == 404:
                # URL not yet in VT — submit it for analysis (costs 1 quota unit)
                client.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers=headers,
                    data={"url": url},
                )
                return {"pending": True}

            response.raise_for_status()
            payload = response.json()

        stats = (
            payload.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        )
        return {
            "malicious": int(stats.get("malicious", 0)),
            "suspicious": int(stats.get("suspicious", 0)),
            "harmless": int(stats.get("harmless", 0)),
            "undetected": int(stats.get("undetected", 0)),
        }

    @staticmethod
    def scan_user_email_links(user_id: int, email_limit: int = 200) -> dict:
        """
        Scan unchecked links from user's emails, respecting global daily quota.
        Returns counters: checked, skipped, errors, quota_remaining.
        """
        usage = VirusTotalService.get_daily_usage()
        remaining = usage["remaining"]
        if remaining <= 0:
            logger.info("VirusTotal quota exhausted for today, skipping scan")
            return {"checked": 0, "skipped": 0, "errors": 0, "quota_remaining": 0}

        checked = 0
        skipped = 0
        errors = 0

        emails = Email.get_by_user_id(user_id, limit=email_limit, offset=0)
        for email in emails:
            if remaining <= 0:
                break
            email_id = email["id"]
            body = email.get("body") or ""
            urls = VirusTotalService._extract_urls(body)
            if not urls:
                continue

            for url in urls:
                if remaining <= 0:
                    break
                url_hash = VirusTotalService._url_hash(url)

                if VTLinkCheck.exists(email_id, url_hash):
                    skipped += 1
                    continue

                try:
                    stats = VirusTotalService._check_single_url(url)
                    if stats.get("pending"):
                        VTLinkCheck.upsert(
                            user_id=user_id,
                            email_id=email_id,
                            url=url,
                            url_hash=url_hash,
                            status="pending_scan",
                        )
                    else:
                        VTLinkCheck.upsert(
                            user_id=user_id,
                            email_id=email_id,
                            url=url,
                            url_hash=url_hash,
                            status="success",
                            malicious=stats["malicious"],
                            suspicious=stats["suspicious"],
                            harmless=stats["harmless"],
                            undetected=stats["undetected"],
                        )
                        checked += 1
                    VTDailyUsage.increment(VirusTotalService._today_key(), 1)
                    remaining -= 1
                except Exception as exc:
                    errors += 1
                    VTLinkCheck.upsert(
                        user_id=user_id,
                        email_id=email_id,
                        url=url,
                        url_hash=url_hash,
                        status="error",
                        error_message=str(exc),
                    )
                    logger.warning(
                        f"VirusTotal check failed [user_id={user_id}] [email_id={email_id}] [url={url}]: {exc}"
                    )
                    checked += 1
                    VTDailyUsage.increment(VirusTotalService._today_key(), 1)
                    remaining -= 1
                except Exception as exc:
                    errors += 1
                    VTLinkCheck.create(
                        user_id=user_id,
                        email_id=email_id,
                        url=url,
                        url_hash=url_hash,
                        status="error",
                        error_message=str(exc),
                    )
                    logger.warning(
                        f"VirusTotal check failed [user_id={user_id}] [email_id={email_id}] [url={url}]: {exc}"
                    )

        return {
            "checked": checked,
            "skipped": skipped,
            "errors": errors,
            "quota_remaining": remaining,
        }

    # ------------------------------------------------------------------ #
    # File / attachment scanning                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _check_file_by_hash(sha256: str) -> dict | None:
        """Look up an existing VT report by sha256.

        Returns the stats dict on success, None on 404 (no report yet),
        and raises on any other HTTP error.
        """
        api_key = settings.VIRUSTOTAL_API_KEY
        if not api_key:
            raise ValueError("VIRUSTOTAL_API_KEY is not configured")

        headers = {"x-apikey": api_key}
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f"https://www.virustotal.com/api/v3/files/{sha256}",
                headers=headers,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            payload = response.json()

        stats = (
            payload.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        )
        return {
            "malicious": int(stats.get("malicious", 0)),
            "suspicious": int(stats.get("suspicious", 0)),
            "harmless": int(stats.get("harmless", 0)),
            "undetected": int(stats.get("undetected", 0)),
        }

    @staticmethod
    def _upload_file_for_scan(file_path: Path, filename: str) -> None:
        """POST a file to VirusTotal for analysis.

        Free-tier upload cap is 32MB. The caller must check size before
        calling. Returns nothing — VT queues the analysis; result will be
        retrievable via _check_file_by_hash on a later run.
        """
        api_key = settings.VIRUSTOTAL_API_KEY
        if not api_key:
            raise ValueError("VIRUSTOTAL_API_KEY is not configured")

        headers = {"x-apikey": api_key}
        with file_path.open("rb") as fp, httpx.Client(timeout=120.0) as client:
            files = {"file": (filename, fp)}
            response = client.post(
                "https://www.virustotal.com/api/v3/files",
                headers=headers,
                files=files,
            )
            response.raise_for_status()

    @staticmethod
    def _scan_attachment_row(attachment: dict, user_id: int) -> tuple[str, int]:
        """Run one attachment through VT.

        Returns (outcome, quota_consumed):
          outcome ∈ {"checked", "pending", "skipped", "error"}
          quota_consumed: number of VT requests this call consumed
        """
        attachment_id = attachment["id"]
        sha256 = attachment["sha256"]
        email_id = attachment["email_id"]
        size = int(attachment.get("size") or 0)
        filename = attachment.get("filename") or "attachment.bin"
        storage_path = attachment.get("storage_path")

        # Skip metadata-only rows (the surrogate sha cannot be resolved by VT)
        if not storage_path:
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="error",
                error_message="No file content stored locally — cannot scan",
            )
            return "skipped", 0

        path = Path(storage_path)
        if not path.exists():
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="error",
                error_message="Local blob missing on disk",
            )
            return "skipped", 0

        # Step 1: hash lookup (counts toward quota even on hit per VT TOS,
        # but is the cheapest path; we always try this before uploading).
        try:
            stats = VirusTotalService._check_file_by_hash(sha256)
        except Exception as exc:
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="error",
                error_message=str(exc),
            )
            return "error", 1

        if stats is not None:
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="success",
                malicious=stats["malicious"],
                suspicious=stats["suspicious"],
                harmless=stats["harmless"],
                undetected=stats["undetected"],
            )
            return "checked", 1

        # Step 2: VT has never seen this file → upload (eligible only if size is OK)
        if size <= 0 or size > settings.ATTACHMENT_MAX_SIZE_BYTES:
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="error",
                error_message=f"File too large to upload to VirusTotal ({size} bytes)",
            )
            return "skipped", 1

        try:
            VirusTotalService._upload_file_for_scan(path, filename)
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="pending_scan",
            )
            return "pending", 2
        except Exception as exc:
            VTAttachmentCheck.upsert(
                user_id=user_id,
                email_id=email_id,
                attachment_id=attachment_id,
                sha256=sha256,
                status="error",
                error_message=str(exc),
            )
            return "error", 2

    @staticmethod
    def scan_user_email_attachments(user_id: int, attachment_limit: int = 100) -> dict:
        """Scan unscanned attachments for *user_id* respecting the global daily quota."""
        usage = VirusTotalService.get_daily_usage()
        remaining = usage["remaining"]
        if remaining <= 0:
            logger.info("VirusTotal quota exhausted for today, skipping file scan")
            return {"checked": 0, "pending": 0, "skipped": 0, "errors": 0, "quota_remaining": 0}

        attachments = EmailAttachment.get_unscanned_for_user(
            user_id, limit=attachment_limit
        )
        checked = 0
        pending = 0
        skipped = 0
        errors = 0

        for att in attachments:
            if remaining <= 0:
                break
            outcome, used = VirusTotalService._scan_attachment_row(att, user_id)
            if used > 0:
                VTDailyUsage.increment(VirusTotalService._today_key(), used)
                remaining -= used
            if outcome == "checked":
                checked += 1
            elif outcome == "pending":
                pending += 1
            elif outcome == "error":
                errors += 1
            else:
                skipped += 1

        return {
            "checked": checked,
            "pending": pending,
            "skipped": skipped,
            "errors": errors,
            "quota_remaining": max(remaining, 0),
        }

    @staticmethod
    def scan_single_email_attachments(user_id: int, email_id: int) -> dict:
        """Scan attachments for a single email (used by manual VT trigger)."""
        usage = VirusTotalService.get_daily_usage()
        remaining = usage["remaining"]
        if remaining <= 0:
            return {"checked": 0, "pending": 0, "skipped": 0, "errors": 0, "quota_remaining": 0}

        email = Email.get_by_id(email_id)
        if not email or email.get("user_id") != user_id:
            raise ValueError("Email not found or access denied")

        attachments = EmailAttachment.get_by_email_id(email_id)
        checked = 0
        pending = 0
        skipped = 0
        errors = 0

        for att in attachments:
            if remaining <= 0:
                break
            if VTAttachmentCheck.exists_success(att["id"]):
                skipped += 1
                continue
            outcome, used = VirusTotalService._scan_attachment_row(att, user_id)
            if used > 0:
                VTDailyUsage.increment(VirusTotalService._today_key(), used)
                remaining -= used
            if outcome == "checked":
                checked += 1
            elif outcome == "pending":
                pending += 1
            elif outcome == "error":
                errors += 1
            else:
                skipped += 1

        return {
            "checked": checked,
            "pending": pending,
            "skipped": skipped,
            "errors": errors,
            "quota_remaining": max(remaining, 0),
        }

    # ------------------------------------------------------------------ #

    @staticmethod
    def scan_single_email_links(user_id: int, email_id: int) -> dict:
        """Scan unchecked links for one specific email, respecting daily quota."""
        usage = VirusTotalService.get_daily_usage()
        remaining = usage["remaining"]
        if remaining <= 0:
            return {"checked": 0, "skipped": 0, "errors": 0, "quota_remaining": 0}

        email = Email.get_by_id(email_id)
        if not email or email.get("user_id") != user_id:
            raise ValueError("Email not found or access denied")

        checked = 0
        skipped = 0
        errors = 0

        body = email.get("body") or ""
        urls = VirusTotalService._extract_urls(body)
        for url in urls:
            if remaining <= 0:
                break
            url_hash = VirusTotalService._url_hash(url)

            if VTLinkCheck.exists(email_id, url_hash):
                skipped += 1
                continue

            try:
                stats = VirusTotalService._check_single_url(url)
                if stats.get("pending"):
                    VTLinkCheck.upsert(
                        user_id=user_id,
                        email_id=email_id,
                        url=url,
                        url_hash=url_hash,
                        status="pending_scan",
                    )
                else:
                    VTLinkCheck.upsert(
                        user_id=user_id,
                        email_id=email_id,
                        url=url,
                        url_hash=url_hash,
                        status="success",
                        malicious=stats["malicious"],
                        suspicious=stats["suspicious"],
                        harmless=stats["harmless"],
                        undetected=stats["undetected"],
                    )
                    checked += 1
                VTDailyUsage.increment(VirusTotalService._today_key(), 1)
                remaining -= 1
            except Exception as exc:
                errors += 1
                VTLinkCheck.upsert(
                    user_id=user_id,
                    email_id=email_id,
                    url=url,
                    url_hash=url_hash,
                    status="error",
                    error_message=str(exc),
                )
                logger.warning(
                    f"VirusTotal single-email check failed [user_id={user_id}] [email_id={email_id}] [url={url}]: {exc}"
                )
                checked += 1
                VTDailyUsage.increment(VirusTotalService._today_key(), 1)
                remaining -= 1
            except Exception as exc:
                errors += 1
                VTLinkCheck.create(
                    user_id=user_id,
                    email_id=email_id,
                    url=url,
                    url_hash=url_hash,
                    status="error",
                    error_message=str(exc),
                )
                logger.warning(
                    f"VirusTotal single-email check failed [user_id={user_id}] [email_id={email_id}] [url={url}]: {exc}"
                )

        return {
            "checked": checked,
            "skipped": skipped,
            "errors": errors,
            "quota_remaining": remaining,
        }
