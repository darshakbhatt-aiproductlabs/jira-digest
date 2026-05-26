#!/usr/bin/env python3
"""Generate docs/preview.html — a mocked-up digest used as the live example
on the landing page.

This calls the SAME render_email function the production script uses, so
the preview is structurally identical to a real digest. The data is
fabricated end-to-end (fake company names, fake assignees, fake tickets)
to avoid any risk of real customer data on a public page.

Re-run after changing mock data or the renderer:

    cd docs && python3 build_preview.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to path so we can import the production renderer.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from render_html import render_email  # noqa: E402


JIRA_BASE = "https://example-co.atlassian.net"
ACCENT = "#7c3aed"  # purple to match the landing page

# ---------------------------------------------------------------------------
# Mock digest sections — realistic shape and tone, fully fabricated.
# ---------------------------------------------------------------------------
SECTIONS = [
    {
        "id": "kpis",
        "title": "Key metrics",
        "kind": "kpi",
        "data": [
            ("Open", 127, 'project = "CUS" AND statusCategory != Done'),
            ("New (7d)", 12, 'project = "CUS" AND created >= -7d'),
            ("Closed (7d)", 18, 'project = "CUS" AND resolved >= -7d'),
            ("Critical open", 8, 'project = "CUS" AND priority IN (Highest, High) AND statusCategory != Done'),
        ],
        "columns": None,
        "note": None,
        "empty_message": None,
        "jql": None,
    },
    {
        "id": "critical",
        "title": "Critical & high priority — open",
        "kind": "table",
        "data": [
            {"key": "CUS-1024", "summary": "SSO login intermittently fails for SAML users",
             "assignee": "Alice Chen", "priority": "Highest", "status": "In Progress", "days_in_status": 31},
            {"key": "CUS-1018", "summary": "Billing webhook silently drops retries after 3 failures",
             "assignee": "Ben Martinez", "priority": "High", "status": "In Review", "days_in_status": 18},
            {"key": "CUS-0982", "summary": "Onboarding email duplicated when invite resent within 5 min",
             "assignee": "Carol Park", "priority": "High", "status": "In Progress", "days_in_status": 12},
            {"key": "CUS-0964", "summary": "Dashboard widget timeout on accounts with 1k+ projects",
             "assignee": "David Singh", "priority": "High", "status": "To Do", "days_in_status": 8},
            {"key": "CUS-0931", "summary": "CSV export drops Unicode chars in customer-facing reports",
             "assignee": "Elena Russo", "priority": "High", "status": "In Progress", "days_in_status": 5},
        ],
        "columns": ["key", "summary", "assignee", "priority", "status", "days_in_status"],
        "note": "showing 5 of 12",
        "empty_message": None,
        "jql": 'project = "CUS" AND priority IN (Highest, High) AND statusCategory != Done',
    },
    {
        "id": "status_summary",
        "title": "Status breakdown",
        "kind": "breakdown",
        "data": [
            ("In Progress", 42),
            ("To Do", 38),
            ("In Review", 24),
            ("Awaiting Customer", 18),
            ("Blocked", 5),
            ("Open", 0),  # zero count — still shown so stalls are visible
        ],
        "columns": None,
        "note": "total: 127",
        "empty_message": None,
        "jql": 'project = "CUS" AND statusCategory != Done',
    },
    {
        "id": "stuck",
        "title": "Stuck — no status change in 30+ days",
        "kind": "table",
        "data": [
            {"key": "CUS-0731", "summary": "Salesforce sync edge case for accounts with custom-field overrides",
             "status": "In Progress", "days_in_status": 89, "assignee": "Alice Chen"},
            {"key": "CUS-0844", "summary": "Webhooks dropped after retry threshold for high-volume tenants",
             "status": "To Do", "days_in_status": 54, "assignee": "(unassigned)"},
            {"key": "CUS-0807", "summary": "Audit log truncation on enterprise plans during peak hours",
             "status": "In Review", "days_in_status": 47, "assignee": "Ben Martinez"},
            {"key": "CUS-0901", "summary": "Bulk import error messaging unclear for partial-success cases",
             "status": "Awaiting Customer", "days_in_status": 33, "assignee": "Carol Park"},
        ],
        "columns": ["key", "summary", "status", "days_in_status", "assignee"],
        "note": "showing 4 of 7 stuck ≥ 30d",
        "empty_message": None,
        "jql": 'project = "CUS" AND statusCategory != Done',
    },
    {
        "id": "new_today",
        "title": "Created in last 24 hours",
        "kind": "table",
        "data": [
            {"key": "CUS-1102", "summary": "Cannot export project data to CSV from Reports page",
             "reporter": "Customer · Northstar Logistics", "priority": "High"},
            {"key": "CUS-1101", "summary": "Filter persistence broken across page reloads in Issues view",
             "reporter": "Customer · Pacific Foods", "priority": "Medium"},
            {"key": "CUS-1100", "summary": "Email notifications delayed by ~15 min for some users",
             "reporter": "Customer · Meridian Health", "priority": "Medium"},
        ],
        "columns": ["key", "summary", "reporter", "priority"],
        "note": None,
        "empty_message": None,
        "jql": 'project = "CUS" AND created >= -24h',
    },
    {
        "id": "by_customer",
        "title": "Top customer accounts by open ticket count",
        "kind": "groups",
        "data": [
            {"name": "Northstar Logistics", "count": 18, "samples": [
                {"key": "CUS-1024", "summary": "SSO login intermittently fails for SAML users"},
                {"key": "CUS-0982", "summary": "Onboarding email duplicated when invite resent"},
                {"key": "CUS-0901", "summary": "Bulk import error messaging unclear"},
            ]},
            {"name": "Pacific Foods", "count": 14, "samples": [
                {"key": "CUS-1101", "summary": "Filter persistence broken across page reloads"},
                {"key": "CUS-0844", "summary": "Webhooks dropped after retry threshold"},
            ]},
            {"name": "Meridian Health", "count": 11, "samples": [
                {"key": "CUS-1100", "summary": "Email notifications delayed by ~15 min"},
                {"key": "CUS-0931", "summary": "CSV export drops Unicode chars"},
            ]},
            {"name": "Atlas Manufacturing", "count": 9, "samples": [
                {"key": "CUS-0964", "summary": "Dashboard widget timeout on accounts with 1k+ projects"},
            ]},
            {"name": "Continental Energy", "count": 7, "samples": [
                {"key": "CUS-0807", "summary": "Audit log truncation on enterprise plans"},
            ]},
        ],
        "columns": ["key", "summary"],
        "note": "showing 5 of 14 customer accounts",
        "empty_message": None,
        "jql": 'project = "CUS" AND statusCategory != Done AND customer_account IS NOT EMPTY',
    },
]


def main() -> int:
    html = render_email(
        SECTIONS,
        subject="Daily Jira digest — example",
        jira_base=JIRA_BASE,
        accent=ACCENT,
        footer="Generated by jira-digest · mock data for landing page preview",
        web_url=None,
    )
    out = Path(__file__).resolve().parent / "preview.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
