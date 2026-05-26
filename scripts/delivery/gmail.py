"""Gmail OAuth2 delivery.

Two modes:
  - draft (recommended): creates a Gmail draft you review and send manually.
  - send: dispatches the message immediately.

Requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN secrets.
Run scripts/get_gmail_token.py locally once to obtain them.
"""
from __future__ import annotations

import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"


def _refresh_access_token() -> str:
    cid = os.environ.get("GMAIL_CLIENT_ID")
    cs = os.environ.get("GMAIL_CLIENT_SECRET")
    rt = os.environ.get("GMAIL_REFRESH_TOKEN")
    if not (cid and cs and rt):
        raise RuntimeError("Missing GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN")
    r = requests.post(TOKEN_URL, data={
        "client_id": cid, "client_secret": cs,
        "refresh_token": rt, "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _build_message(*, subject: str, html: str, to: list[str], cc: list[str] | None) -> str:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.attach(MIMEText(html, "html", "utf-8"))
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def send(*, html: str, subject: str, config: dict[str, Any], **_kwargs) -> dict[str, Any]:
    to = config.get("to") or []
    cc = config.get("cc") or []
    if not to:
        raise RuntimeError("Gmail delivery: no recipients in delivery.email.to")
    draft_mode = bool(config.get("gmail_draft_mode", True))

    access_token = _refresh_access_token()
    raw = _build_message(subject=subject, html=html, to=to, cc=cc)
    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json"}

    if draft_mode:
        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        payload = {"message": {"raw": raw}}
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        return {"mode": "draft", "id": r.json().get("id"), "to": to}

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    payload = {"raw": raw}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return {"mode": "send", "id": r.json().get("id"), "to": to}
