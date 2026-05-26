#!/usr/bin/env python3
"""Local helper: obtain a Gmail refresh token via the OAuth desktop flow.

Run this once on your laptop after creating a Google Cloud OAuth client
(Desktop app type) with the Gmail API enabled. It prints the three values
you then store as GitHub Actions secrets:

  GMAIL_CLIENT_ID
  GMAIL_CLIENT_SECRET
  GMAIL_REFRESH_TOKEN

Requirements:
  pip install google-auth-oauthlib

Scopes requested:
  https://www.googleapis.com/auth/gmail.compose   # create/send drafts
"""
from __future__ import annotations

import getpass
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependency. Run: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def main() -> int:
    print("Paste the OAuth client credentials from Google Cloud Console.")
    print("(APIs & Services → Credentials → your Desktop OAuth client.)\n")
    client_id = input("Client ID:     ").strip()
    client_secret = getpass.getpass("Client secret: ").strip()
    if not client_id or not client_secret:
        print("Both fields required.")
        return 1

    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    print("\nOpening browser to authorize... (sign in with the account that will send the digest)")
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print("\n❌ No refresh token returned. Revoke previous grant at "
              "https://myaccount.google.com/permissions then retry.")
        return 1

    print("\n✅ Success. Add these as GitHub Actions secrets:\n")
    print(f"  GMAIL_CLIENT_ID     = {client_id}")
    print(f"  GMAIL_CLIENT_SECRET = {client_secret}")
    print(f"  GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
