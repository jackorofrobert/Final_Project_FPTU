"""
Background scheduler for periodic email fetching, auto-analysis, and VT checks.

Uses APScheduler to:
- Poll Gmail every 5 minutes for each authenticated user (incremental fetch).
- Auto-analyze unanalyzed emails every 5 minutes (runs after fetch).
- Check email links via VirusTotal with daily quota protection.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.models import User, Email, FetchLog, AnalysisLog, VTScanLog
from app.services.mail_api_service import MailApiService
from app.services.email_service import EmailService
from app.services.attachment_service import AttachmentService
from app.services.virustotal_service import VirusTotalService
from app.utils.logger import get_logger

logger = get_logger(__name__)

FETCH_INTERVAL_MINUTES = 5
ANALYSIS_INTERVAL_MINUTES = 5
MAX_RESULTS_PER_FETCH = 50
MAX_ANALYSIS_PER_RUN = 20
VT_CHECK_INTERVAL_MINUTES = 5

scheduler = AsyncIOScheduler()


def fetch_new_emails_for_all_users():
    """Iterate over all users with OAuth tokens and fetch new emails."""
    logger.info("Scheduler: starting periodic email fetch for all users")

    try:
        users = User.get_all_with_tokens()
    except Exception as e:
        logger.error(f"Scheduler: failed to query users: {e}", exc_info=True)
        return

    if not users:
        logger.info("Scheduler: no users with valid tokens, skipping")
        return

    logger.info(f"Scheduler: found {len(users)} user(s) to fetch emails for")

    for user in users:
        user_id = user["id"]

        try:
            # Fetch without a date filter — the DB UNIQUE(user_id, gmail_message_id)
            # constraint deduplicates on insert, so re-fetching known emails is harmless.
            emails = MailApiService.fetch_emails(
                user_id, max_results=MAX_RESULTS_PER_FETCH
            )

            stored_count = 0
            new_count = 0
            for email_data in emails:
                existing = EmailService.get_email_by_gmail_id(
                    user_id, email_data["gmail_message_id"]
                )
                stored = EmailService.create_email(
                    user_id=user_id,
                    gmail_message_id=email_data["gmail_message_id"],
                    subject=email_data["subject"],
                    sender=email_data["sender"],
                    recipient=email_data["recipient"],
                    body=email_data["body"],
                    received_at=email_data["received_at"],
                )
                stored_count += 1
                if not existing:
                    new_count += 1

                # Persist attachments only on first ingest to avoid re-downloading
                if not existing and stored and email_data.get("attachments"):
                    AttachmentService.persist_for_email(
                        user_id=user_id,
                        email_id=stored["id"],
                        message_uid=email_data.get("uid"),
                        attachments=email_data["attachments"],
                    )

            User.update_last_fetch(user_id)
            FetchLog.create(
                user_id=user_id,
                source="scheduler",
                emails_fetched=len(emails),
                new_emails=new_count,
            )
            logger.info(
                f"Scheduler: fetched {len(emails)} emails, {new_count} new "
                f"[user_id={user_id}]"
            )
        except Exception as e:
            logger.error(
                f"Scheduler: error fetching emails [user_id={user_id}]: {e}",
                exc_info=True,
            )


def analyze_unanalyzed_emails_for_all_users():
    """Auto-analyze emails that have no prediction yet, for all users."""
    logger.info("Scheduler: starting auto-analysis for all users")

    try:
        users = User.get_all_with_tokens()
    except Exception as e:
        logger.error(
            f"Scheduler: failed to query users for analysis: {e}", exc_info=True
        )
        return

    if not users:
        logger.info("Scheduler: no users with valid tokens, skipping analysis")
        return

    for user in users:
        user_id = user["id"]
        try:
            unanalyzed = Email.get_unanalyzed_by_user_id(
                user_id, limit=MAX_ANALYSIS_PER_RUN
            )

            if not unanalyzed:
                logger.info(f"Scheduler: no unanalyzed emails [user_id={user_id}]")
                AnalysisLog.create(
                    user_id=user_id,
                    source="scheduler",
                    emails_analyzed=0,
                    emails_skipped=0,
                )
                User.update_last_analysis(user_id)
                continue

            analyzed = 0
            skipped = 0
            for email in unanalyzed:
                try:
                    body = email.get("body") or ""
                    if not body.strip():
                        skipped += 1
                        continue
                    EmailService.analyze_and_save(email["id"], body)
                    analyzed += 1
                except Exception as e:
                    skipped += 1
                    logger.warning(
                        f"Scheduler: failed to analyze email [email_id={email['id']}] "
                        f"[user_id={user_id}]: {e}"
                    )

            User.update_last_analysis(user_id)
            AnalysisLog.create(
                user_id=user_id,
                source="scheduler",
                emails_analyzed=analyzed,
                emails_skipped=skipped,
            )
            logger.info(
                f"Scheduler: auto-analysis done — {analyzed} analyzed, {skipped} skipped "
                f"[user_id={user_id}]"
            )
        except Exception as e:
            logger.error(
                f"Scheduler: error during auto-analysis [user_id={user_id}]: {e}",
                exc_info=True,
            )


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        fetch_new_emails_for_all_users,
        trigger=IntervalTrigger(minutes=FETCH_INTERVAL_MINUTES),
        id="periodic_email_fetch",
        name=f"Fetch new emails every {FETCH_INTERVAL_MINUTES} minutes",
        replace_existing=True,
    )
    scheduler.add_job(
        analyze_unanalyzed_emails_for_all_users,
        trigger=IntervalTrigger(minutes=ANALYSIS_INTERVAL_MINUTES),
        id="periodic_email_analysis",
        name=f"Auto-analyze emails every {ANALYSIS_INTERVAL_MINUTES} minutes",
        replace_existing=True,
    )
    scheduler.add_job(
        scan_links_with_virustotal_for_all_users,
        trigger=IntervalTrigger(minutes=VT_CHECK_INTERVAL_MINUTES),
        id="periodic_vt_link_scan",
        name=f"Check links with VirusTotal every {VT_CHECK_INTERVAL_MINUTES} minutes",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started — fetch every {FETCH_INTERVAL_MINUTES}min, "
        f"analysis every {ANALYSIS_INTERVAL_MINUTES}min, "
        f"VT check every {VT_CHECK_INTERVAL_MINUTES}min"
    )


def scan_links_with_virustotal_for_all_users():
    """Check email links against VirusTotal, with daily quota."""
    logger.info("Scheduler: starting VirusTotal link scan for all users")
    try:
        users = User.get_all_with_tokens()
    except Exception as e:
        logger.error(
            f"Scheduler: failed to query users for VT scan: {e}", exc_info=True
        )
        return

    if not users:
        logger.info("Scheduler: no users with valid tokens, skipping VT scan")
        return

    for user in users:
        user_id = user["id"]
        try:
            result = VirusTotalService.scan_user_email_links(user_id=user_id)
            VTScanLog.create(
                user_id=user_id,
                source="scheduler",
                checked=result["checked"],
                skipped=result["skipped"],
                errors=result["errors"],
                quota_remaining=result["quota_remaining"],
            )
            logger.info(
                f"Scheduler: VT link scan done [user_id={user_id}] "
                f"checked={result['checked']} skipped={result['skipped']} "
                f"errors={result['errors']} quota_remaining={result['quota_remaining']}"
            )

            # Reuse the same daily quota for attachment scans — runs after the
            # link scan so URLs (the cheaper lookup) get priority.
            att_result = VirusTotalService.scan_user_email_attachments(
                user_id=user_id
            )
            VTScanLog.create(
                user_id=user_id,
                source="scheduler-attachments",
                checked=att_result["checked"] + att_result["pending"],
                skipped=att_result["skipped"],
                errors=att_result["errors"],
                quota_remaining=att_result["quota_remaining"],
            )
            logger.info(
                f"Scheduler: VT attachment scan done [user_id={user_id}] "
                f"checked={att_result['checked']} pending={att_result['pending']} "
                f"skipped={att_result['skipped']} errors={att_result['errors']} "
                f"quota_remaining={att_result['quota_remaining']}"
            )
        except Exception as e:
            logger.error(
                f"Scheduler: error during VT scan [user_id={user_id}]: {e}",
                exc_info=True,
            )


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Email fetch scheduler stopped")
