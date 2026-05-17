---
name: create-guest-agent
description: >
  Provision a dedicated Claude Managed Agent for a specific hotel guest, pre-loaded with
  their profile, preferences, room details, and stay dates. Use this skill at check-in
  (or when a guest profile is first established) so every future session starts with full
  personal context — no cold-start, no repeated introductions.
compatibility: Requires Python 3.9+, uv, and ANTHROPIC_API_KEY in the environment (falls back to mock data if absent).
metadata:
  author: rosewood-aura
  version: "1.0"
---

## Overview

This skill calls `client.beta.agents.create(...)` to spin up a Claude Managed Agent
dedicated to a single guest. The agent's system prompt is generated from the guest's
profile (output of the `guest-research` skill), room assignment, and stay dates — so
every channel interaction (email, SMS, phone) opens a session against an agent that
already knows who the guest is and what they care about.

Supports all three Aura personas: **Aris** (Rosewood Sand Hill), **Thatcher** (The Carlyle),
and **Soline** (Hôtel de Crillon). Falls back to rich mock data when `ANTHROPIC_API_KEY`
is absent so the demo always runs.

## When to activate

- A guest checks in or their profile is established for an upcoming stay
- `guest-research` has just returned a profile and you want to bake it into an agent
- Aura needs a channel-agnostic agent context for a multi-day stay
- You want to A/B different persona styles across properties

## Inputs

| Field          | Required | Description                                                         |
|----------------|----------|---------------------------------------------------------------------|
| `guest_name`   | Yes      | Guest's full name                                                   |
| `guest_email`  | No       | Guest's email address                                               |
| `room`         | No       | Assigned room or suite number, e.g. `"412"` or `"Terrace Suite 3"` |
| `check_in`     | No       | Check-in datetime (ISO-8601), e.g. `"2026-05-17T15:00:00-07:00"`   |
| `check_out`    | No       | Check-out datetime (ISO-8601)                                       |
| `profile`      | No       | Guest profile dict from the `guest-research` skill                  |
| `persona`      | No       | `"aris"` (default), `"thatcher"`, or `"soline"`                     |

## Outputs

The script prints a JSON object:

```json
{
  "agent_id": "ag_01AbCdEfGhIjKlMnOpQr",
  "agent_name": "Aris — Kelvin Ma",
  "guest_name": "Kelvin Ma",
  "guest_email": "kelvin.ma23@gmail.com",
  "room": "412",
  "check_in": "2026-05-17T15:00:00-07:00",
  "check_out": "2026-05-20T11:00:00-07:00",
  "persona": "aris",
  "hotel": "Rosewood Sand Hill",
  "created_at": "2026-05-16T20:00:00+00:00",
  "mock": false
}
```

Store `agent_id` in the guest's PMS record so `agent_runner.py` can open sessions
against this agent instead of the shared default.

## How to use

### Run as a script

Basic (no profile):

```bash
uv run skills/create-guest-agent/scripts/create_agent.py \
  --guest-name "Kelvin Ma" \
  --email "kelvin.ma23@gmail.com" \
  --room "412" \
  --check-in "2026-05-17T15:00:00-07:00" \
  --check-out "2026-05-20T11:00:00-07:00"
```

With a pre-built profile (chain with guest-research):

```bash
uv run skills/guest-research/scripts/research.py \
  --name "Kelvin Ma" --email "kelvin.ma23@gmail.com" > /tmp/profile.json

uv run skills/create-guest-agent/scripts/create_agent.py \
  --guest-name "Kelvin Ma" \
  --room "412" \
  --check-in "2026-05-17T15:00:00-07:00" \
  --check-out "2026-05-20T11:00:00-07:00" \
  --profile-file /tmp/profile.json
```

Different persona:

```bash
uv run skills/create-guest-agent/scripts/create_agent.py \
  --guest-name "Eleanor Voss" \
  --room "Penthouse" \
  --persona thatcher
```

### Call as a Python function (server integration)

```python
from skills.create_guest_agent import create_guest_agent
from skills.customer_research import research_guest

profile = research_guest("Kelvin Ma", email="kelvin.ma23@gmail.com")
result = create_guest_agent(
    guest_name="Kelvin Ma",
    guest_email="kelvin.ma23@gmail.com",
    room="412",
    check_in="2026-05-17T15:00:00-07:00",
    check_out="2026-05-20T11:00:00-07:00",
    profile=profile,
    persona="aris",
)
agent_id = result["agent_id"]
# Store agent_id in PMS; pass to agent_runner.run_session()
```

The `create_guest_agent` function is also registered as the `create_guest_agent` tool in
`server/tools.py`, so Aura can call it directly (e.g., after researching a new guest).

## Steps

1. Resolve `persona` to one of `aris | thatcher | soline` (default: `aris`).
2. Build a personalized system prompt embedding: persona identity, guest name, room,
   stay dates, and — if provided — the full profile from `guest-research`.
3. If `ANTHROPIC_API_KEY` is set, call `client.beta.agents.create(name, model, system, tools)`
   with `model="claude-opus-4-7"` and the four hotel tools.
4. Return a result dict with `agent_id`, `agent_name`, guest metadata, and `"mock": false`.
5. If `ANTHROPIC_API_KEY` is absent, return the same shape with a placeholder `agent_id`
   and `"mock": true` so the demo always completes.

## How to use the result in Aura

After calling `create_guest_agent`:

- Store `agent_id` in the guest's PMS profile alongside their phone/email
- In `agent_runner.run_session`, read `agent_id` from the guest record instead of the
  global `ANTHROPIC_AGENT_ID` — that one session now runs against the guest-specific agent
- Each channel (email, SMS, phone) opens a new *session* against the same agent, keeping
  all four hotel tools and the baked-in guest profile

## Edge cases

- **Missing profile**: The agent is still created with minimal context (name, room, dates).
  Call `research_guest` first for the richest personalization.
- **Agent already exists**: This skill always creates a fresh agent. If you need to update
  preferences mid-stay, re-run and update the PMS record with the new `agent_id`.
- **Invalid persona**: Any value outside `aris | thatcher | soline` silently falls back to `aris`.
- **API unavailable**: Returns mock data; log for ops review and retry at next check-in event.
