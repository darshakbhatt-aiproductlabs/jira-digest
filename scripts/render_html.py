"""Render the digest as a self-contained HTML document for email delivery.

Inline styles only — email clients drop <style> blocks and external CSS.

Visual treatment:
- Section cards get a colored left border based on section type (or a
  per-section override from config — `accent: red|amber|green|blue|purple`).
- Tables auto-format common column types:
    * days_in_status / days / idle / age   → colored age badge (red ≥30d, amber 7-30d, green <7d)
    * priority                              → colored priority pill
    * amount / deal_amount / value / etc.   → right-aligned green money formatting
    * status                                → soft colored chip
- KPI sections render as bordered stat cards (not inline counters).
- status_breakdown sections render as a bar chart proportional to the largest count.
- Card titles include a "view in Jira ↗" pill that deep-links to the JQL.
"""
from __future__ import annotations

import re
from html import escape
from typing import Any, Iterable

from jira import search_url


# ---------------------------------------------------------------------------
# Accents (left-border colors per section type / per-section override)
# ---------------------------------------------------------------------------

ACCENT_PALETTE = {
    "blue":   "#0052CC",
    "amber":  "#FF8B00",
    "red":    "#DE350B",
    "green":  "#00875A",
    "purple": "#6554C0",
}

DEFAULT_ACCENT_BY_KIND = {
    "kpi":              "#0052CC",  # blue
    "table":            "#0052CC",  # blue (handle_list & handle_recent)
    "breakdown":        "#0052CC",  # blue (status_breakdown)
    "groups":           "#00875A",  # green (group_by)
    "empty":            "#6B778C",  # muted
}


def _resolve_accent(section: dict[str, Any], fallback: str) -> str:
    """Pick the card's left-border color: per-section override → ID heuristics → kind default → caller fallback."""
    explicit = section.get("accent")
    if isinstance(explicit, str):
        return ACCENT_PALETTE.get(explicit.lower(), explicit)  # accept literal hex too

    sid = (section.get("id") or "").lower()
    # Heuristic by id
    if "stuck" in sid or "bottleneck" in sid:
        return ACCENT_PALETTE["amber"]
    if "critical" in sid or "blocker" in sid or "urgent" in sid:
        return ACCENT_PALETTE["red"]
    if "customer" in sid or "account" in sid or "revenue" in sid:
        return ACCENT_PALETTE["green"]
    if "recent" in sid or "new_" in sid or sid.startswith("new") or "today" in sid:
        return ACCENT_PALETTE["blue"]
    if "score" in sid or "engage" in sid or "ranked" in sid or "pressure" in sid:
        return ACCENT_PALETTE["purple"]

    return DEFAULT_ACCENT_BY_KIND.get(section.get("kind", ""), fallback)


# ---------------------------------------------------------------------------
# Column-type detection + per-cell formatting
# ---------------------------------------------------------------------------

_AGE_COLS      = re.compile(r"(^|_)(days(_in_status)?|idle|age|stuck)($|_)", re.I)
_MONEY_COLS    = re.compile(r"(amount|money|value|deal|revenue|price|arr|mrr)", re.I)
_PRIORITY_COLS = re.compile(r"^priority$", re.I)
_STATUS_COLS   = re.compile(r"^status$", re.I)
_KEY_COLS      = re.compile(r"^(key|ticket|issue)$", re.I)


def _badge(text: str, bg: str, *, fg: str = "#FFFFFF") -> str:
    return (
        f'<span style="display:inline-block;padding:2px 9px;border-radius:999px;'
        f'font-size:11px;font-weight:700;color:{fg};background:{bg};'
        f'letter-spacing:0.02em;white-space:nowrap">{escape(text)}</span>'
    )


def _age_badge(days_value: Any) -> str | None:
    try:
        days = int(days_value)
    except (TypeError, ValueError):
        return None
    if days >= 30:
        bg = ACCENT_PALETTE["red"]
    elif days >= 7:
        bg = ACCENT_PALETTE["amber"]
    else:
        bg = ACCENT_PALETTE["green"]
    return _badge(f"{days}d", bg)


def _priority_badge(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip().lower()
    mapping = {
        "highest": ACCENT_PALETTE["red"],
        "blocker": ACCENT_PALETTE["red"],
        "critical": ACCENT_PALETTE["red"],
        "high":     ACCENT_PALETTE["amber"],
        "medium":   ACCENT_PALETTE["blue"],
        "low":      "#6B778C",
        "lowest":   "#6B778C",
        "trivial":  "#6B778C",
    }
    bg = mapping.get(v)
    return _badge(str(value), bg) if bg else None


def _money_html(value: Any) -> str | None:
    """Format a numeric value as a right-aligned green money string."""
    if value is None or value == "":
        return None
    try:
        n = float(str(value).replace(",", "").lstrip("$").strip())
    except ValueError:
        return None
    abs_n = abs(n)
    if abs_n >= 1_000_000:
        txt = f"${n/1_000_000:.1f}M"
    elif abs_n >= 1_000:
        txt = f"${int(n/1000)}k"
    else:
        txt = f"${int(n)}"
    return f'<span style="color:#00875A;font-weight:600">{escape(txt)}</span>'


def _status_chip(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip().lower()
    if v in ("done", "closed", "resolved"):
        return _badge(str(value), "#E3FCEF", fg="#006644")
    if v in ("blocked",):
        return _badge(str(value), "#FFEBE6", fg="#BF2600")
    if v in ("in progress", "in review"):
        return _badge(str(value), "#DEEBFF", fg="#0747A6")
    if v in ("awaiting customer", "awaiting triage", "needs info"):
        return _badge(str(value), "#FFFAE6", fg="#974F0C")
    # Fallback — soft neutral chip
    return _badge(str(value), "#F4F5F7", fg="#42526E")


def _link_issue(jira_base: str, key: str | None) -> str:
    if not key:
        return '<span style="color:#999">—</span>'
    safe = escape(str(key))
    return (
        f'<a href="{escape(jira_base.rstrip("/"))}/browse/{safe}" '
        f'style="color:#0052CC;text-decoration:none;font-family:monospace;font-size:12px;'
        f'background:rgba(0,82,204,0.06);padding:2px 8px;border-radius:4px;white-space:nowrap">'
        f'{safe}</a>'
    )


def _empty_cell() -> str:
    return '<span style="color:#999">—</span>'


def _wrap_link(inner_html: str, url: str | None) -> str:
    """Wrap an already-styled inner HTML in a Jira deep-link if a URL is given."""
    if not url:
        return inner_html
    return (
        f'<a href="{escape(url)}" style="text-decoration:none;color:inherit;'
        f'display:inline-block">{inner_html}</a>'
    )


def _cell_for(col: str, value: Any, jira_base: str,
              section_jql: str | None = None) -> tuple[str, str]:
    """Return (cell_inner_html, extra_td_style) for a (column, value) pair.

    Auto-detects column type from the column name and applies appropriate
    formatting (badges, money, ticket link). If `section_jql` is supplied,
    priority and status cells get wrapped in a Jira deep-link that filters
    the section's query by the cell's value.
    """
    if value is None or value == "":
        return _empty_cell(), ""

    if _KEY_COLS.match(col):
        return _link_issue(jira_base, value), "white-space:nowrap"

    if _AGE_COLS.search(col):
        badge = _age_badge(value)
        if badge:
            return badge, "text-align:center"

    if _PRIORITY_COLS.match(col):
        pill = _priority_badge(value)
        if pill:
            # Clickable priority pill → filtered Jira search
            if section_jql:
                url = search_url(jira_base, f'({section_jql}) AND priority = "{value}"')
                return _wrap_link(pill, url), ""
            return pill, ""

    if _STATUS_COLS.match(col):
        chip = _status_chip(value)
        if chip:
            if section_jql:
                url = search_url(jira_base, f'({section_jql}) AND status = "{value}"')
                return _wrap_link(chip, url), ""
            return chip, ""

    if _MONEY_COLS.search(col):
        money = _money_html(value)
        if money:
            return money, "text-align:right;white-space:nowrap"

    return escape(str(value)), ""


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _table(columns: list[str], rows: list[dict[str, Any]], jira_base: str,
           section_jql: str | None = None) -> str:
    head_cells = []
    for c in columns:
        align = "left"
        if _AGE_COLS.search(c):
            align = "center"
        elif _MONEY_COLS.search(c):
            align = "right"
        head_cells.append(
            f'<th style="text-align:{align};padding:9px 10px;background:#F4F5F7;'
            f'border-bottom:2px solid #DFE1E6;font-size:11px;text-transform:uppercase;'
            f'color:#5E6C84;letter-spacing:0.06em;font-weight:600">'
            f'{escape(c.replace("_", " "))}</th>'
        )
    head = "".join(head_cells)

    body_rows = []
    for r in rows:
        cells = []
        for c in columns:
            inner, extra = _cell_for(c, r.get(c), jira_base, section_jql)
            cells.append(
                f'<td style="padding:9px 10px;border-bottom:1px solid #F4F5F7;'
                f'vertical-align:top;{extra}">{inner}</td>'
            )
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
    )


def _render_kpi(section: dict[str, Any], jira_base: str) -> str:
    """KPI section → grid of bordered stat cards."""
    items = section["data"]
    cards = []
    for label, count, jql in items:
        url = search_url(jira_base, jql) if jql else None
        count_html = (
            f'<a href="{escape(url)}" style="color:#172B4D;text-decoration:none">{count}</a>'
            if url else str(count)
        )
        cards.append(
            '<div style="background:#FFFFFF;border:1px solid #DFE1E6;border-radius:8px;'
            'padding:14px 16px;text-align:center;flex:1 1 130px;min-width:120px">'
            f'<div style="font-size:11px;color:#5E6C84;text-transform:uppercase;'
            f'letter-spacing:0.04em">{escape(label)}</div>'
            f'<div style="font-size:26px;font-weight:800;color:#0052CC;line-height:1.1;'
            f'margin-top:5px">{count_html}</div>'
            '</div>'
        )
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:4px 0 0">'
        f'{"".join(cards)}</div>'
    )


def _render_breakdown(section: dict[str, Any]) -> str:
    """status_breakdown → bar chart proportional to max count, with the
    biggest value's bar at full width."""
    items = section["data"]
    if not items:
        return ""
    max_count = max((c for _, c in items), default=0) or 1
    rows = []
    for name, count in items:
        pct = int(round(100 * count / max_count))
        bar_color = "#0052CC"
        n = name.strip().lower()
        if n in ("blocked",):
            bar_color = ACCENT_PALETTE["red"]
        elif n in ("awaiting customer", "awaiting triage", "needs info"):
            bar_color = ACCENT_PALETTE["amber"]
        elif n in ("done", "closed", "resolved", "in review"):
            bar_color = ACCENT_PALETTE["green"]
        rows.append(
            '<tr>'
            f'<td style="padding:8px 12px 8px 0;font-weight:600;color:#172B4D;'
            f'white-space:nowrap;font-size:13px">{escape(name)}</td>'
            f'<td style="padding:8px 12px 8px 0;text-align:right;font-weight:700;'
            f'color:#172B4D;font-size:14px;width:60px">{count}</td>'
            f'<td style="padding:8px 0;width:100%">'
            f'<div style="height:8px;background:#F4F5F7;border-radius:999px;overflow:hidden">'
            f'<div style="height:100%;background:{bar_color};width:{pct}%;'
            f'border-radius:999px"></div></div></td>'
            '</tr>'
        )
    return (
        '<table style="width:100%;border-collapse:collapse">'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
    )


def _render_groups(section: dict[str, Any], jira_base: str) -> str:
    out = ['<div>']
    for g in section["data"]:
        samples_html = ""
        if g.get("samples"):
            sample_lines = []
            for s in g["samples"]:
                key_html = _link_issue(jira_base, s.get("key"))
                summary = escape(str(s.get("summary") or ""))
                sample_lines.append(f'<li style="margin:3px 0">{key_html} <span style="color:#172B4D">— {summary}</span></li>')
            samples_html = (
                '<ul style="margin:6px 0 0 0;padding-left:20px;color:#5E6C84;font-size:12.5px">'
                f'{"".join(sample_lines)}</ul>'
            )
        # Group name is clickable → Jira search filtered to this group.
        group_url = search_url(jira_base, g["jql"]) if g.get("jql") else None
        name_html = (
            f'<a href="{escape(group_url)}" '
            f'style="font-weight:600;color:#172B4D;font-size:14px;text-decoration:none;'
            f'border-bottom:1px dotted #97A0AF">{escape(g["name"])}</a>'
            if group_url
            else f'<span style="font-weight:600;color:#172B4D;font-size:14px">{escape(g["name"])}</span>'
        )
        out.append(
            '<div style="padding:10px 0;border-bottom:1px solid #F4F5F7">'
            f'{name_html}'
            f'<span style="color:#5E6C84;margin-left:8px;font-size:13px">— {g["count"]} open</span>'
            f'{samples_html}'
            '</div>'
        )
    out.append('</div>')
    return "".join(out)


def _render_empty(section: dict[str, Any]) -> str:
    msg = section.get("empty_message") or "No matching issues."
    return f'<p style="margin:4px 0;color:#5E6C84;font-style:italic">{escape(msg)}</p>'


def _section_card(title: str, body: str, *, note: str | None, accent: str,
                  deep_link: str | None) -> str:
    note_html = (
        f'<span style="color:#5E6C84;font-size:12px;font-weight:500;'
        f'white-space:nowrap;margin-left:auto">{escape(note)}</span>'
        if note else ""
    )
    if deep_link:
        title_html = (
            f'<a href="{escape(deep_link)}" '
            f'style="color:#172B4D;text-decoration:none;display:inline-flex;align-items:center;gap:8px">'
            f'<span>{escape(title)}</span>'
            f'<span style="color:#6554C0;font-size:11px;font-weight:500;'
            f'background:rgba(101,84,192,0.10);padding:2px 8px;border-radius:999px;'
            f'white-space:nowrap">view in Jira ↗</span>'
            f'</a>'
        )
    else:
        title_html = f'<span>{escape(title)}</span>'
    return (
        f'<div style="background:#FFFFFF;border:1px solid #DFE1E6;border-left:4px solid {accent};'
        f'border-radius:6px;padding:16px 20px 18px;margin:0 0 16px;'
        f'box-shadow:0 1px 2px rgba(9,30,66,0.04)">'
        f'<div style="display:flex;align-items:center;gap:12px;margin:0 0 12px;'
        f'padding-bottom:8px;border-bottom:1px solid #DFE1E6">'
        f'<h2 style="margin:0;font-size:15.5px;font-weight:700;color:#172B4D">{title_html}</h2>'
        f'{note_html}</div>'
        f'{body}'
        f'</div>'
    )


def render_section(section: dict[str, Any], jira_base: str, accent_fallback: str) -> str:
    kind = section["kind"]
    jql = section.get("jql")
    if kind == "kpi":
        body = _render_kpi(section, jira_base)
    elif kind == "table":
        body = _table(section["columns"], section["data"], jira_base, section_jql=jql)
    elif kind == "breakdown":
        body = _render_breakdown(section)
    elif kind == "groups":
        body = _render_groups(section, jira_base)
    elif kind == "empty":
        body = _render_empty(section)
    else:
        body = f'<pre>{escape(str(section.get("data")))}</pre>'
    deep_link = search_url(jira_base, jql) if jql else None
    accent = _resolve_accent(section, accent_fallback)
    return _section_card(section["title"], body, note=section.get("note"),
                         accent=accent, deep_link=deep_link)


# ---------------------------------------------------------------------------
# Email shell + footer CTA
# ---------------------------------------------------------------------------

HANDOFF_CTA = (
    '<div style="background:linear-gradient(135deg,rgba(101,84,192,0.08),rgba(56,189,248,0.05));'
    'border:1px solid rgba(101,84,192,0.30);border-radius:10px;padding:16px 20px;'
    'margin:18px 0 8px;font-size:13.5px;color:#172B4D;line-height:1.55">'
    '<div style="font-weight:700;color:#5b21b6;margin-bottom:6px">🤖 Want this for your own Jira?</div>'
    'Copy the <b>interactive handoff prompt</b> from the '
    '<a href="https://github.com/darshakbhatt-aiproductlabs/jira-digest#interactive-handoff-prompt" '
    'style="color:#0052CC;text-decoration:none;font-weight:600">jira-digest README</a> '
    'and paste it into Claude Code, Codex, Cursor, or any LLM with file access. '
    'The assistant interviews you and configures everything — ~20 minutes end to end.'
    '</div>'
)


def render_email(sections: list[dict[str, Any]], *, subject: str, jira_base: str,
                 accent: str = "#0052CC", footer: str | None = None,
                 web_url: str | None = None,
                 include_handoff_cta: bool = True) -> str:
    body = "".join(render_section(s, jira_base, accent) for s in sections)
    footer_html = (
        f'<p style="font-size:11px;color:#97A0AF;margin:24px 0 0 0;text-align:center">{escape(footer)}</p>'
        if footer else ""
    )
    web_html = (
        f'<p style="margin:0 0 14px;font-size:13px;color:#5E6C84">'
        f'📄 <a href="{escape(web_url)}" '
        f'style="color:#0052CC;text-decoration:none;font-weight:600">View full digest in browser</a>'
        f'</p>' if web_url else ""
    )
    cta_html = HANDOFF_CTA if include_handoff_cta else ""
    return (
        '<!doctype html><html><body style="margin:0;padding:0;background:#F4F5F7;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;'
        'color:#172B4D">'
        '<div style="max-width:760px;margin:0 auto;padding:24px 20px 32px">'
        f'<h1 style="font-size:20px;color:#0052CC;margin:0 0 6px;letter-spacing:-0.01em;'
        f'border-bottom:3px solid #0052CC;padding-bottom:10px">{escape(subject)}</h1>'
        '<p style="color:#6B778C;font-size:12.5px;margin:6px 0 18px">'
        'Daily Jira digest · generated by GitHub Actions</p>'
        f'{web_html}'
        f'{body}'
        f'{cta_html}'
        f'{footer_html}'
        '</div></body></html>'
    )


# Backwards-compat alias used by older callers / tests.
def _cell(value: Any) -> str:  # pragma: no cover
    if value is None or value == "":
        return _empty_cell()
    return escape(str(value))
