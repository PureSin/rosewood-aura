---
name: send-calendar-invite
description: >
  Send a Google Calendar invite to a hotel guest for any stay-related event —
  spa appointments, dining reservations, activities, or arrival logistics.
  The guest receives an email invite they can accept or decline.
compatibility: Requires the Google Calendar MCP connection, or GOOGLE_CALENDAR_TOKEN_FILE for the standalone script.
metadata:
  author: rosewood-aura
  version: "1.0"
---

## Overview

Creates a Google Calendar event and sends an email invite to the guest. The agent
uses the Google Calendar MCP tool directly. A standalone CLI script is provided
for server-side use (e.g., triggered automatically after a booking is confirmed).

## When to activate

- A spa or dining reservation is confirmed and the guest should have it on their calendar
- A guest asks "can you send me a calendar invite for that?"
- After `update_spa_reservation` succeeds — follow up with an invite
- Any activity, transfer, or check-in/check-out time worth putting on the guest's calendar

## Inputs

| Field        | Required | Description                                              |
|--------------|----------|----------------------------------------------------------|
| `guest_email`| Yes      | Guest's email address — receives the invite              |
| `summary`    | Yes      | Event title, e.g. "Spa: Deep Tissue Massage – Rosewood"  |
| `start_time` | Yes      | ISO 8601 start, e.g. `2026-05-20T14:00:00`              |
| `end_time`   | Yes      | ISO 8601 end, e.g. `2026-05-20T15:00:00`                |
| `location`   | No       | Free-form text, e.g. "Rosewood Spa, 3rd Floor"           |
| `description`| No       | HTML-supported body with booking details and any notes   |
| `timezone`   | No       | IANA name, e.g. `America/Los_Angeles`. Defaults to hotel local time |

## Agent usage

Call `mcp__claude_ai_Google_Calendar__create_event` with:

```
summary      → event title
startTime    → ISO 8601 start
endTime      → ISO 8601 end
location     → venue / room
description  → booking details (can include HTML)
attendeeEmails → [guest_email]
notificationLevel → "ALL"   ← ensures the guest receives the email invite
timeZone     → hotel's IANA timezone if known
```

Example values:
```
summary: "Spa: Deep Tissue Massage – Rosewood Aura"
startTime: "2026-05-20T14:00:00"
endTime: "2026-05-20T15:00:00"
location: "Rosewood Spa, 3rd Floor"
description: "Your 60-minute deep tissue massage is confirmed.\n\nIf you need to reschedule, reply to this email or text us."
attendeeEmails: ["guest@example.com"]
notificationLevel: "ALL"
timeZone: "America/Los_Angeles"
```

## Standalone script usage

```bash
uv run skills/send-calendar-invite/scripts/send_invite.py \
  --email "katia31sandoval@gmail.com" \
  --summary "Spa: Deep Tissue Massage – Rosewood Aura" \
  --start "2026-05-20T14:00:00" \
  --end "2026-05-20T15:00:00" \
  --location "Rosewood Spa, 3rd Floor" \
  --description "Your massage is confirmed. Reply to reschedule." \
  --timezone "America/Los_Angeles"
```

Requires `GOOGLE_CALENDAR_TOKEN_FILE` in the environment pointing to a valid
OAuth 2.0 token JSON (scope: `https://www.googleapis.com/auth/calendar`).

## Output

Prints a JSON object:

```json
{
  "event_id": "abc123xyz",
  "html_link": "https://calendar.google.com/calendar/event?eid=...",
  "summary": "Spa: Deep Tissue Massage – Rosewood Aura",
  "start": "2026-05-20T14:00:00",
  "end": "2026-05-20T15:00:00",
  "guest_email": "guest@example.com",
  "status": "confirmed"
}
```

## Tone guidance

Keep `summary` concise and branded: `"[Type]: [Service] – Rosewood Aura"`.
In `description`, include:
- Confirmation of what was booked
- How to reschedule (text or email)
- Any relevant prep notes (e.g., "Please arrive 10 minutes early")
