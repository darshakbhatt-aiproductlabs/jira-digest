"""Generic SMTP delivery — works with Mailgun, SendGrid, Office365, custom servers."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


def send(*, html: str, subject: str, config: dict[str, Any], **_kwargs) -> dict[str, Any]:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    sender = config.get("from") or os.environ.get("SMTP_FROM") or user
    use_tls = os.environ.get("SMTP_USE_TLS", "1") not in ("0", "false", "False", "")

    if not (host and sender):
        raise RuntimeError("SMTP delivery: SMTP_HOST and a sender address are required")

    to = config.get("to") or []
    cc = config.get("cc") or []
    if not to:
        raise RuntimeError("SMTP delivery: no recipients in delivery.email.to")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.attach(MIMEText(html, "html", "utf-8"))

    recipients = list(to) + list(cc)
    ctx = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            if user:
                s.login(user, password or "")
            s.sendmail(sender, recipients, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            if use_tls:
                s.starttls(context=ctx)
                s.ehlo()
            if user:
                s.login(user, password or "")
            s.sendmail(sender, recipients, msg.as_string())

    return {"mode": "smtp", "to": recipients, "host": f"{host}:{port}"}
