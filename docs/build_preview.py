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

import html as html_lib
import sys
from pathlib import Path

# Add scripts/ to path so we can import the production renderer.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from render_html import render_email  # noqa: E402


# Per-section tooltips that appear when you hover the pulsating purple dot
# next to each section title in the landing-page preview. They explain
# exactly what's configurable about that section.
SECTION_TOOLTIPS: dict[str, str] = {
    "Key metrics": (
        "KPI counters. Add or remove counters by editing the `metrics` list under "
        "this section in config/digest.yml — each one runs its own JQL count query."
    ),
    "Critical & high priority — open": (
        "Customize the JQL filter, which columns appear, the sort order, and how many "
        "rows show before the link to the full Jira search."
    ),
    "Status breakdown": (
        "Edit `statuses.active` in config to control which statuses appear here. "
        "Zero-count statuses are kept on purpose so stalls are visible."
    ),
    "Stuck — no status change in 30+ days": (
        "Change the `threshold_days` (14, 30, 90…), choose the columns, and tune the "
        "sort. Dwell time is computed from Jira's changelog — no false positives."
    ),
    "Created in last 24 hours": (
        "Swap the time window to anything Jira understands: -24h, -7d, startOfWeek(), "
        "your last sprint. The section name is yours to set."
    ),
    "Top customer accounts by open ticket count": (
        "Group by any field — assignee for bandwidth, customer for impact, component "
        "for hot-spots, severity for risk. Custom fields work via alias."
    ),
}


DEMO_BANNER_HTML = """
<div class="demo-banner" role="note">
  <span class="demo-banner-icon" aria-hidden="true">💡</span>
  <span class="demo-banner-text">
    <strong>This is a sample digest.</strong> Every section is configurable —
    <strong>hover the purple dots</strong> next to each title to see what you can change.
  </span>
</div>
"""


# CSS injected into the preview only — controls the pulsating dots, the
# tooltips, the demo banner, and a few hover affordances. None of this
# touches the production renderer, so real emails stay untouched.
PREVIEW_STYLES = """
<style>
  /* Demo banner */
  .demo-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.10), rgba(56, 189, 248, 0.06));
    border: 1px solid rgba(124, 58, 237, 0.35);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 0 0 18px 0;
    font-size: 13.5px;
    color: #172B4D;
    line-height: 1.5;
  }
  .demo-banner-icon { font-size: 22px; flex-shrink: 0; }
  .demo-banner-text strong { color: #5b21b6; font-weight: 600; }

  /* Pulsating dot + tooltip */
  .dot-pulse {
    position: relative;
    display: inline-block;
    width: 9px;
    height: 9px;
    margin-left: 10px;
    background: #7c3aed;
    border-radius: 50%;
    cursor: help;
    vertical-align: middle;
    flex-shrink: 0;
  }
  .dot-pulse::before {
    content: "";
    position: absolute;
    inset: -5px;
    border-radius: 50%;
    background: rgba(124, 58, 237, 0.35);
    animation: dot-pulse-ring 1.8s ease-out infinite;
    pointer-events: none;
  }
  @keyframes dot-pulse-ring {
    0%   { transform: scale(0.5); opacity: 0.9; }
    100% { transform: scale(2.4); opacity: 0;   }
  }
  .dot-pulse::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + 12px);
    left: 50%;
    transform: translateX(-50%) translateY(4px);
    width: max-content;
    max-width: 320px;
    background: #172B4D;
    color: #ffffff;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12.5px;
    font-weight: 400;
    line-height: 1.5;
    white-space: normal;
    text-align: left;
    box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.45);
    opacity: 0;
    pointer-events: none;
    transition: opacity 150ms ease, transform 150ms ease;
    z-index: 50;
  }
  .dot-pulse:hover::after,
  .dot-pulse:focus::after {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  /* Small caret on the tooltip */
  .dot-pulse[data-tooltip]:hover::before,
  .dot-pulse[data-tooltip]:focus::before {
    /* Keep the ring animation going while hovered */
  }

  /* Hover affordances on the email itself */
  div[style*="border-left:4px solid"] {
    transition: box-shadow 200ms ease, transform 200ms ease;
  }
  div[style*="border-left:4px solid"]:hover {
    box-shadow: 0 18px 40px -18px rgba(124, 58, 237, 0.35);
    transform: translateY(-1px);
  }
  table tbody tr {
    transition: background 150ms ease;
  }
  table tbody tr:hover {
    background: #FAFAFC;
  }

  /* Fix the H2 to allow the dot to render outside it without clipping */
  h2 { overflow: visible !important; }
</style>
"""


def annotate(html: str) -> str:
    """Post-process the rendered email HTML to add preview-only affordances:
    a demo banner, pulsating dots with tooltips, and hover effects.
    """
    # 1. Give the document a <head> so the <style> block lives in the right place.
    if "<head>" not in html:
        html = html.replace(
            "<!doctype html><html>",
            "<!doctype html><html><head><meta charset=\"utf-8\">" + PREVIEW_STYLES + "</head>",
            1,
        )

    # 2. Drop in the demo banner right after the digest's H1.
    html = html.replace("</h1>", "</h1>" + DEMO_BANNER_HTML, 1)

    # 3. After each known section title, append a pulsating dot with that
    #    section's tooltip. We match the unique title text inside the linked
    #    H2 the renderer emits.
    for title, tooltip in SECTION_TOOLTIPS.items():
        escaped_title = html_lib.escape(title)
        # The renderer ends each clickable title with `↗</span></a>` — we
        # inject our dot right after that closing `</a>`.
        marker = (
            f'>{escaped_title}'
            '<span style="color:#0052CC;font-weight:normal;font-size:12px;margin-left:6px">↗</span>'
            '</a>'
        )
        dot = (
            f'<span class="dot-pulse" tabindex="0" role="img" '
            f'aria-label="{html_lib.escape(tooltip)}" '
            f'data-tooltip="{html_lib.escape(tooltip)}"></span>'
        )
        if marker in html:
            html = html.replace(marker, marker + dot, 1)
        else:
            # Fallback: title with no deep-link (shouldn't happen for our sample,
            # but handle it anyway so future content doesn't silently drop a dot).
            fallback = f'>{escaped_title}</h2>'
            if fallback in html:
                html = html.replace(fallback, f'>{escaped_title}{dot}</h2>', 1)

    return html


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
    # Post-process: add demo banner, pulsating dots, hover affordances.
    html = annotate(html)

    out = Path(__file__).resolve().parent / "preview.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({len(html):,} bytes, {html.count('dot-pulse')} pulsating dots)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
