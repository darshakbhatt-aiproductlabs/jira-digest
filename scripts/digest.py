#!/usr/bin/env python3
"""jira-digest entry point.

Reads a YAML config, fetches Jira issues per section, renders to HTML +
Slack Block Kit, and delivers via every enabled channel.

Usage:
    python scripts/digest.py [config/digest.yml]

Env vars consumed (see .env.example):
    JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN          (required)
    DRY_RUN                                            (optional)
    GMAIL_*, SMTP_*, SLACK_*, TEAMS_WEBHOOK_URL        (per enabled channel)
"""
from __future__ import annotations

import html as html_mod
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Local imports — scripts/ is added to sys.path below so this works whether
# invoked as `python scripts/digest.py` or as a module.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import yaml  # noqa: E402

from jira import make_client_from_env  # noqa: E402
from sections import jql_context, run_section  # noqa: E402
from render_html import render_email  # noqa: E402
from render_slack import render_slack  # noqa: E402
from delivery import CHANNELS  # noqa: E402


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config root must be a mapping, got {type(cfg).__name__}")
    return cfg


def resolve_jira_base(cfg: dict[str, Any]) -> str:
    jira = cfg.get("jira", {})
    env_key = jira.get("base_url_env", "JIRA_BASE_URL")
    base = os.environ.get(env_key) or jira.get("base_url")
    if not base:
        raise RuntimeError(f"JIRA base URL not set (looked in env {env_key} and jira.base_url)")
    os.environ["JIRA_BASE_URL"] = base.rstrip("/")
    return base.rstrip("/")


# ---------------------------------------------------------------------------
# Section rendering pipeline
# ---------------------------------------------------------------------------

def gather_sections(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    jira_cfg = cfg.get("jira", {})
    project_keys = jira_cfg.get("project_keys") or []
    if not project_keys:
        raise RuntimeError("config.jira.project_keys must contain at least one project key")
    global_jql = jira_cfg.get("global_jql", "")

    field_aliases = (cfg.get("fields", {}) or {}).get("aliases") or {}
    client = make_client_from_env(
        field_aliases=field_aliases,
        page_size=int(jira_cfg.get("page_size", 100)),
        timeout=int(jira_cfg.get("request_timeout", 30)),
    )

    # Preflight Jira reachability.
    try:
        me = client.preflight()
        print(f"[jira] connected as {me.get('emailAddress') or me.get('displayName')}",
              flush=True)
    except Exception as e:
        raise RuntimeError(f"Jira preflight failed: {e}") from e

    statuses = cfg.get("statuses", {}) or {}
    rendering = cfg.get("rendering", {}) or {}
    opts = {
        "active_statuses": statuses.get("active") or [],
        "done_statuses": statuses.get("done") or [],
        "summary_max_chars": int(rendering.get("summary_max_chars", 80)),
    }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ctx = jql_context(project_keys, today)

    rendered: list[dict[str, Any]] = []
    for section in cfg.get("sections", []):
        sid = section.get("id") or section.get("type")
        try:
            print(f"[section] {sid} ({section['type']}) ...", flush=True)
            r = run_section(section, client, ctx, global_jql, opts)
            rendered.append(r)
        except Exception as e:
            print(f"[section] {sid} FAILED: {e}", flush=True)
            traceback.print_exc()
            rendered.append({
                "id": sid, "title": section.get("title", sid),
                "kind": "empty", "data": None, "columns": None, "note": None,
                "empty_message": f"⚠ Section failed: {e}",
            })
    return rendered


def render_subject(template: str, date_str: str) -> str:
    return template.replace("{date}", date_str)


# ---------------------------------------------------------------------------
# Browser-hosted full-HTML copy (GitHub Gist + htmlpreview.github.io)
# ---------------------------------------------------------------------------
# See scripts/delivery/gist.py for the upload mechanics and the rationale
# for using gists instead of GitHub Pages.


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

def deliver(rendered: list[dict[str, Any]], cfg: dict[str, Any], jira_base: str) -> dict[str, Any]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rendering = cfg.get("rendering", {}) or {}
    accent = rendering.get("accent_color", "#0052CC")
    show_footer = bool(rendering.get("show_footer", True))
    footer = f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC" if show_footer else None

    delivery_cfg = cfg.get("delivery", {}) or {}
    results: dict[str, Any] = {}

    # Browser-hosted full HTML (gist) --------------------------------------
    # Upload first so the URL is available for embedding in Slack/Teams below.
    # The hosted copy intentionally does NOT include a "view in browser"
    # link to itself.
    web_url: str | None = None
    gist_cfg = delivery_cfg.get("gist") or {}
    if gist_cfg.get("enabled"):
        from delivery import gist as gist_module
        web_subject = render_subject(
            gist_cfg.get("description")
            or (delivery_cfg.get("email") or {}).get("subject")
            or (delivery_cfg.get("slack") or {}).get("title")
            or "Jira digest — {date}",
            today,
        )
        web_html = render_email(rendered, subject=web_subject, jira_base=jira_base,
                                accent=accent, footer=footer, web_url=None)
        web_url = gist_module.upload(web_html, today=today, config=gist_cfg)
        if web_url:
            results["web"] = {"mode": "gist", "url": web_url}

    # Email -----------------------------------------------------------------
    email_cfg = delivery_cfg.get("email") or {}
    if email_cfg.get("enabled"):
        subject = render_subject(email_cfg.get("subject", "Jira digest — {date}"), today)
        html = render_email(rendered, subject=subject, jira_base=jira_base,
                            accent=accent, footer=footer, web_url=web_url)
        if os.environ.get("DRY_RUN") in ("1", "true", "True"):
            out_dir = Path("dry_run_output")
            out_dir.mkdir(exist_ok=True)
            out_path = out_dir / f"digest-{today}.html"
            out_path.write_text(html, encoding="utf-8")
            results["email"] = {"mode": "dry_run", "path": str(out_path),
                                "to": email_cfg.get("to") or []}
            print(f"[delivery] dry-run: wrote {out_path}", flush=True)
        else:
            via = (email_cfg.get("via") or "gmail").lower()
            channel = CHANNELS.get(via)
            if not channel:
                raise RuntimeError(f"Unknown email via: {via!r}")
            try:
                results["email"] = channel(html=html, subject=subject, config=email_cfg)
                print(f"[delivery] email via {via}: {results['email']}", flush=True)
            except Exception as e:
                results["email"] = {"error": str(e)}
                print(f"[delivery] email FAILED: {e}", flush=True)

    # Slack -----------------------------------------------------------------
    slack_cfg = delivery_cfg.get("slack") or {}
    if slack_cfg.get("enabled"):
        title = render_subject(slack_cfg.get("title", "Jira digest — {date}"), today)
        payload = render_slack(rendered, title=title, jira_base=jira_base,
                               footer=footer, web_url=web_url)
        if os.environ.get("DRY_RUN") in ("1", "true", "True"):
            out_dir = Path("dry_run_output")
            out_dir.mkdir(exist_ok=True)
            out_path = out_dir / f"slack-{today}.json"
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            results["slack"] = {"mode": "dry_run", "path": str(out_path)}
            print(f"[delivery] dry-run: wrote {out_path}", flush=True)
        else:
            try:
                results["slack"] = CHANNELS["slack"](slack_payload=payload, config=slack_cfg)
                print(f"[delivery] slack: {results['slack']}", flush=True)
            except Exception as e:
                results["slack"] = {"error": str(e)}
                print(f"[delivery] slack FAILED: {e}", flush=True)

    # Teams -----------------------------------------------------------------
    teams_cfg = delivery_cfg.get("teams") or {}
    if teams_cfg.get("enabled"):
        title = render_subject(teams_cfg.get("title", "Jira digest — {date}"), today)
        if os.environ.get("DRY_RUN") in ("1", "true", "True"):
            results["teams"] = {"mode": "dry_run"}
            print("[delivery] dry-run: skipping Teams send", flush=True)
        else:
            try:
                results["teams"] = CHANNELS["teams"](sections=rendered, title=title,
                                                     jira_base=jira_base, config=teams_cfg,
                                                     accent=accent, web_url=web_url)
                print(f"[delivery] teams: {results['teams']}", flush=True)
            except Exception as e:
                results["teams"] = {"error": str(e)}
                print(f"[delivery] teams FAILED: {e}", flush=True)

    return results


# ---------------------------------------------------------------------------
# Failure notification (on_failure block in config)
# ---------------------------------------------------------------------------

def notify_failure(cfg: dict[str, Any], error: BaseException, tb_text: str) -> None:
    """Best-effort alert when the run fails. Never re-raises.

    Honours config.on_failure:
        notify_via: none | slack | email
        to:        slack channel ID (for slack) or email address (for email)

    Slack uses delivery.slack settings for transport (SLACK_BOT_TOKEN, via);
    email uses delivery.email settings (gmail/smtp). This lets the failure
    alert reach a *different* destination (e.g. your DM) than the digest
    itself (a team channel).
    """
    try:
        on_fail = (cfg.get("on_failure") or {})
        notify_via = (on_fail.get("notify_via") or "none").lower()
        to = (on_fail.get("to") or "").strip()
        if notify_via in ("none", "") or not to:
            return

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        title = f"⚠ jira-digest run failed — {ts}"
        summary = f"{type(error).__name__}: {error}"
        tb_snippet = (tb_text or "").strip()[:2800]
        run_url = ""
        if os.environ.get("GITHUB_SERVER_URL") and os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID"):
            run_url = (
                f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
                f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"
            )

        if notify_via == "slack":
            from delivery.slack import send as slack_send  # local import keeps cold path cheap
            blocks: list[dict[str, Any]] = [
                {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
                {"type": "section", "text": {"type": "mrkdwn",
                                              "text": f"*Error:* `{summary}`"}},
            ]
            if tb_snippet:
                blocks.append({"type": "section", "text": {"type": "mrkdwn",
                                                            "text": f"```\n{tb_snippet}\n```"}})
            if run_url:
                blocks.append({"type": "context", "elements": [
                    {"type": "mrkdwn", "text": f"<{run_url}|Open workflow run>"}
                ]})
            payload = {"text": title, "blocks": blocks,
                       "unfurl_links": False, "unfurl_media": False}
            slack_cfg = (cfg.get("delivery") or {}).get("slack") or {}
            transport = (slack_cfg.get("via") or "bot").lower()
            slack_send(slack_payload=payload, config={"via": transport, "channel_id": to})
            print(f"[on_failure] slack notification sent to {to}", flush=True)
            return

        if notify_via == "email":
            from delivery import CHANNELS
            email_cfg = dict((cfg.get("delivery") or {}).get("email") or {})
            via = (email_cfg.get("via") or "gmail").lower()
            channel = CHANNELS.get(via)
            if not channel:
                print(f"[on_failure] unknown email transport: {via}", flush=True)
                return
            # Override recipient + force-send (don't sit as a draft).
            email_cfg["to"] = [to]
            email_cfg["cc"] = []
            email_cfg["gmail_draft_mode"] = False
            run_link = f'<p><a href="{html_mod.escape(run_url)}">Open workflow run</a></p>' if run_url else ""
            body = (
                f"<h2 style='font-family:sans-serif'>{html_mod.escape(title)}</h2>"
                f"<p><b>Error:</b> <code>{html_mod.escape(summary)}</code></p>"
                f"{run_link}"
                f"<pre style='background:#f4f5f7;padding:12px;border-radius:4px;"
                f"font-size:12px;overflow:auto'>{html_mod.escape(tb_snippet)}</pre>"
            )
            channel(html=body, subject=title, config=email_cfg)
            print(f"[on_failure] email notification sent to {to}", flush=True)
            return

        print(f"[on_failure] unknown notify_via: {notify_via}", flush=True)
    except Exception as inner:
        # The notification path itself failed. Log and move on — we don't
        # want to mask the original error.
        print(f"[on_failure] notification dispatch failed: {inner}", flush=True)


# ---------------------------------------------------------------------------
# GitHub Actions step summary
# ---------------------------------------------------------------------------

def write_step_summary(rendered: list[dict[str, Any]], results: dict[str, Any]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = ["# Jira digest run", ""]
    lines.append(f"**Sections rendered:** {len(rendered)}")
    for s in rendered:
        kind = s["kind"]
        note = f" — {s['note']}" if s.get("note") else ""
        lines.append(f"- `{s['id']}` ({kind}){note}")
    lines.append("")
    lines.append("**Delivery:**")
    for ch, info in results.items():
        ok = "❌" if isinstance(info, dict) and "error" in info else "✅"
        lines.append(f"- {ok} **{ch}**: `{info}`")
    Path(summary_path).write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    cfg_for_failure: dict[str, Any] = {}
    try:
        config_path = argv[1] if len(argv) > 1 else os.environ.get("DIGEST_CONFIG", "config/digest.yml")
        if not Path(config_path).is_file():
            print(f"❌ Config file not found: {config_path}", flush=True)
            return 2

        cfg = load_config(config_path)
        cfg_for_failure = cfg
        jira_base = resolve_jira_base(cfg)
        print(f"[config] {config_path}  jira={jira_base}", flush=True)

        rendered = gather_sections(cfg)
        results = deliver(rendered, cfg, jira_base)
        write_step_summary(rendered, results)

        # Determine pass/fail. Treat "every enabled channel errored" as a hard failure
        # so on_failure fires even if the script technically finished.
        enabled_channels = [c for c in ("email", "slack", "teams")
                            if ((cfg.get("delivery") or {}).get(c) or {}).get("enabled")]
        per_channel_failed = [c for c in enabled_channels
                              if isinstance(results.get(c), dict) and "error" in results.get(c, {})]
        all_failed = bool(enabled_channels) and len(per_channel_failed) == len(enabled_channels)

        if all_failed:
            err = RuntimeError(
                "All enabled delivery channels failed: "
                + "; ".join(f"{c}: {results[c].get('error')}" for c in per_channel_failed)
            )
            print(f"❌ {err}", flush=True)
            notify_failure(cfg_for_failure, err, "")
            return 1

        return 0 if not per_channel_failed else 1

    except SystemExit:
        raise
    except BaseException as e:
        tb = traceback.format_exc()
        print(f"❌ jira-digest run failed: {e}\n{tb}", flush=True)
        notify_failure(cfg_for_failure, e, tb)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
