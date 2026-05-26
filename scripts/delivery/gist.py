"""Upload the full HTML digest as a GitHub gist; return a preview URL.

Slack and Teams messages embed this URL as a "View full digest in browser"
link, so recipients who hit chat-platform truncation limits can still see
everything.

Why gists (not Pages):
  - No repo Settings to change. One PAT with `gist` scope is all it takes.
  - Each day's digest is a separate gist with a separate, permanent URL —
    a Slack link sent on Monday still shows Monday's digest on Friday.
  - Works for public and private repos identically (gist visibility is
    independent of repo visibility).

Privacy note on "secret" gists:
  - public:true  → listed on the user's profile and indexed by search.
  - public:false → "secret" — NOT listed, NOT in search results — but
    anyone with the URL can read it (no auth). That's the right default
    for Slack/Teams links: the URL is shared only with the intended
    audience via the chat channel, and isn't discoverable elsewhere.

The HTML is rendered in-browser via htmlpreview.github.io, a popular
third-party wrapper that fetches the raw gist content and serves it with
the correct MIME type. (Browsers won't render raw HTML served directly
from gist.githubusercontent.com because of GitHub's Content-Type policy.)
"""
from __future__ import annotations

import os
from typing import Any

import requests


def upload(html: str, *, today: str, config: dict[str, Any]) -> str | None:
    """Create a gist containing the HTML and return the htmlpreview URL.

    Returns None if disabled, if GIST_PAT isn't set, or if the upload fails
    for any reason — the digest still delivers via the other channels.
    """
    pat = os.environ.get("GIST_PAT")
    if not pat:
        print("[gist] GIST_PAT not set — skipping upload (Slack/Teams won't get a 'view in browser' link)",
              flush=True)
        return None

    is_public = bool(config.get("public", False))
    description_template = config.get("description") or "Jira digest — {date}"
    description = description_template.replace("{date}", today)
    filename = f"jira-digest-{today}.html"

    try:
        r = requests.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"token {pat}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "description": description,
                "public": is_public,
                "files": {filename: {"content": html}},
            },
            timeout=20,
        )
    except requests.RequestException as e:
        print(f"[gist] network error: {e}", flush=True)
        return None

    if r.status_code not in (200, 201):
        print(f"[gist] HTTP {r.status_code}: {r.text[:300]}", flush=True)
        return None

    body = r.json()
    raw_url = (body.get("files") or {}).get(filename, {}).get("raw_url", "")
    if not raw_url:
        # Fall back to the gist landing page (shows source, not rendered).
        landing = body.get("html_url")
        if landing:
            print(f"[gist] uploaded (no raw_url returned) → {landing}", flush=True)
        return landing

    preview_url = f"https://htmlpreview.github.io/?{raw_url}"
    visibility = "public" if is_public else "secret"
    print(f"[gist] uploaded ({visibility}) → {preview_url}", flush=True)
    return preview_url
