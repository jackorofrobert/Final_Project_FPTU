"""
Probe what shape the mail-api message response uses for attachments.

Usage:
    .venv/bin/python scripts/probe_mail_attachments.py <user_id>

Prints the raw `message` JSON for the first email that has attachments, and
also tries the candidate attachment-fetch endpoints we currently support so
we know which one your server actually exposes.
"""

import json
import sys
from pprint import pprint

import httpx

from app.core.config import settings
from app.services.auth_service import AuthService
from app.services.mail_api_service import MailApiService


FOLDER = "INBOX"
ATTACHMENT_ENDPOINT_CANDIDATES = [
    # (method, path, payload-builder)
    ("POST", "/api/mail/attachment",          lambda uid, aid: {"folder": FOLDER, "uid": uid, "attachmentId": aid}),
    ("POST", "/api/mail/attachments/fetch",   lambda uid, aid: {"folder": FOLDER, "uid": uid, "attachmentId": aid}),
    ("POST", "/api/mail/message/attachment",  lambda uid, aid: {"folder": FOLDER, "uid": uid, "attachmentId": aid}),
    ("GET",  "/api/mail/attachment/{uid}/{aid}", None),
]


def main(user_id: int):
    tokens = AuthService.get_tokens(user_id)
    if not tokens or not tokens.get("access_token"):
        print(f"!! No access token for user_id={user_id}")
        return

    access_token = tokens["access_token"]
    base = settings.MAIL_API_BASE_URL
    headers_app = {"X-Mail-Api-Token": settings.MAIL_API_TOKEN}
    headers_full = {**headers_app, "X-Mail-Access-Token": access_token, "Content-Type": "application/json"}

    # 1. List inbox
    with httpx.Client(timeout=20.0) as client:
        r = client.post(
            f"{base}/api/mail/list",
            headers=headers_full,
            json={"folder": FOLDER, "limit": 25, "offset": 0},
        )
        r.raise_for_status()
        msgs = (r.json().get("data") or {}).get("messages", [])
        print(f"Inbox returned {len(msgs)} message summaries")

        # 2. Find an email that the summary suggests has attachments,
        # else just iterate until we find one in the full message body.
        target = None
        for m in msgs:
            uid = m.get("uid")
            if uid is None:
                continue
            r = client.post(
                f"{base}/api/mail/message",
                headers=headers_full,
                json={"folder": FOLDER, "uid": uid},
            )
            if r.status_code != 200:
                continue
            body = (r.json().get("data") or {}).get("message") or {}
            atts = body.get("attachments") or body.get("attachment") or []
            if atts:
                target = (uid, body, atts)
                print(f"\nFound message uid={uid} with {len(atts)} attachment(s)")
                break

        if not target:
            print("!! No attachments found in the first 25 messages")
            return

        uid, message, atts = target

        # 3. Dump the FIRST attachment dict — full keys, truncate large fields
        first = atts[0]
        printable = {}
        for k, v in first.items():
            if isinstance(v, str) and len(v) > 200:
                printable[k] = f"{v[:120]}...({len(v)} chars total)"
            else:
                printable[k] = v
        print("\n=== First attachment dict ===")
        pprint(printable, sort_dicts=True)

        # 4. Try the candidate fetch endpoints
        att_id = (
            first.get("id")
            or first.get("attachmentId")
            or first.get("partId")
            or first.get("uid")
        )
        print(f"\n=== Probing attachment-fetch endpoints (uid={uid}, attachment_id={att_id}) ===")
        for method, path_tpl, build_payload in ATTACHMENT_ENDPOINT_CANDIDATES:
            path = path_tpl.replace("{uid}", str(uid)).replace("{aid}", str(att_id) if att_id else "")
            url = f"{base}{path}"
            try:
                if method == "POST":
                    rp = client.post(url, headers=headers_full, json=build_payload(uid, att_id))
                else:
                    rp = client.get(url, headers=headers_full)
                snippet = rp.text[:200].replace("\n", " ")
                print(f"  {method:4s} {path:48s} -> {rp.status_code}  {snippet}")
            except Exception as e:
                print(f"  {method:4s} {path:48s} -> ERROR {type(e).__name__}: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: probe_mail_attachments.py <user_id>")
        sys.exit(1)
    main(int(sys.argv[1]))
