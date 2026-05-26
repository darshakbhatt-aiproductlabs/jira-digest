"""Microsoft Teams delivery — incoming webhook with adaptive card.

Teams webhooks don't support full HTML, so the digest is converted to a
MessageCard with one section per digest section. Best-effort formatting.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import requests

# Allow importing the sibling `jira` module when this file is loaded via the
# delivery package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jira import search_url  # noqa: E402


def _facts_from_kpi(data: list[tuple], jira_base: str) -> list[dict[str, str]]:
    out = []
    for label, count, jql in data:
        if jql:
            out.append({"name": label, "value": f"[**{count}**]({search_url(jira_base, jql)})"})
        else:
            out.append({"name": label, "value": str(count)})
    return out


def _facts_from_breakdown(data: list[tuple[str, int]]) -> list[dict[str, str]]:
    return [{"name": name, "value": str(count)} for name, count in data]


def _markdown_from_table(rows: list[dict[str, Any]], columns: list[str], jira_base: str) -> str:
    out: list[str] = []
    base = jira_base.rstrip("/")
    for r in rows:
        bits = []
        for c in columns:
            v = r.get(c)
            if v is None or v == "":
                continue
            if c == "key":
                bits.append(f"[**{v}**]({base}/browse/{v})")
            elif c == "summary":
                bits.append(str(v))
            else:
                bits.append(f"_{c.replace('_', ' ')}:_ {v}")
        out.append("- " + " · ".join(bits))
    return "\n".join(out)


def _markdown_from_groups(data: list[dict[str, Any]], jira_base: str) -> str:
    base = jira_base.rstrip("/")
    out = []
    for g in data:
        # Group name → Jira deep-link filtered to that group.
        if g.get("jql"):
            url = search_url(jira_base, g["jql"])
            name_md = f"[**{g['name']}**]({url})"
        else:
            name_md = f"**{g['name']}**"
        line = f"{name_md} — {g['count']}"
        samples = [f"[{s.get('key')}]({base}/browse/{s.get('key')})"
                   for s in g.get("samples", []) if s.get("key")]
        if samples:
            line += f"  \n_e.g._ {', '.join(samples)}"
        out.append(line)
    return "\n\n".join(out)


def _build_card(sections: list[dict[str, Any]], title: str, jira_base: str,
                accent: str = "0052CC", web_url: str | None = None) -> dict[str, Any]:
    card_sections: list[dict[str, Any]] = []

    # Top-of-card link to the full hosted digest (if Pages is configured).
    if web_url:
        card_sections.append({
            "activityTitle": "📄 View full digest in browser",
            "text": f"[Open the complete digest with all rows]({web_url})",
        })

    for s in sections:
        kind = s["kind"]
        # If we have a JQL, make the section title a clickable link.
        jql = s.get("jql")
        if jql:
            block: dict[str, Any] = {
                "activityTitle": s["title"],
                "activitySubtitle": f"[View in Jira ↗]({search_url(jira_base, jql)})",
            }
            if s.get("note"):
                block["activitySubtitle"] += f"  ·  {s['note']}"
        else:
            block = {"activityTitle": s["title"]}
            if s.get("note"):
                block["activitySubtitle"] = s["note"]

        if kind == "kpi":
            block["facts"] = _facts_from_kpi(s["data"], jira_base)
        elif kind == "breakdown":
            block["facts"] = _facts_from_breakdown(s["data"])
        elif kind == "table":
            block["text"] = _markdown_from_table(s["data"], s["columns"], jira_base)
        elif kind == "groups":
            block["text"] = _markdown_from_groups(s["data"], jira_base)
        elif kind == "empty":
            block["text"] = f"_{s.get('empty_message') or 'No matching issues.'}_"

        card_sections.append(block)

    # Bottom CTA — repeat the full-digest link at the end so it's visible
    # after the recipient has scrolled the card.
    if web_url:
        card_sections.append({
            "activityTitle": "📄 Open the full digest in browser",
            "text": f"[Every section, no truncation]({web_url})",
        })

    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": title,
        "themeColor": accent.lstrip("#"),
        "title": title,
        "markdown": True,
        "sections": card_sections,
    }


def send(*, sections: list[dict[str, Any]], title: str, jira_base: str,
         config: dict[str, Any], accent: str = "#0052CC",
         web_url: str | None = None, **_kwargs) -> dict[str, Any]:
    url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not url:
        raise RuntimeError("Teams delivery: TEAMS_WEBHOOK_URL not set")
    card = _build_card(sections, title, jira_base, accent.lstrip("#"), web_url=web_url)
    r = requests.post(url, json=card, timeout=30)
    r.raise_for_status()
    return {"mode": "teams_webhook", "status": r.status_code}
