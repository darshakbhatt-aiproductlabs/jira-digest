"""Slack delivery — bot token (Block Kit) or incoming webhook."""
from __future__ import annotations

import json
import os
from typing import Any

import requests


def _send_via_bot(payload: dict[str, Any], channel_id: str) -> dict[str, Any]:
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("Slack bot delivery: SLACK_BOT_TOKEN not set")
    body = dict(payload)
    body["channel"] = channel_id
    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"},
        data=json.dumps(body), timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error')} (channel={channel_id})")
    return {"mode": "bot", "channel": channel_id, "ts": data.get("ts")}


def _send_via_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        raise RuntimeError("Slack webhook delivery: SLACK_WEBHOOK_URL not set")
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return {"mode": "webhook", "status": r.status_code}


def send(*, slack_payload: dict[str, Any], config: dict[str, Any], **_kwargs) -> dict[str, Any]:
    via = (config.get("via") or "bot").lower()
    if via == "bot":
        channel_id = config.get("channel_id")
        if not channel_id:
            raise RuntimeError("Slack bot delivery: delivery.slack.channel_id is required")
        return _send_via_bot(slack_payload, channel_id)
    if via == "webhook":
        return _send_via_webhook(slack_payload)
    raise RuntimeError(f"Unknown slack.via: {via!r} (expected 'bot' or 'webhook')")


def preflight_auth(token: str | None = None) -> dict[str, Any]:
    """Optional helper: verify SLACK_BOT_TOKEN with auth.test before sending."""
    token = token or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        return {"ok": False, "error": "no_token"}
    r = requests.post(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return r.json()
