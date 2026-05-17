---
name: guest-agent-session
description: >
  Look up whether a dedicated Claude Managed Agent already exists for a hotel guest and,
  if found, send it a message. Use this at the start of every inbound interaction — before
  create_guest_agent — to avoid spinning up duplicate agents and to ensure the guest's
  prior context is preserved across channels.
compatibility: Requires Python 3.9+, uv, and ANTHROPIC_API_KEY + ANTHROPIC_ENVIRONMENT_ID in the environment (falls back to mock data if absent).
metadata:
  author: rosewood-aura
  version: "1.0"
---

## Overview

This skill wraps two operations into one call:

1. **Find** — lists all Managed Agents via `client.beta.agents.list()` and matches
   against the guest's name using the Aura naming convention (`"Aris — Kelvin Ma"`,
   `"Thatcher — Eleanor Voss"`, etc.).
2. **Message** — if a message is provided and an agent is found, opens a new session
   against that agent, sends the message (with guest context injected), handles any
   tool calls, and returns the reply.

If no agent is found, the skill returns `{"found": false}` — the caller should then
invoke `create_guest_agent` to provision one.

Falls back to rich mock data when `ANTHROPIC_API_KEY` is absent so the demo always runs.

## When to activate

- Any inbound message (email, SMS, phone) arrives for a named guest
- Before calling `create_guest_agent` — check first to avoid duplicates
- When routing a mid-stay request to the guest's personalized agent
- Any time you need the reply from a guest-specific agent rather than the shared default

## Inputs

| Field        | Required | Description                                                              |
|--------------|----------|--------------------------------------------------------------------------|
| `guest_name` | Yes      | Guest's full name — matched against agent names in `"Persona — Name"` format |
| `message`    | No       | Message to send. Omit to perform a lookup-only (returns agent metadata)  |
| `phone`      | No       | Guest phone — used to inject prior interaction history into the session  |
| `channel`    | No       | `"email"`, `"sms"`, or `"phone"`. Defaults to `"sms"`                   |

## Outputs

### Lookup only (no `message`)

```json
{
  "found": true,
  "agent_id": "ag_01AbCdEfGhIjKlMnOpQr",
  "agent_name": "Aris — Kelvin Ma",
  "guest_name": "Kelvin Ma",
  "mock": false
}
```

### With message

```json
{
  "found": true,
  "agent_id": "ag_01AbCdEfGhIjKlMnOpQr",
  "agent_name": "Aris — Kelvin Ma",
  "guest_name": "Kelvin Ma",
  "reply": "Done, Kelvin — your massage has been moved to 4:30 PM. A Jaguar I-PACE...",
  "mock": false
}
```

### Not found

```json
{
  "found": false,
  "guest_name": "Kelvin Ma"
}
```

## How to use

### Run as a script

Lookup only:

```bash
uv run skills/guest-agent-session/scripts/session.py \
  --guest-name "Kelvin Ma"
```

Find and message:

```bash
uv run skills/guest-agent-session/scripts/session.py \
  --guest-name "Kelvin Ma" \
  --message "Can you reschedule my 3pm massage to 4:30pm?" \
  --phone "+14155551234" \
  --channel sms
```

### Call as a Python function (server integration)

```python
from skills.guest_agent_session import guest_agent_session, find_guest_agent
from skills.create_guest_agent import create_guest_agent

# Recommended pattern for every inbound message:
result = guest_agent_session(
    guest_name="Kelvin Ma",
    message="Can you reschedule my 3pm massage to 4:30pm?",
    phone="+14155551234",
    channel="sms",
)

if not result["found"]:
    # No dedicated agent yet — create one (optionally after research)
    agent = create_guest_agent(guest_name="Kelvin Ma", room="412")
    # Then re-run the session against the new agent
    result = guest_agent_session(
        guest_name="Kelvin Ma",
        message="Can you reschedule my 3pm massage to 4:30pm?",
        phone="+14155551234",
    )

reply = result.get("reply", "")
```

The `guest_agent_session` function is registered as the `guest_agent_session` tool in
`server/tools.py`, so Aura can call it directly mid-session.

## Steps

1. Normalize `guest_name` and compile a regex matching `"(Aris|Thatcher|Soline) — {name}"`.
2. Call `client.beta.agents.list()` and scan all agents for a case-insensitive match.
3. If multiple matches exist (e.g., recreated after a profile update), use the last one
   (most recently created per Anthropic pagination order).
4. If `message` is not provided, return the agent metadata and stop.
5. If `message` is provided, pull the guest's interaction history from `context_store`
   (if `phone` is given), build the full message with channel prefix, and open a session
   via `client.beta.sessions.create(agent=..., environment_id=...)`.
6. Stream events, dispatch any `agent.custom_tool_use` calls through `execute_tool`, and
   collect the reply.
7. Archive the session and write the interaction back to `context_store`.

## How to use the result in Aura

- Use `reply` as the outbound message text for the channel (SMS body, email body, TTS input).
- If `found` is `false`, chain directly into `create_guest_agent` before re-sending.
- Log `agent_id` in the PMS so future lookups can skip the list scan (pass it directly to
  `run_guest_session` instead of going through `find_guest_agent`).

## Edge cases

- **No match**: Returns `{"found": false}`. Caller must create the agent first.
- **Multiple matches**: Uses the last in list (newest). Old agents are not deleted — they
  just won't receive new messages.
- **Session error**: The session is always archived in a `finally` block; partial replies
  are returned rather than raising.
- **No `ANTHROPIC_ENVIRONMENT_ID`**: Sessions require an environment. Set this in `.env`
  or run `server/setup.py` once to provision one.
- **API unavailable**: Returns mock data; logs nothing to `context_store`.
