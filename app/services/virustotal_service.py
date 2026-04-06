"""
VirusTotal integration service with daily quota control.
"""
import base64
import hashlib
import re
from datetime import datetime

import httpx

from app.core.config import settings
from app.models import Email, VTLinkCheck, VTDailyUsage
from app.utils.logger import get_logger

logger = get_logger(__name__)

URL_PATTERN = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)


class VirusTotalService:
    """Service for checking email links against VirusTotal."""

    @staticmethod
    def _today_key() -> str:
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def get_daily_usage() -> dict:
        """Return current day's usage and limit."""
        today = VirusTotalService._today_key()
        used = VTDailyUsage.get_count(today)
        return {
            'date': today,
            'used': used,
            'limit': settings.VIRUSTOTAL_DAILY_LIMIT,
            'remaining': max(settings.VIRUSTOTAL_DAILY_LIMIT - used, 0),
        }

    @staticmethod
    def _normalize_url(url: str) -> str:
        value = (url or '').strip()
        value = value.rstrip('.,);\'"!?')
        if value.lower().startswith('www.'):
            value = f'https://{value}'
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
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    @staticmethod
    def _vt_url_id(url: str) -> str:
        encoded = base64.urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')
        return encoded.rstrip('=')

    @staticmethod
    def _check_single_url(url: str) -> dict:
        """Call VirusTotal URL report endpoint and return parsed stats."""
        api_key = settings.VIRUSTOTAL_API_KEY
        if not api_key:
            raise ValueError('VIRUSTOTAL_API_KEY is not configured')

        url_id = VirusTotalService._vt_url_id(url)
        endpoint = f'https://www.virustotal.com/api/v3/urls/{url_id}'
        headers = {'x-apikey': api_key}

        with httpx.Client(timeout=20.0) as client:
            response = client.get(endpoint, headers=headers)
            response.raise_for_status()
            payload = response.json()

        stats = (
            payload.get('data', {})
            .get('attributes', {})
            .get('last_analysis_stats', {})
        )
        return {
            'malicious': int(stats.get('malicious', 0)),
            'suspicious': int(stats.get('suspicious', 0)),
            'harmless': int(stats.get('harmless', 0)),
            'undetected': int(stats.get('undetected', 0)),
        }

    @staticmethod
    def scan_user_email_links(user_id: int, email_limit: int = 200) -> dict:
        """
        Scan unchecked links from user's emails, respecting global daily quota.
        Returns counters: checked, skipped, errors, quota_remaining.
        """
        usage = VirusTotalService.get_daily_usage()
        remaining = usage['remaining']
        if remaining <= 0:
            logger.info('VirusTotal quota exhausted for today, skipping scan')
            return {'checked': 0, 'skipped': 0, 'errors': 0, 'quota_remaining': 0}

        checked = 0
        skipped = 0
        errors = 0

        emails = Email.get_by_user_id(user_id, limit=email_limit, offset=0)
        for email in emails:
            if remaining <= 0:
                break
            email_id = email['id']
            body = email.get('body') or ''
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
                    VTLinkCheck.create(
                        user_id=user_id,
                        email_id=email_id,
                        url=url,
                        url_hash=url_hash,
                        status='success',
                        malicious=stats['malicious'],
                        suspicious=stats['suspicious'],
                        harmless=stats['harmless'],
                        undetected=stats['undetected'],
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
                        status='error',
                        error_message=str(exc),
                    )
                    logger.warning(
                        f'VirusTotal check failed [user_id={user_id}] [email_id={email_id}] [url={url}]: {exc}'
                    )

        return {
            'checked': checked,
            'skipped': skipped,
            'errors': errors,
            'quota_remaining': remaining,
        }
