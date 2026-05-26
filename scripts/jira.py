"""Thin Jira REST API wrapper.

Handles auth, pagination, custom-field alias substitution, and changelog-based
days-in-status computation. No business logic — that lives in sections.py.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import quote

import requests


def search_url(base_url: str, jql: str) -> str:
    """Return a browser-openable Jira search URL for a JQL string.

    Used by renderers to turn each section title into a deep-link the
    reader can click to see the full live list in Jira.
    """
    return f"{base_url.rstrip('/')}/issues/?jql={quote(jql, safe='')}"


class JiraClient:
    def __init__(self, base_url: str, email: str, token: str, *,
                 timeout: int = 30, page_size: int = 100,
                 field_aliases: dict[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = (email, token)
        self.timeout = timeout
        self.page_size = page_size
        self.field_aliases = dict(field_aliases or {})
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    # --- preflight ---------------------------------------------------------
    def preflight(self) -> dict[str, Any]:
        r = self.session.get(f"{self.base_url}/rest/api/3/myself", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # --- JQL / fields ------------------------------------------------------
    def expand_aliases(self, jql: str) -> str:
        """Replace alias tokens in a JQL string with customfield_XXXXX IDs.

        Whole-word match only, so `customer_account` becomes `cf[XXXXX]`
        without mangling substrings.
        """
        out = jql
        for alias, cf_id in self.field_aliases.items():
            out = re.sub(rf"\b{re.escape(alias)}\b", cf_id, out)
        return out

    def resolve_field(self, name: str) -> str:
        """Translate a field alias or builtin name into the Jira field ID."""
        return self.field_aliases.get(name, name)

    # --- search ------------------------------------------------------------
    def search(self, jql: str, *, fields: Iterable[str] | None = None,
               expand: Iterable[str] | None = None,
               max_results: int | None = None) -> list[dict[str, Any]]:
        """Page through /rest/api/3/search/jql and return all matching issues."""
        url = f"{self.base_url}/rest/api/3/search/jql"
        body: dict[str, Any] = {
            "jql": self.expand_aliases(jql),
            "maxResults": min(self.page_size, max_results or self.page_size),
        }
        if fields:
            body["fields"] = [self.resolve_field(f) for f in fields]
        if expand:
            body["expand"] = list(expand)

        out: list[dict[str, Any]] = []
        next_token: str | None = None
        while True:
            if next_token:
                body["nextPageToken"] = next_token
            r = self.session.post(url, json=body, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            issues = data.get("issues", [])
            out.extend(issues)
            if max_results and len(out) >= max_results:
                return out[:max_results]
            next_token = data.get("nextPageToken")
            if not next_token or not issues:
                return out

    def count(self, jql: str) -> int:
        """Return the count of issues matching a JQL, using the approximate-count endpoint."""
        url = f"{self.base_url}/rest/api/3/search/approximate-count"
        r = self.session.post(url, json={"jql": self.expand_aliases(jql)}, timeout=self.timeout)
        if r.status_code == 200:
            data = r.json()
            return int(data.get("count", 0))
        # Fall back to a paged search if approximate-count isn't available.
        return len(self.search(jql, fields=["summary"]))


# ---------------------------------------------------------------------------
# Helpers that operate on issue dicts (not bound to the client).
# ---------------------------------------------------------------------------

ISO_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    # Jira returns offsets like "+0000" — Python <3.11 needs colon-less handling.
    try:
        return datetime.strptime(s, ISO_FMT)
    except ValueError:
        # Try without microseconds.
        try:
            return datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            return None


def days_in_current_status(issue: dict[str, Any], *, now: datetime | None = None) -> int:
    """Days since the issue last transitioned into its current status.

    Requires the search call to have included `expand=["changelog"]`. Falls
    back to `created` date if no status change is recorded.
    """
    now = now or datetime.now(timezone.utc)
    current_status = (issue.get("fields", {}).get("status") or {}).get("name", "")
    histories = (issue.get("changelog") or {}).get("histories", [])

    last_transition: datetime | None = None
    for h in histories:
        for item in h.get("items", []):
            if item.get("field") == "status" and item.get("toString") == current_status:
                ts = _parse_iso(h.get("created"))
                if ts and (not last_transition or ts > last_transition):
                    last_transition = ts

    if not last_transition:
        last_transition = _parse_iso(issue.get("fields", {}).get("created"))
    if not last_transition:
        return 0
    return max(0, (now - last_transition).days)


def get_field(issue: dict[str, Any], field: str) -> Any:
    """Extract a field value from an issue. Handles common shapes: status,
    priority, assignee, reporter, plus raw custom fields."""
    f = issue.get("fields", {})
    raw = f.get(field)
    if raw is None:
        return None
    if isinstance(raw, dict):
        # Common Jira shapes
        for key in ("displayName", "name", "value", "key"):
            if key in raw and raw[key] is not None:
                return raw[key]
    return raw


def make_client_from_env(field_aliases: dict[str, str] | None = None,
                         page_size: int = 100, timeout: int = 30) -> JiraClient:
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]
    return JiraClient(base, email, token,
                      timeout=timeout, page_size=page_size,
                      field_aliases=field_aliases or {})
