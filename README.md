# jira-digest

> **Replace your morning Jira ritual with one daily summary — wherever you already read things.**
>
> Pipeline health, what's critical, what's stuck, who's overloaded, what came in overnight — delivered to your inbox, Slack channel, or Teams channel before standup. No dashboards to babysit. No saved-filter gymnastics. No servers to run.

### 🌐 <a href="https://darshakbhatt-aiproductlabs.github.io/jira-digest/" target="_blank" rel="noopener noreferrer"><strong>Live demo &amp; landing page →</strong></a>

See a rendered example digest, feature overview, and the 3-step setup walkthrough. *(Opens in a new tab.)*

---

Every PM, EM, and support lead does the same dance each morning: open Jira, click five saved filters, mentally aggregate the numbers, then walk into standup hoping nothing leaked overnight. This tool replaces that dance with one well-formatted message.

One YAML file configures everything. Works with any Atlassian Cloud Jira instance, any project, any custom fields. Runs on GitHub Actions (free tier covers it — ~22 minutes/month of usage). Setup takes ~20 minutes if you let an AI assistant walk you through it.

### What lands in your inbox

```
─── Daily Jira digest — 2026-05-26 ─────────────────────────────────────

KEY METRICS         Open: 127   ·   New (7d): 12   ·   Closed (7d): 18

CRITICAL & HIGH PRIORITY        (showing 5 of 12, sorted by days stuck)
  PROJ-1024  SSO login intermittently fails for…   @alice   High   31d
  PROJ-1018  Billing webhook silently drops…       @bob     High   18d
  PROJ-0982  Onboarding email duplicated when…     @carol   High   12d
  …

STATUS BREAKDOWN    In Progress 42  ·  To Do 18  ·  In Review 11
                    Blocked 0           (zero counts shown — spot stalls)

STUCK — NO MOVEMENT IN 30+ DAYS
  PROJ-0731  Salesforce sync edge case…       In Progress     89d
  PROJ-0844  Webhooks dropped after retry…    To Do           54d

CREATED IN LAST 24 HOURS  (3)
  PROJ-1102  Customer report: cannot export to CSV…    @reporter   High
  …

BY ASSIGNEE         @alice 12 · @bob 8 · @carol 6 · @dan 3 · @eve 2
```

That's an ASCII sketch — real digests are styled HTML email, Slack Block Kit, or Teams adaptive cards. You pick which sections, which channels, and what time of morning.

---

## 👋 For non-tech folks — we've got you

You don't need to read the rest of this README, touch JQL, or know what a cron expression is.

1. **Fork this repo** (button at the top of the GitHub page).
2. **Copy the [interactive handoff prompt](#interactive-handoff-prompt)** (one big block of text further down this page).
3. **Paste it as your first message** into one of these AI assistants, with your forked repo opened:

   | Tool | What it is | Best for |
   |---|---|---|
   | [**Claude Code**](https://claude.com/product/claude-code) | Anthropic's terminal coding agent | Most thorough — handles secrets and API calls end-to-end |
   | [**Codex**](https://chatgpt.com/codex) | OpenAI's coding agent (web or CLI) | Good if you already pay for ChatGPT |
   | [**Cursor**](https://cursor.com) | AI-first code editor | Best if you like a GUI |
   | [**Windsurf**](https://windsurf.com) | Agentic IDE from Codeium | Alternative to Cursor |
   | Any other LLM (Claude.ai, ChatGPT, Gemini, GitHub Copilot Chat in agent mode) | Web/chat assistants | Works but you'll do more copy-pasting |

4. The assistant **interviews you** — "which Jira board?", "what time of morning?", "email or Slack?" — and configures the entire workflow for you. You answer questions in plain English.

**Estimated setup time:**

- 🧑‍🦱 **Non-tech, with an AI assistant:** ~20–30 minutes (mostly waiting for OAuth flows)
- 🧑‍💻 **Tech, reading the docs manually:** ~45–60 minutes

**Value:** Saves you ~30 minutes of board-juggling every workday morning — for as long as you survive in your current role. Side benefits: never being the last to find out what's on fire, sounding suspiciously well-prepared in standups, and a defensible answer when leadership asks "what's our pipeline looking like?" at 8:47am.

---

## What you get

Stop juggling Jira filters. Stop refreshing five saved searches. Every weekday morning, your inbox or Slack channel has the answers already — generated from real Jira data, not a stale snapshot.

A typical digest gives you:

- **🎯 Pipeline health at a glance** — KPI counters: total open, new in the last 7 days, closed in the last 7 days. One look and you know if the queue is growing or shrinking. *(Section type: `kpi`)*
- **🚦 Ticket flow visibility** — How many tickets sit in each active status (Open / In Progress / In Review / Blocked / etc.), including statuses with zero items so stalls jump out. *(Section type: `status_breakdown`)*
- **🔥 Critical attention items** — A sorted list of high/critical priority tickets that are still open, ranked by how long they've sat in their current status. *(Section type: `list`, sorted by `days_in_status`)*
- **🐢 Bottleneck detection** — Everything that hasn't moved in 30+ days (configurable). Uses the Jira changelog for accurate dwell time — no false positives from comment edits. *(Section type: `stuck`)*
- **🆕 What came in overnight** — Issues created in the last 24 hours, so the day starts with awareness, not surprise. *(Section type: `recent`)*
- **👥 Developer bandwidth** — Group by assignee to see who has 12 open tickets and who has 2. Spot overload before it becomes a missed deadline. *(Section type: `group_by` on `assignee`)*
- **🏢 Customer / component slicing** — Group by any custom field — customer account, severity, component, platform, deal tier — to see where load concentrates. *(Section type: `group_by` on a custom field alias)*
- **🎉 Recently resolved** — Optional celebration section showing what closed in the last 7 days. Good for morale and good for visibility. *(Section type: `list` with `resolved >= -7d` JQL)*

Compose any combination of the above into your digest. Most teams run 4–8 sections. Defaults give you the first 5 out of the box.

**Click any section title to drill in.** Every section header in the email, Slack post, and Teams card is a live link to a Jira search showing exactly the issues that section is summarising. No JQL gymnastics — the link is built for you. KPI counters work the same way: clicking the "12 New (7d)" number opens the 12 issues.

**Optional: a hosted browser version.** Slack and Teams have hard message-size limits — if your digest has 200+ stuck tickets, the chat post gets truncated. Enable the optional gist hosting (one config flag + one PAT) and every Slack/Teams message gets a "📄 View full digest in browser" link to a permanent URL with the complete HTML. Each day's digest is a separate gist, so links from older messages still show *that day's* content, not the latest. See [§ Browser-hosted version](#browser-hosted-version-optional).

**Who reads it:** the digest is rendered as a polished HTML email *and* a Slack Block Kit post *and* a Teams adaptive card — pick whichever channels matter for your audience. Same content, different formatting.

**Who builds it:** GitHub Actions runs the script on schedule. No server. Free tier covers it (running 5 days/week × ~1 minute = ~22 minutes/month against your 2,000-minute allowance).

---

## Table of contents

1. [For non-tech folks](#-for-non-tech-folks--weve-got-you)
2. [What you get](#what-you-get)
3. [How it works](#how-it-works)
4. [Quick start](#quick-start)
5. [Detailed setup](#detailed-setup)
6. [Interactive handoff prompt](#interactive-handoff-prompt)
7. [Config schema reference](#config-schema-reference)
8. [Section types](#section-types)
9. [Finding your custom field IDs](#finding-your-custom-field-ids)
10. [Failure notifications](#failure-notifications)
11. [Browser-hosted version (GitHub Gist)](#browser-hosted-version-optional)
12. [Tightening the schedule (cron-job.org)](#tightening-the-schedule)
13. [Troubleshooting](#troubleshooting)
14. [Extending](#extending)

---

## How it works

Every morning, a GitHub Actions workflow runs `scripts/digest.py`, which:

1. Reads your `config/digest.yml`.
2. For each **section** you've defined, runs a JQL query against Jira.
3. Renders the results into a styled HTML email + a Slack Block Kit payload + a Teams adaptive card.
4. Delivers via every channel you've enabled (Gmail draft/send, SMTP, Slack bot or webhook, Teams webhook).
5. If anything blows up and you've configured `on_failure`, pings you so you find out from the script, not from a confused manager.

There's nothing Jira-instance- or company-specific in the code. All of that lives in `config/digest.yml`.

### Section types you can compose

| Type | What it renders |
|---|---|
| `kpi` | Row of counters — each runs a JQL count |
| `list` | Table of issues from a JQL query |
| `recent` | Same as `list`, conventionally with a time-window JQL |
| `status_breakdown` | Count of issues per status (covers active statuses even when 0) |
| `stuck` | Issues with no status change in N+ days (uses changelog) |
| `group_by` | Count + sample issues grouped by any field (incl. custom fields) |

Mix and match — a typical digest has 4–8 sections. See [§ What you get](#what-you-get) above for concrete examples.

---

## Quick start

**If you have access to an LLM (Claude, Codex, ChatGPT, etc.):** skip everything and jump to the [interactive handoff prompt](#interactive-handoff-prompt). Paste it in. The LLM asks you questions, picks sections, and configures the whole thing for you.

**If you'd rather do it by hand:** follow [Detailed setup](#detailed-setup) below.

---

## Detailed setup

### Prerequisites

- A GitHub account (free tier is fine — Actions includes 2,000 minutes/month for private repos).
- An Atlassian Cloud account with permission to view the project(s) you want to digest.
- At least one delivery channel set up (Gmail / Slack / Teams / SMTP).

### Step 1 — Fork this repo

Click **Use this template** (or fork). Keep it private if your JQL or recipient list is sensitive — secrets stay encrypted either way, but config files are visible to anyone with repo access.

```bash
git clone https://github.com/<your-username>/jira-digest.git
cd jira-digest
```

### Step 2 — Get a Jira API token

1. Open <https://id.atlassian.com/manage-profile/security/api-tokens>
2. **Create API token** → label it `jira-digest` → copy the value.
3. Note your Jira base URL (e.g. `https://your-domain.atlassian.net`) and the email of the account.

### Step 3 — Customize `config/digest.yml`

Open the file and edit:

- `jira.project_keys` — your project keys (e.g. `[ENG, OPS]`).
- `statuses.active` — the EXACT status names from your workflow (case-sensitive).
- `fields.aliases` — only if you reference custom fields (see [§ Finding your custom field IDs](#finding-your-custom-field-ids)).
- `sections` — keep the defaults to start, or trim/edit to match what you care about.
- `delivery` — flip `enabled: true` on the channel you want.
- `delivery.email.to` — your recipient email(s).

That's the minimum. Commit the changes:

```bash
git add config/digest.yml
git commit -m "Configure digest for <your project>"
git push
```

### Step 4 — Pick & wire up a delivery channel

#### Option A — Gmail (creates a Gmail draft each morning)

Best for "I want to review before sending." A draft is created, you click **Send** in Gmail.

1. Create a Google Cloud OAuth Desktop client:
   - <https://console.cloud.google.com/> → **APIs & Services → Library → Gmail API → Enable**.
   - **Credentials → Create credentials → OAuth client ID → Desktop app**. Copy the Client ID + Client Secret.
2. Locally (one time):
   ```bash
   pip install google-auth-oauthlib
   python scripts/get_gmail_token.py
   ```
   Paste the Client ID + Secret when prompted. A browser opens — sign in with the account that will send the digest. The script prints three values:
   ```
   GMAIL_CLIENT_ID     = ...
   GMAIL_CLIENT_SECRET = ...
   GMAIL_REFRESH_TOKEN = ...
   ```
3. Add them as GitHub Actions secrets (Step 5).

To auto-send instead of creating a draft, set `delivery.email.gmail_draft_mode: false` in the config.

#### Option B — Generic SMTP

Works with Mailgun, SendGrid, your own server, Office 365 SMTP, etc. Set `delivery.email.via: smtp` and add SMTP secrets (see [§ Step 5](#step-5--add-secrets)).

#### Option C — Slack (bot token, recommended)

1. <https://api.slack.com/apps> → **Create New App → From scratch**.
2. **OAuth & Permissions → Scopes → Bot Token Scopes → Add `chat:write`**.
3. **Install to Workspace** → copy the **Bot User OAuth Token** (`xoxb-...`).
4. In Slack, **invite the bot** to the target channel: `/invite @<your-bot-name>`.
5. Get the channel ID — click the channel name → **About → Channel ID** at the bottom.
6. Set `delivery.slack.enabled: true`, `via: bot`, and `channel_id: C0...` in `config/digest.yml`.
7. Add `SLACK_BOT_TOKEN` as a secret.

#### Option D — Slack (incoming webhook, simpler)

If you don't want to install an app: <https://api.slack.com/messaging/webhooks> → create a webhook for your channel → save the URL as `SLACK_WEBHOOK_URL`. Set `delivery.slack.via: webhook`.

#### Option E — Microsoft Teams

In Teams: **Channel → ⋯ → Connectors → Incoming Webhook → Configure** → copy the URL. Save it as `TEAMS_WEBHOOK_URL` and set `delivery.teams.enabled: true`.

### Step 5 — Add secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | When needed |
|---|---|
| `JIRA_BASE_URL` | Always (e.g. `https://your-domain.atlassian.net`) |
| `JIRA_EMAIL` | Always |
| `JIRA_API_TOKEN` | Always |
| `GMAIL_CLIENT_ID` | If `delivery.email.via=gmail` |
| `GMAIL_CLIENT_SECRET` | ↳ |
| `GMAIL_REFRESH_TOKEN` | ↳ |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | If `delivery.email.via=smtp` |
| `SLACK_BOT_TOKEN` | If `delivery.slack.via=bot` |
| `SLACK_WEBHOOK_URL` | If `delivery.slack.via=webhook` |
| `TEAMS_WEBHOOK_URL` | If `delivery.teams.enabled=true` |
| `GIST_PAT` | If `delivery.gist.enabled=true` — fine-grained PAT with `gist` scope only |
| `HTTPS_PROXY` | Only if your Jira instance IP-allowlists and you need a fixed egress IP (e.g. QuotaGuard) |

### Step 6 — Pick a schedule (your timezone)

Open `.github/workflows/digest.yml`. The line:

```yaml
- cron: '30 2 * * 1-5'    # 02:30 UTC, Mon–Fri
```

uses UTC. Convert your desired local time to UTC and edit accordingly. Examples:

| Local time | Timezone | UTC cron |
|---|---|---|
| 08:00 weekdays | IST (UTC+5:30) | `30 2 * * 1-5` |
| 09:00 weekdays | PT (UTC-7 DST) | `0 16 * * 1-5` |
| 08:30 weekdays | CET (UTC+1) | `30 7 * * 1-5` |

GitHub Actions cron can be **delayed by 1–3 hours** during peak demand. If on-time delivery matters, see [§ Tightening the schedule](#tightening-the-schedule).

### Step 7 — First dry run

Don't trust it blind. Run it once in dry-run mode:

**Actions tab → Jira digest → Run workflow → Set "Render to dry_run_output" = true → Run workflow.**

When it finishes, scroll down on the run page to **Artifacts → digest-dry-run** and download the zip. Open the `.html` in a browser. If sections look right, repeat without dry run; if not, edit the config and rerun.

### Step 8 — Done

Enable Actions if it isn't already (top of the **Actions** tab, "I understand my workflows, go ahead and enable them"). The workflow will fire on schedule.

---

## Interactive handoff prompt

Copy everything inside the fence below and paste it as a new conversation with Claude Code, Codex, ChatGPT, or any LLM that can read your repo and run shell/API calls. The assistant will interview you, gather everything it needs, and finish the setup.

````text
You are setting up the jira-digest tool in this repository for the user. Your job is to interview them, gather configuration, and produce a working digest — end to end.

==============================================================================
STEP 0 — Set the working mode
==============================================================================
Ask the user FIRST, before anything else:

"Setup mode — pick one:
  A) Hands-on — I'll set up tokens/secrets myself; you guide me and edit config files.
  B) Full auto — I'll grant you the credentials; you handle Jira, Git, secrets, and delivery setup end-to-end.

Which one (A or B)?"

If B: warn them that they'll be pasting tokens. Confirm they understand the credentials are shared with this LLM session only and they should rotate them after if concerned. Then continue.

==============================================================================
STEP 1 — Persona & goal
==============================================================================
Ask:
- "What's your role? (PM / EM / Support lead / Exec / Other)"
- "Which board or project do you want to digest? (Paste a Jira board URL or project key.)"
- "Who is this for? Yourself, your team, leadership, or a customer-facing list?"

The persona shapes section recommendations later. Note the answers.

==============================================================================
STEP 2 — Git connection
==============================================================================
Verify git access to the repo:
- Run `git status` and `git remote -v`. If no remote, ask for the repo URL.
- Confirm the user has a Personal Access Token with scopes: `repo`, `workflow`, `actions:write` (the last is needed to add secrets via API in mode B).
- If hands-on, just tell them which scopes they'll need.
- If full auto, ask them to paste the PAT, then verify with: `curl -s -H "Authorization: token <PAT>" https://api.github.com/user`. Confirm the username matches the repo owner.

==============================================================================
STEP 3 — Jira connection
==============================================================================
Check if a Jira MCP server or connector is available in this session (look for tools whose names contain "jira" or "atlassian"). If yes, prefer that for discovery. Otherwise:

Ask for:
- Jira base URL (e.g. https://your-domain.atlassian.net)
- Jira email (Atlassian account)
- Jira API token (get from https://id.atlassian.com/manage-profile/security/api-tokens)

Verify with a curl call: `curl -u "$EMAIL:$TOKEN" "$BASE/rest/api/3/myself"`. If it returns 200, you're connected. If 401/403, walk the user through fixing it.

==============================================================================
STEP 4 — Project, board, and key fields
==============================================================================
Once connected, discover what the user has:
1. Confirm the project key. Run `GET /rest/api/3/project/$KEY` to verify.
2. List issue types in that project: `GET /rest/api/3/project/$KEY/statuses` — show them.
3. Ask which issue types they care about (or "all").
4. List active statuses: from the same response, extract status names — present them grouped by category. Confirm which are "active" (not Done) for the config.
5. Custom fields discovery: `GET /rest/api/3/field`. From the response, identify any custom fields the user references in conversation (e.g. "we have a 'customer account' field"). Build the `fields.aliases` map.

For each custom field they want to use, ask its human-readable alias (e.g. `customer_account`, `severity`, `deal_amount`). Save the alias → customfield_XXXXX mapping.

==============================================================================
STEP 5 — Digest content (section selection)
==============================================================================
Tell the user: "Here are the section types I can compose into your digest. Pick any combination — most teams use 4 to 8."

Present this menu. For each, propose a concrete JQL based on what you learned in step 4. Adapt names to the user's project/fields — do not use any placeholder values from this prompt.

  1) KPI row — open count, new in 7d, closed in 7d (or whatever the user wants)
  2) Open critical / high priority — list, sorted by age in current status
  3) Status breakdown — count per active status
  4) Stuck items — no status change in N days (ask N, default 30)
  5) New since yesterday — list created in last 24h
  6) Group by a field — count + sample issues grouped by customer, assignee, component, severity, etc.
  7) By priority bucket — group_by priority, samples
  8) Awaiting triage — no assignee or no priority set
  9) Recently resolved — closed in last 7 days (celebration section, optional)

For each section the user picks:
  - Confirm the JQL by running it once via the API and reporting the result count.
  - If the count is 0 or wildly off, iterate before saving.
  - Decide which columns to show.
  - Ask for sort + limit.

==============================================================================
STEP 6 — Delivery channels
==============================================================================
Ask: "Which channels should receive the digest?" — Gmail, SMTP, Slack, Teams. Multi-select OK.

For each chosen channel, verify connectivity BEFORE moving on:

GMAIL
  - Check for a Gmail MCP or Google connector. If available, ask user if they want to use that account (good for previewing drafts) or set up the standalone OAuth client below.
  - Standalone path: walk them through the steps in README §Step 4-A. If full-auto mode, the user must still run `scripts/get_gmail_token.py` locally — you can't run a browser-based OAuth flow for them. Make this clear.
  - Test by refreshing the token via the OAuth endpoint and listing drafts to confirm scope.

SMTP
  - Ask for host, port, username, password, sender. Try a `smtplib.SMTP(...).noop()` from a quick Python snippet via the shell to confirm.

SLACK
  - Check for a Slack MCP/connector. If available, use it to verify channel access and the bot is invited.
  - Otherwise: ask for SLACK_BOT_TOKEN. Verify with `curl -H "Authorization: Bearer $TOKEN" https://slack.com/api/auth.test` (expects `ok:true`).
  - Get the channel ID — confirm by sending a test message via `chat.postMessage` saying "jira-digest setup test ✅".

TEAMS / OUTLOOK
  - Teams: ask for TEAMS_WEBHOOK_URL. Test with a tiny MessageCard POST containing "jira-digest setup test ✅".
  - Outlook standalone: if they want Outlook email specifically (not Gmail), point them at SMTP via Office 365 (`smtp.office365.com:587`, OAuth or app password).

==============================================================================
STEP 6B — Browser-hosted version (optional, only if Slack/Teams selected)
==============================================================================
Only ask this if the user picked Slack or Teams as a delivery channel.

Explain: "Slack and Teams cap message size — Slack truncates after ~50 blocks of content (roughly 4–6 sections of detail). If your digest gets big, recipients only see the first chunk. We can fix this by uploading the full HTML to a GitHub gist each morning and linking to it from the Slack/Teams message. Each day = a new gist with its own permanent URL."

CRITICAL — explain the "secret gist" nuance BEFORE they decide:
  - public:true  → listed on the user's GitHub profile, indexed by search.
  - public:false → "secret" gist: NOT listed, NOT searchable, but anyone
                   who holds the URL can read it (no auth wall).
  - "Secret" is NOT "private." The URL is long and random, so it's not
    guessable, but if it's shared or leaks (e.g., a Slack DM gets forwarded),
    anyone with the URL can read the content.

Then ask:
  "Is your digest content OK to be readable by anyone who gets the URL?
   (Bearing in mind the URL only ends up in the Slack/Teams channels you
   pick, and isn't guessable or indexed.)"

If yes → walk them through:
  1. Create a fine-grained PAT at https://github.com/settings/tokens?type=beta
     with ONLY the `gist` scope (no repo permissions needed).
  2. Add it as a GitHub Actions secret named `GIST_PAT`.
  3. In config/digest.yml set:
        delivery:
          gist:
            enabled: true
            public: false          # secret = unlisted, recommended default
            description: "Jira digest — {date}"
  4. On the next run, the digest script uploads to gist and the Slack/Teams
     message includes the "📄 View full digest in browser" link.

If no → recommend SKIP. The per-section JQL deep-links already let recipients
click through to live Jira (which IS authenticated), so the marginal value
of hosted HTML doesn't justify the data-leak risk.

==============================================================================
STEP 7 — Secrets
==============================================================================
List every secret the user needs based on chosen channels. Examples:
  REQUIRED:  JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
  GMAIL:     GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
  SMTP:      SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM
  SLACK:     SLACK_BOT_TOKEN  (or SLACK_WEBHOOK_URL)
  TEAMS:     TEAMS_WEBHOOK_URL
  GIST:      GIST_PAT  (only if STEP 6B was opted in)

Hands-on: print the table and have the user add each via repo Settings → Secrets and variables → Actions.

Full-auto: use the GitHub REST API:
  - Get the repo's public key: GET /repos/{owner}/{repo}/actions/secrets/public-key
  - For each secret, encrypt the value with libsodium sealed-box using that key, then PUT /repos/{owner}/{repo}/actions/secrets/{NAME} with {"encrypted_value":"...","key_id":"..."}.
After adding, GET the list of secrets (names only — values are not returned) and confirm every required one is present.

==============================================================================
STEP 7B — Failure notifications
==============================================================================
Ask: "If the daily run ever crashes (expired Jira token, deleted Slack channel, etc.), where should it ping you?"

Options:
  - none  — workflow run will show as failed in GitHub, but no proactive notification.
  - slack — DM your Slack user ID (e.g. U01ABCDEF12) or a private channel ID. Uses SLACK_BOT_TOKEN.
  - email — a single address. Uses the same email transport (gmail/smtp) as the digest.

Recommend slack DM if they're using Slack delivery already (zero extra setup, and a DM survives even if the team channel is broken). Otherwise, an email to their personal/work address.

Set `on_failure.notify_via` and `on_failure.to` in config/digest.yml. If they pick slack, walk them through finding their member ID: Slack profile → ⋯ → Copy member ID.

Confirm by deliberately breaking one thing (e.g. set JIRA_API_TOKEN to a junk value via a workflow_dispatch with an override, then run) and verifying the alert lands. Restore the token after the test.

==============================================================================
STEP 8 — Schedule (timezone)
==============================================================================
Ask the user's timezone (e.g. "Asia/Kolkata", "America/Los_Angeles") and what time they want the digest in their local morning.

Compute the equivalent UTC cron expression. Edit `.github/workflows/digest.yml` and replace the `cron:` line. Suggest weekdays-only unless they say otherwise.

Tell them:
"GitHub Actions cron can be delayed 1–3 hours under peak load. For tighter delivery, we'll set up cron-job.org later AFTER you've confirmed the digest output is correct (see Step 10)."

==============================================================================
STEP 9 — Dry run
==============================================================================
Run the workflow with dry-run enabled:
  - GitHub UI: Actions → Jira digest → Run workflow → dry_run=true.
  - Or via API: `gh workflow run digest.yml -f dry_run=true` (or REST POST equivalent).

When it finishes, download the `digest-dry-run` artifact, open the HTML in a browser, and ask the user:
"Does this match what you wanted? What's missing, what's noisy?"

Iterate on `config/digest.yml`, push, re-run dry. When the user is happy:

  - Flip `gmail_draft_mode: false` if they want auto-send (optional — drafts are safer initially).
  - Trigger a real (non-dry) workflow_dispatch run to confirm delivery.
  - Have them check their inbox / Slack / Teams.

==============================================================================
STEP 10 — Tightening the schedule (optional)
==============================================================================
After the digest content is verified correct, offer:
"GitHub Actions cron drift can push your morning email to lunch. Want me to set up cron-job.org to trigger this at the exact minute?"

If yes:
  - Have the user create a GitHub fine-grained PAT with `actions:write` on this repo only.
  - Direct them to https://cron-job.org → Create cronjob:
      URL: https://api.github.com/repos/{owner}/{repo}/dispatches
      Method: POST
      Headers:
        Authorization: Bearer <PAT>
        Accept: application/vnd.github.v3+json
        Content-Type: application/json
      Body: {"event_type":"jira-digest"}
      Schedule: their target time, target timezone, weekdays.
  - The workflow's `repository_dispatch` trigger picks it up within seconds.
  - Save a screenshot of the cron-job.org config so they can recreate it.

==============================================================================
STEP 11 — Hand off
==============================================================================
Summarize what you set up:
  - Project keys, sections, delivery channels, schedule (local + UTC), secrets added.
  - Link to the latest successful run.
  - Token expirations to watch (Jira API tokens don't expire by default; Gmail refresh tokens persist as long as scope isn't revoked).
  - Where to edit things later: config/digest.yml for content, .github/workflows/digest.yml for schedule.

Tell the user:
"You're set. Future tweaks: edit config/digest.yml and push — the next scheduled run picks up changes automatically. To add a new section type or delivery channel, the source lives in scripts/."

==============================================================================
GUARDRAILS
==============================================================================
- NEVER hard-code any user-specific value (project key, custom field ID, email, channel ID) in scripts/. All such values belong in config/digest.yml or as secrets.
- NEVER commit secrets, tokens, or API keys to the repo. They go in GitHub Actions secrets only.
- If a JQL returns 0 results unexpectedly, debug it with the user before saving — silent empty sections are worse than no section.
- For destructive actions (rotating tokens, deleting secrets), confirm with the user first.
````

---

## Config schema reference

See `config/digest.yml` — every field has an inline comment. Key top-level keys:

- `jira` — base URL (from env), project keys, optional global JQL filter, request limits.
- `fields.aliases` — alias → `customfield_XXXXX` map. Aliases are usable anywhere in JQL and column lists.
- `statuses.active` / `statuses.done` — list of status names. Used for stuck/aging/breakdown sections.
- `sections` — ordered list. Each item has `id`, `type`, `title`, plus type-specific fields.
- `delivery.{email,slack,teams}` — per-channel config.
- `rendering` — summary truncation, accent color, footer toggle.
- `schedule` — metadata only (the actual cron lives in the workflow file).
- `on_failure` — where to alert you if the run crashes or every delivery channel errors. See [§ Failure notifications](#failure-notifications).

---

## Section types

### `kpi`
```yaml
- id: kpis
  type: kpi
  title: "Key metrics"
  metrics:
    - { label: "Open", jql: 'project IN ({project_keys}) AND statusCategory != Done' }
    - { label: "New (7d)", jql: 'project IN ({project_keys}) AND created >= -7d' }
```

### `list`
```yaml
- id: open_critical
  type: list
  title: "Critical & high priority — open"
  jql: 'project IN ({project_keys}) AND priority IN (Highest, High) AND statusCategory != Done'
  columns: [key, summary, assignee, priority, status, days_in_status]
  sort: { by: days_in_status, dir: desc }
  limit: 25
  empty_message: "No critical items open."
```

Available columns: `key`, `summary`, `status`, `priority`, `assignee`, `reporter`, `created`, `updated`, `resolved`, `days_in_status`, `labels`, `issuetype`, plus any field alias from `fields.aliases`.

### `status_breakdown`
```yaml
- id: status_summary
  type: status_breakdown
  title: "Status breakdown"
  jql: 'project IN ({project_keys}) AND statusCategory != Done'
```

### `stuck`
```yaml
- id: stuck_items
  type: stuck
  title: "Stuck items"
  jql: 'project IN ({project_keys}) AND statusCategory != Done'
  threshold_days: 30
  columns: [key, summary, status, days_in_status, assignee]
```

### `recent`
Like `list`, intent-named for time-window queries.

### `group_by`
```yaml
- id: by_customer
  type: group_by
  title: "By customer"
  jql: 'project IN ({project_keys}) AND statusCategory != Done AND customer_account IS NOT EMPTY'
  group_by: customer_account
  show: [count, sample]
  sample_size: 3
  limit: 10
```

---

## Finding your custom field IDs

```bash
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
     "$JIRA_BASE_URL/rest/api/3/field" \
  | python -c 'import sys, json; [print(f["{:<24}".format(f["id"]), f.get("name")) for f in json.load(sys.stdin) if f["custom"]]'
```

Pick the IDs you care about, give them readable aliases, and put them in `fields.aliases` in the config. From then on you can write `customer_account` in JQL and column lists — the script swaps in the real ID.

---

## Failure notifications

When the daily run dies — Jira creds expire, Slack channel deleted, SMTP server unreachable, custom field renamed — you want to hear about it from the script, not from a teammate at 11am asking where the digest is.

In `config/digest.yml`:

```yaml
on_failure:
  notify_via: slack       # none | slack | email
  to: "U01ABCDEF12"       # Slack member ID (DM) or channel ID, or email address
```

**Behavior:**

- Fires when the script crashes (config invalid, Jira preflight fails, code bug) **or** when every enabled delivery channel errors (so you're not silently dropping the digest).
- For `slack`: posts to the channel/DM in `to` using `SLACK_BOT_TOKEN` (or webhook, whichever your `delivery.slack.via` is set to). This is independent of the digest's normal Slack channel — point it at your DM so you're notified even if the team channel is misconfigured.
- For `email`: sends to the address in `to` via your configured email transport (`delivery.email.via` — gmail or smtp). For Gmail, the failure email is **always sent immediately** (it overrides `gmail_draft_mode`) — drafts in Gmail at 9am are not useful when something's broken.
- Includes the error message, a short traceback snippet, and a link to the failed GitHub Actions run.
- Notification itself is best-effort — if the failure-notification path *also* fails (e.g. Slack is what's broken), the original error is still logged to the workflow output. You won't get into a doom loop.

**How to find your Slack DM ID:** in Slack, click your profile → ⋯ → Copy member ID. It starts with `U`.

---

## Browser-hosted version (optional)

Slack and Teams messages are capped — Slack truncates after ~50 blocks (≈ 4–6 sections of meaningful content). If your digest has 200 stuck tickets across 8 sections, recipients see "…truncated" and have to switch to email.

Enable **gist-based hosting** and every Slack/Teams message gets a "📄 View full digest in browser" link at the top, pointing to a permanent URL with the complete HTML.

### How it works

Each run, the script uploads the rendered HTML as a [GitHub gist](https://gist.github.com), then wraps the raw URL through [htmlpreview.github.io](https://htmlpreview.github.io) so browsers render it correctly. The preview URL goes into the Slack/Teams payload.

**Why gists, not GitHub Pages:**

- No repo settings to change — one PAT with the `gist` scope is all the setup.
- **Each day's digest is its own gist with its own URL.** A Slack message from last Monday still links to last Monday's digest, not today's. Pages would have overwritten it.
- Works for public and private repos identically — gist visibility is independent of repo visibility.

### ⚠ Privacy — what "secret" gist actually means

GitHub has two gist visibilities:

| Setting | On your profile? | Searchable? | Anyone with URL can read? |
|---|---|---|---|
| `public: true` | ✅ Listed | ✅ Indexed | ✅ Yes |
| `public: false` ("secret") | ❌ Not listed | ❌ Not indexed | ✅ Yes |

**A "secret" gist is unlisted, not private.** The URL is long and random; nobody can stumble onto it. But if it's shared (or leaks), anyone holding it can read the content — there's no GitHub login wall.

For Slack/Teams sharing this is exactly the model you want: the URL goes into a specific channel, only members of that channel see it, and there's no auth dance for them when they click. But don't enable this if your digest contains content that would be a problem if a Slack DM containing the link got forwarded.

Default in `config/digest.yml` is `public: false`. Leave it that way unless you have a specific reason to publish.

### Enabling it

1. **Create a fine-grained PAT** at <https://github.com/settings/tokens?type=beta> with **only** the `gist` scope. No repo access needed.
2. Add it as a GitHub Actions secret named `GIST_PAT`.
3. Edit `config/digest.yml`:
   ```yaml
   delivery:
     gist:
       enabled: true
       public: false                          # secret (unlisted)
       description: "Jira digest — {date}"
   ```
4. Commit + push. Next run uploads to gist; the URL appears in the run logs and in every Slack/Teams message.

### Cleanup

Each run creates a new gist, so over time they accumulate (~260/year on weekday runs). They're small (HTML only, no images), so disk usage is negligible. To prune: <https://gist.github.com/> → batch-delete older entries. There's no auto-delete in this tool — old URLs staying live is usually the point.

### Disabling

Flip `enabled: false` in config and push. No new gists get created; existing ones stay live until you delete them.

---

## Tightening the schedule

GitHub Actions `schedule:` triggers can run **1–3 hours late** during peak demand. For reliable morning delivery, add a [cron-job.org](https://cron-job.org) task that POSTs to your repo's `dispatches` endpoint — `repository_dispatch` triggers fire within seconds.

1. Create a GitHub fine-grained PAT with `actions:write` scoped to this repo only.
2. cron-job.org → **Create cronjob**:
   - **URL:** `https://api.github.com/repos/<owner>/<repo>/dispatches`
   - **Method:** POST
   - **Headers:**
     ```
     Authorization: Bearer <YOUR_PAT>
     Accept: application/vnd.github.v3+json
     Content-Type: application/json
     ```
   - **Body:** `{"event_type":"jira-digest"}`
   - **Schedule:** your target time in your local timezone, weekdays.
3. Save. The workflow runs within seconds of the cron firing.

Keep the GitHub-side `schedule:` cron in place as a fallback — if cron-job.org is ever down, you still get a (slightly late) digest.

---

## Troubleshooting

**Jira 401 / 403** — API token wrong, email mismatched, or your Jira admin has IP-allowlisted the project. For the latter, either whitelist GitHub's Actions IP ranges (`https://api.github.com/meta` → `actions`) or use a fixed-IP HTTPS proxy via the `HTTPS_PROXY` secret.

**Gmail "invalid_grant"** — your refresh token was revoked (someone visited <https://myaccount.google.com/permissions> and removed access, or the OAuth client was deleted). Re-run `scripts/get_gmail_token.py`.

**Slack `not_in_channel`** — the bot hasn't been invited to the target channel. In Slack: `/invite @<bot-name>`.

**Empty sections** — your JQL returned no issues. Run the same query in Jira's issue search UI to debug; common causes are wrong status names (case-sensitive), wrong project key, or a custom-field alias that hasn't been mapped.

**`status` column shows blank** — your search call didn't request the `status` field. The script does this automatically for known builtins. If you're using a custom field, add an alias.

**Workflow not running on schedule** — GitHub Actions cron can be delayed. See [§ Tightening the schedule](#tightening-the-schedule).

**Dry-run output missing** — make sure you triggered with `dry_run=true` from the workflow_dispatch UI; artifacts are only uploaded in that mode.

---

## Extending

The repo ships with six section types — `kpi`, `list`, `recent`, `status_breakdown`, `stuck`, `group_by`. For anything richer (composite scoring, deal-value columns, multi-axis matrices) just **paste one of these short prompts into Claude Code / Codex / Cursor in your fork** and the assistant extends the renderer for you.

### Sample prompts to extend the renderer

**🎯 Composite "worth engaging today" scoring:**
> Add a new section type called `weighted_score` that ranks tickets by criticality × customer value × roadmap fit. Show top 10 sorted by score with a 'why this one' explainer column.

**💰 Deal-value column in group_by:**
> In my group_by section, add a 'deal_amount' custom-field column right-aligned with money formatting (e.g. $60k). Sort groups by total deal value descending.

**🌟 Customer pressure index (bucketed stat cards):**
> Add a section type called `buckets` that classifies customers into High pressure / Watch / Healthy / New voices and renders as 4 colored stat cards.

**🧩 Component health matrix:**
> Add a section type called `matrix` that cross-tabs components (rows) against statuses (columns), with cell counts and a 'signal' dot (green/amber/red) based on roadmap-alignment percentage.

**💬 Reporter mix breakdown:**
> Add a KPI section with 4 metrics: tickets filed by internal users (CSM/PM), external customers, first-time reporters in the last 30 days, and % repeat reporters.

### Extending the architecture

- **New section type:** add a handler in `scripts/sections.py`, register it in the `HANDLERS` dict, and add a rendering branch in `scripts/render_html.py` and `scripts/render_slack.py`.
- **New delivery channel:** drop a module in `scripts/delivery/` exposing a `send(...)` function, register it in `scripts/delivery/__init__.py`.
- **Multiple digests:** copy `.github/workflows/digest.yml` to a second file with a different schedule and a different `DIGEST_CONFIG` env var. Each can read its own YAML.

---

## License

This is a template repo. Use it however you like — free to fork, modify, and ship to your own team.

---

## Connect

Built by **Darshak Bhatt** — [LinkedIn](https://www.linkedin.com/in/darshak-bhatt/) · [GitHub](https://github.com/darshakbhatt-aiproductlabs)

If this saves your morning, a connect on LinkedIn is appreciated. If it breaks, open an issue on the repo.
