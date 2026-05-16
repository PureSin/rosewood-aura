#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "google-auth",
#   "google-auth-oauthlib",
#   "google-api-python-client",
# ]
# ///
"""
Standalone CLI for the send-calendar-invite skill.

Usage:
  uv run skills/send-calendar-invite/scripts/send_invite.py \
    --email "guest@example.com" \
    --summary "Spa: Deep Tissue Massage – Rosewood Aura" \
    --start "2026-05-20T14:00:00" \
    --end "2026-05-20T15:00:00" \
    --location "Rosewood Spa, 3rd Floor" \
    --description "Your massage is confirmed." \
    --timezone "America/Los_Angeles"

Requires GOOGLE_CALENDAR_TOKEN_FILE env var pointing to a valid OAuth 2.0
token JSON with scope https://www.googleapis.com/auth/calendar.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv
load_dotenv()


def send_calendar_invite(
    guest_email: str,
    summary: str,
    start_time: str,
    end_time: str,
    location: str = None,
    description: str = None,
    timezone: str = "America/Los_Angeles",
) -> dict:
    token_file = os.getenv("GOOGLE_CALENDAR_TOKEN_FILE")
    if not token_file:
        return _mock_invite(guest_email, summary, start_time, end_time)

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(
        token_file,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    service = build("calendar", "v3", credentials=creds)

    event_body = {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": timezone},
        "end": {"dateTime": end_time, "timeZone": timezone},
        "attendees": [{"email": guest_email}],
        "guestsCanModify": False,
        "guestsCanInviteOthers": False,
        "sendUpdates": "all",
    }
    if location:
        event_body["location"] = location
    if description:
        event_body["description"] = description

    event = service.events().insert(
        calendarId="primary",
        body=event_body,
        sendUpdates="all",
    ).execute()

    return {
        "event_id": event.get("id"),
        "html_link": event.get("htmlLink"),
        "summary": event.get("summary"),
        "start": start_time,
        "end": end_time,
        "guest_email": guest_email,
        "status": event.get("status", "confirmed"),
    }


def _mock_invite(guest_email: str, summary: str, start_time: str, end_time: str) -> dict:
    print("[GOOGLE_CALENDAR_TOKEN_FILE not set — returning mock invite]", file=sys.stderr)
    return {
        "event_id": "mock_event_001",
        "html_link": "https://calendar.google.com/calendar/event?eid=mock",
        "summary": summary,
        "start": start_time,
        "end": end_time,
        "guest_email": guest_email,
        "status": "confirmed (mock)",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a Google Calendar invite to a hotel guest."
    )
    parser.add_argument("--email", required=True, help="Guest email address")
    parser.add_argument("--summary", required=True, help="Event title")
    parser.add_argument("--start", required=True, help="Start time (ISO 8601)")
    parser.add_argument("--end", required=True, help="End time (ISO 8601)")
    parser.add_argument("--location", help="Event location")
    parser.add_argument("--description", help="Event description (HTML supported)")
    parser.add_argument("--timezone", default="America/Los_Angeles", help="IANA timezone")
    args = parser.parse_args()

    result = send_calendar_invite(
        guest_email=args.email,
        summary=args.summary,
        start_time=args.start,
        end_time=args.end,
        location=args.location,
        description=args.description,
        timezone=args.timezone,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
