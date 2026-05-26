"""Render the digest as Slack Block Kit JSON."""
from __future__ import annotations

from typing import Any

from jira import search_url

SLACK_MAX_BLOCKS = 50  # Slack hard limit per message


def _issue_link(jira_base: str, key: str | None) -> str:
    if not key:
        return ""
    return f"<{jira_base.rstrip('/')}/browse/{key}|{key}>"


def _row_line(row: dict[str, Any], columns: list[str], jira_base: str) -> str:
    """Render one issue row as a single mrkdwn line."""
    parts = []
    for c in columns:
        v = row.get(c)
        if c == "key":
            parts.append(f"*{_issue_link(jira_base, v)}*")
        elif v is None or v == "":
            continue
        elif c == "summary":
            parts.append(str(v))
        else:
            parts.append(f"_{c.replace('_', ' ')}:_ {v}")
    return " · ".join(parts)


def _section_blocks(section: dict[str, Any], jira_base: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    title = section["title"]
    note = section.get("note")
    jql = section.get("jql")
    if jql:
        url = search_url(jira_base, jql)
        # Wrap the bold title in a Slack link so clicking the section header
        # opens a live Jira search for the underlying JQL.
        title_md = f"<{url}|*{title}*>  _view in Jira ↗_"
    else:
        title_md = f"*{title}*"
    header_text = title_md
    if note:
        header_text += f"  _({note})_"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": header_text}})

    kind = section["kind"]
    if kind == "empty":
        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"_{section.get('empty_message') or 'No matching issues.'}_"}
        ]})

    elif kind == "kpi":
        # Per-metric deep-link: each count number becomes its own Jira search link.
        parts = []
        for label, count, m_jql in section["data"]:
            if m_jql:
                parts.append(f"<{search_url(jira_base, m_jql)}|*{count}*> {label}")
            else:
                parts.append(f"*{count}* {label}")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "   ".join(parts)}})

    elif kind == "breakdown":
        lines = [f"`{count:>4}`  {name}" for name, count in section["data"]]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}})

    elif kind == "table":
        # Slack section blocks are capped at 3000 chars — chunk if needed.
        rows = section["data"]
        columns = section["columns"]
        lines = ["• " + _row_line(r, columns, jira_base) for r in rows]
        chunk: list[str] = []
        chunk_len = 0
        for line in lines:
            if chunk_len + len(line) + 1 > 2800 and chunk:
                blocks.append({"type": "section",
                               "text": {"type": "mrkdwn", "text": "\n".join(chunk)}})
                chunk, chunk_len = [], 0
            chunk.append(line)
            chunk_len += len(line) + 1
        if chunk:
            blocks.append({"type": "section",
                           "text": {"type": "mrkdwn", "text": "\n".join(chunk)}})

    elif kind == "groups":
        lines = []
        for g in section["data"]:
            line = f"*{g['name']}* — {g['count']}"
            if g.get("samples"):
                sample_keys = ", ".join(_issue_link(jira_base, s.get("key")) for s in g["samples"])
                line += f"\n   _e.g._ {sample_keys}"
            lines.append(line)
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": "\n".join(lines)}})

    blocks.append({"type": "divider"})
    return blocks


def render_slack(sections: list[dict[str, Any]], *, title: str, jira_base: str,
                 footer: str | None = None, web_url: str | None = None) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150]}}
    ]
    # Optional "view full digest in browser" CTA right under the header.
    if web_url:
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"📄 <{web_url}|*View full digest in browser*>  "
                               f"_(no Slack truncation, all rows visible)_"}})
        blocks.append({"type": "divider"})

    truncated = False
    for s in sections:
        s_blocks = _section_blocks(s, jira_base)
        # Reserve 3 blocks at the end for a possible truncation note + footer.
        if len(blocks) + len(s_blocks) > SLACK_MAX_BLOCKS - 3:
            truncated = True
            break
        blocks.extend(s_blocks)

    if truncated:
        msg = "_…truncated to fit Slack's 50-block limit._"
        if web_url:
            msg = f"_…truncated. <{web_url}|View the full digest in browser> for everything._"
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": msg}]})

    if footer:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": footer}]})

    # Trim to Slack's hard limit.
    blocks = blocks[:SLACK_MAX_BLOCKS]
    return {
        "blocks": blocks,
        "text": title,                # fallback for notifications
        "unfurl_links": False,
        "unfurl_media": False,
    }
