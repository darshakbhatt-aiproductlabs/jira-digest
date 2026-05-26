"""Render the digest as a self-contained HTML document for email delivery.

Inline styles only — email clients drop <style> blocks and external CSS.
"""
from __future__ import annotations

from html import escape
from typing import Any

from jira import search_url


def _link_issue(jira_base: str, key: str | None) -> str:
    if not key:
        return ""
    safe = escape(str(key))
    return f'<a href="{escape(jira_base.rstrip("/"))}/browse/{safe}" style="color:#0052CC;text-decoration:none">{safe}</a>'


def _cell(value: Any) -> str:
    if value is None or value == "":
        return '<span style="color:#999">—</span>'
    return escape(str(value))


def _table(columns: list[str], rows: list[dict[str, Any]], jira_base: str) -> str:
    head = "".join(
        f'<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #DFE1E6;'
        f'font-size:12px;text-transform:uppercase;color:#5E6C84">{escape(c.replace("_", " "))}</th>'
        for c in columns
    )
    body_rows = []
    for r in rows:
        cells = []
        for c in columns:
            v = r.get(c)
            if c == "key":
                cells.append(f'<td style="padding:6px 10px;border-bottom:1px solid #F4F5F7;'
                             f'font-family:monospace;white-space:nowrap">{_link_issue(jira_base, v)}</td>')
            else:
                cells.append(f'<td style="padding:6px 10px;border-bottom:1px solid #F4F5F7">{_cell(v)}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
    )


def _section_card(title: str, body: str, *, note: str | None, accent: str,
                  deep_link: str | None) -> str:
    note_html = (
        f'<span style="float:right;font-size:11px;color:#5E6C84;font-weight:normal">{escape(note)}</span>'
        if note else ""
    )
    if deep_link:
        title_html = (
            f'<a href="{escape(deep_link)}" style="color:#172B4D;text-decoration:none">'
            f'{escape(title)}'
            f'<span style="color:#0052CC;font-weight:normal;font-size:12px;margin-left:6px">↗</span>'
            f'</a>'
        )
    else:
        title_html = escape(title)
    return (
        f'<div style="background:#FFFFFF;border:1px solid #DFE1E6;border-left:4px solid {accent};'
        f'border-radius:4px;padding:14px 18px;margin-bottom:14px">'
        f'<h2 style="margin:0 0 10px 0;font-size:15px;color:#172B4D">{title_html}{note_html}</h2>'
        f'{body}'
        f'</div>'
    )


def _render_kpi(section: dict[str, Any], jira_base: str) -> str:
    items = section["data"]
    cells = []
    for label, count, jql in items:
        url = search_url(jira_base, jql) if jql else None
        count_html = (
            f'<a href="{escape(url)}" style="color:#172B4D;text-decoration:none">{count}</a>'
            if url else str(count)
        )
        cells.append(
            '<td style="padding:6px 18px 6px 0;vertical-align:top">'
            f'<div style="font-size:11px;color:#5E6C84;text-transform:uppercase">{escape(label)}</div>'
            f'<div style="font-size:22px;font-weight:600;color:#172B4D">{count_html}</div>'
            '</td>'
        )
    return f'<table><tr>{"".join(cells)}</tr></table>'


def _render_breakdown(section: dict[str, Any]) -> str:
    items = section["data"]
    rows = "".join(
        f'<tr><td style="padding:4px 12px 4px 0">{escape(name)}</td>'
        f'<td style="padding:4px 0;font-weight:600;color:#172B4D">{count}</td></tr>'
        for name, count in items
    )
    return f'<table style="font-size:13px">{rows}</table>'


def _render_groups(section: dict[str, Any], jira_base: str) -> str:
    out = ['<div>']
    for g in section["data"]:
        samples_html = ""
        if g.get("samples"):
            sample_lines = []
            for s in g["samples"]:
                key_html = _link_issue(jira_base, s.get("key"))
                summary = _cell(s.get("summary"))
                sample_lines.append(f'<li style="margin:2px 0">{key_html} — {summary}</li>')
            samples_html = (
                '<ul style="margin:4px 0 0 0;padding-left:18px;color:#5E6C84;font-size:12px">'
                f'{"".join(sample_lines)}</ul>'
            )
        out.append(
            '<div style="padding:8px 0;border-bottom:1px solid #F4F5F7">'
            f'<span style="font-weight:600;color:#172B4D">{escape(g["name"])}</span>'
            f'<span style="color:#5E6C84;margin-left:8px">({g["count"]})</span>'
            f'{samples_html}'
            '</div>'
        )
    out.append('</div>')
    return "".join(out)


def _render_empty(section: dict[str, Any]) -> str:
    msg = section.get("empty_message") or "No matching issues."
    return f'<p style="margin:4px 0;color:#5E6C84;font-style:italic">{escape(msg)}</p>'


def render_section(section: dict[str, Any], jira_base: str, accent: str) -> str:
    kind = section["kind"]
    if kind == "kpi":
        body = _render_kpi(section, jira_base)
    elif kind == "table":
        body = _table(section["columns"], section["data"], jira_base)
    elif kind == "breakdown":
        body = _render_breakdown(section)
    elif kind == "groups":
        body = _render_groups(section, jira_base)
    elif kind == "empty":
        body = _render_empty(section)
    else:
        body = f'<pre>{escape(str(section.get("data")))}</pre>'
    jql = section.get("jql")
    deep_link = search_url(jira_base, jql) if jql else None
    return _section_card(section["title"], body, note=section.get("note"),
                         accent=accent, deep_link=deep_link)


def render_email(sections: list[dict[str, Any]], *, subject: str, jira_base: str,
                 accent: str = "#0052CC", footer: str | None = None,
                 web_url: str | None = None) -> str:
    body = "".join(render_section(s, jira_base, accent) for s in sections)
    footer_html = (
        f'<p style="font-size:11px;color:#97A0AF;margin:24px 0 0 0;text-align:center">{escape(footer)}</p>'
        if footer else ""
    )
    web_html = (
        f'<p style="margin:0 0 12px 0;font-size:12px;color:#5E6C84">'
        f'📄 <a href="{escape(web_url)}" style="color:#0052CC">View full digest in browser</a>'
        f'</p>' if web_url else ""
    )
    return (
        '<!doctype html><html><body style="margin:0;padding:0;background:#F4F5F7;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif;color:#172B4D">'
        '<div style="max-width:760px;margin:0 auto;padding:20px">'
        f'<h1 style="font-size:18px;color:#172B4D;margin:0 0 16px 0">{escape(subject)}</h1>'
        f'{web_html}'
        f'{body}'
        f'{footer_html}'
        '</div></body></html>'
    )
