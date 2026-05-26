"""Section handlers.

Each section type fetches data via the JiraClient and returns a renderer-
friendly dict. Renderers (HTML / Slack) consume that dict.

Intermediate shape:
    {
      "id":            str,
      "title":         str,
      "kind":          "kpi" | "table" | "breakdown" | "groups" | "empty",
      "data":          (varies — see below),
      "columns":       list[str] | None,
      "note":          str | None,            # e.g. "showing 25 of 312"
      "empty_message": str | None,
      "jql":           str | None,            # final JQL after alias + global-filter expansion;
                                              # renderers use this to build deep-links
    }

Data shapes by kind:
    kpi:        [(label, count, jql), ...]
    table:      [ {column_name: value, ...}, ... ]
    breakdown:  [(status_name, count), ...]
    groups:     [ {"name": str, "count": int, "samples": [row, ...]}, ... ]
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable

from jira import JiraClient, days_in_current_status, get_field


# ---------------------------------------------------------------------------
# JQL substitution
# ---------------------------------------------------------------------------

def render_jql(template: str, ctx: dict[str, Any]) -> str:
    """Substitute {project_keys}, {date}, etc. into a JQL template."""
    out = template
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def jql_context(project_keys: list[str], date_str: str, global_jql: str = "") -> dict[str, Any]:
    quoted = ", ".join(f'"{p}"' for p in project_keys)
    ctx = {"project_keys": quoted, "date": date_str}
    return ctx


def apply_global_filter(jql: str, global_jql: str) -> str:
    if not global_jql.strip():
        return jql
    return f"({jql}) AND ({global_jql})"


# ---------------------------------------------------------------------------
# Column extraction
# ---------------------------------------------------------------------------

BUILTIN_COLUMNS = {"key", "summary", "status", "priority", "assignee", "reporter",
                   "created", "updated", "resolved", "days_in_status", "labels",
                   "issuetype"}


def extract_row(issue: dict[str, Any], columns: list[str], client: JiraClient,
                summary_max_chars: int) -> dict[str, Any]:
    fields = issue.get("fields", {})
    row: dict[str, Any] = {}
    for col in columns:
        if col == "key":
            row[col] = issue.get("key")
        elif col == "summary":
            s = fields.get("summary") or ""
            if summary_max_chars and len(s) > summary_max_chars:
                s = s[: summary_max_chars - 1].rstrip() + "…"
            row[col] = s
        elif col == "days_in_status":
            row[col] = days_in_current_status(issue)
        elif col in BUILTIN_COLUMNS:
            row[col] = get_field(issue, col)
        else:
            # Custom field alias or raw customfield_X
            row[col] = get_field(issue, client.resolve_field(col))
    return row


def sort_rows(rows: list[dict[str, Any]], sort_cfg: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not sort_cfg:
        return rows
    key = sort_cfg.get("by")
    direction = (sort_cfg.get("dir") or "asc").lower()
    reverse = direction == "desc"

    def _key(row: dict[str, Any]):
        v = row.get(key)
        # None always sorts last regardless of direction.
        return (v is None, v if v is not None else 0)

    return sorted(rows, key=_key, reverse=reverse)


def empty_section(section_id: str, title: str, message: str | None,
                  jql: str | None = None) -> dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "kind": "empty",
        "data": None,
        "columns": None,
        "note": None,
        "empty_message": message or "No matching issues.",
        "jql": jql,
    }


# ---------------------------------------------------------------------------
# Section handlers
# ---------------------------------------------------------------------------

def handle_kpi(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
               global_jql: str, _opts: dict[str, Any]) -> dict[str, Any]:
    metrics = section.get("metrics", [])
    out: list[tuple[str, int, str]] = []
    for m in metrics:
        jql = apply_global_filter(render_jql(m["jql"], ctx), global_jql)
        out.append((m["label"], client.count(jql), jql))
    return {
        "id": section["id"],
        "title": section["title"],
        "kind": "kpi",
        "data": out,
        "columns": None,
        "note": None,
        "empty_message": None,
        "jql": None,  # kpi has per-metric JQL inside data; no single section-level URL
    }


def _fetch_list(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
                global_jql: str, *, with_changelog: bool
                ) -> tuple[list[dict[str, Any]], int, str]:
    jql = apply_global_filter(render_jql(section["jql"], ctx), global_jql)
    limit = section.get("limit")
    columns = section.get("columns", ["key", "summary", "status"])
    needs_changelog = with_changelog or "days_in_status" in columns
    expand = ["changelog"] if needs_changelog else None
    # Fetch slightly more than the limit so post-filtering (e.g. stuck threshold)
    # has room. We trim before returning.
    fetch_limit = (limit * 3) if limit else None
    issues = client.search(jql, expand=expand, max_results=fetch_limit)
    return issues, len(issues), jql


def handle_list(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
                global_jql: str, opts: dict[str, Any]) -> dict[str, Any]:
    columns = section.get("columns", ["key", "summary", "status"])
    issues, _, jql = _fetch_list(section, client, ctx, global_jql, with_changelog=False)
    rows = [extract_row(i, columns, client, opts["summary_max_chars"]) for i in issues]
    rows = sort_rows(rows, section.get("sort"))
    total = len(rows)
    limit = section.get("limit")
    if limit and total > limit:
        rows = rows[:limit]
        note = f"showing {limit} of {total}"
    else:
        note = None
    if not rows:
        return empty_section(section["id"], section["title"], section.get("empty_message"), jql)
    return {
        "id": section["id"],
        "title": section["title"],
        "kind": "table",
        "data": rows,
        "columns": columns,
        "note": note,
        "empty_message": None,
        "jql": jql,
    }


def handle_recent(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
                  global_jql: str, opts: dict[str, Any]) -> dict[str, Any]:
    # Same as list — the difference is purely intent, expressed via the JQL
    # window the user writes (e.g. created >= -24h).
    return handle_list(section, client, ctx, global_jql, opts)


def handle_status_breakdown(section: dict[str, Any], client: JiraClient,
                            ctx: dict[str, Any], global_jql: str,
                            opts: dict[str, Any]) -> dict[str, Any]:
    jql = apply_global_filter(render_jql(section["jql"], ctx), global_jql)
    issues = client.search(jql, fields=["status"])
    counts = Counter((i.get("fields", {}).get("status") or {}).get("name", "Unknown") for i in issues)

    # Order: start with the configured active list (even at 0), then any
    # statuses found in results but not in the active list.
    active = list(opts.get("active_statuses", []))
    ordered: list[tuple[str, int]] = [(s, counts.get(s, 0)) for s in active]
    for s, c in counts.most_common():
        if s not in active:
            ordered.append((s, c))

    if not ordered:
        return empty_section(section["id"], section["title"], section.get("empty_message"), jql)
    return {
        "id": section["id"],
        "title": section["title"],
        "kind": "breakdown",
        "data": ordered,
        "columns": None,
        "note": f"total: {sum(c for _, c in ordered)}",
        "empty_message": None,
        "jql": jql,
    }


def handle_stuck(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
                 global_jql: str, opts: dict[str, Any]) -> dict[str, Any]:
    threshold = int(section.get("threshold_days", 30))
    columns = section.get("columns", ["key", "summary", "status", "days_in_status", "assignee"])
    if "days_in_status" not in columns:
        columns = list(columns) + ["days_in_status"]
    issues, _, jql = _fetch_list(section, client, ctx, global_jql, with_changelog=True)
    rows = [extract_row(i, columns, client, opts["summary_max_chars"]) for i in issues]
    rows = [r for r in rows if (r.get("days_in_status") or 0) >= threshold]
    rows = sort_rows(rows, section.get("sort") or {"by": "days_in_status", "dir": "desc"})
    total = len(rows)
    limit = section.get("limit")
    if limit and total > limit:
        rows = rows[:limit]
        note = f"showing {limit} of {total} stuck ≥ {threshold}d"
    else:
        note = f"{total} stuck ≥ {threshold}d" if total else None
    if not rows:
        return empty_section(section["id"], section["title"],
                             section.get("empty_message") or f"Nothing stuck for {threshold}+ days.",
                             jql)
    return {
        "id": section["id"],
        "title": section["title"],
        "kind": "table",
        "data": rows,
        "columns": columns,
        "note": note,
        "empty_message": None,
        "jql": jql,
    }


def handle_group_by(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
                    global_jql: str, opts: dict[str, Any]) -> dict[str, Any]:
    group_field = section["group_by"]
    sample_size = int(section.get("sample_size", 3))
    sample_columns = section.get("sample_columns", ["key", "summary"])
    limit = section.get("limit")
    sort_cfg = section.get("sort") or {"by": "count", "dir": "desc"}

    jql = apply_global_filter(render_jql(section["jql"], ctx), global_jql)
    # Need the group field plus sample columns.
    fetch_fields = list({group_field, "summary", "status", *sample_columns})
    issues = client.search(jql, fields=fetch_fields)

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for issue in issues:
        val = get_field(issue, client.resolve_field(group_field))
        bucket_key = str(val) if val is not None else "(none)"
        buckets[bucket_key].append(issue)

    groups = []
    for name, items in buckets.items():
        samples = [extract_row(i, sample_columns, client, opts["summary_max_chars"])
                   for i in items[:sample_size]]
        groups.append({"name": name, "count": len(items), "samples": samples})

    # Sort
    reverse = (sort_cfg.get("dir") or "desc").lower() == "desc"
    sort_key = sort_cfg.get("by", "count")
    groups.sort(key=lambda g: g.get(sort_key, 0), reverse=reverse)

    total_groups = len(groups)
    if limit and total_groups > limit:
        groups = groups[:limit]
        note = f"showing {limit} of {total_groups} groups"
    else:
        note = f"{total_groups} groups" if total_groups else None

    if not groups:
        return empty_section(section["id"], section["title"], section.get("empty_message"), jql)
    return {
        "id": section["id"],
        "title": section["title"],
        "kind": "groups",
        "data": groups,
        "columns": sample_columns,
        "note": note,
        "empty_message": None,
        "jql": jql,
    }


HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "kpi": handle_kpi,
    "list": handle_list,
    "recent": handle_recent,
    "status_breakdown": handle_status_breakdown,
    "stuck": handle_stuck,
    "group_by": handle_group_by,
}


def run_section(section: dict[str, Any], client: JiraClient, ctx: dict[str, Any],
                global_jql: str, opts: dict[str, Any]) -> dict[str, Any]:
    handler = HANDLERS.get(section["type"])
    if not handler:
        raise ValueError(f"Unknown section type: {section['type']!r}. "
                         f"Supported: {sorted(HANDLERS)}")
    return handler(section, client, ctx, global_jql, opts)
