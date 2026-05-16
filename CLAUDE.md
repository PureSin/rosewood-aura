# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Aura** is an omnichannel AI concierge for Rosewood Hotels, built for the Cerebral Valley Rosewood Hospitality 2030 Hackathon. The core concept: a guest can interact via email, SMS, or phone call and the system behaves as a single omniscient entity — full context is preserved across all channels.

## Architecture

The system has three layers:

1. **Claude Managed Agents** (https://platform.claude.com/docs/en/managed-agents/overview) — the AI backbone. Each inbound channel (email, SMS, phone) triggers an agent that shares a common guest context store and a set of mock hotel tools.

2. **Channel Integrations:**
   - Email: inbound webhook (SendGrid Inbound Parse or Postmark) → agent
   - SMS: Twilio webhook → agent → Twilio reply
   - Phone: Twilio number → ElevenLabs Conversational AI, with guest context injected into the system prompt

3. **Demo UI:** a single-page real-time dashboard displaying the guest timeline across all three channels (email event → SMS thread → phone transcript). Uses SSE or polling from the server.

## Mock Hotel Tools

Claude agents call these tools (no real PMS/spa system; all responses are mocked):

- `update_pms_room_prep` — pre-cool room, queue welcome amenity
- `check_spa_availability` — returns available time slots
- `update_spa_reservation` — reschedule or cancel a booking
- `order_room_service` — dispatch a room service order

## Demo Flow

1. **Email** — A flight confirmation email arrives → agent extracts arrival time → calls `update_pms_room_prep`
2. **SMS** — Guest texts to reschedule a massage → agent checks availability → updates booking → replies via SMS
3. **Phone** — Guest calls and asks for a room service item → ElevenLabs voice agent responds with full prior context ("Of course, Mr. Ma...")

## Claude Managed Agent

The agent is created once via `server/setup.py` using `client.beta.agents.create(...)` and a companion environment via `client.beta.environments.create(...)`. Both IDs are written to `.env` on first run.

```bash
cd server && python setup.py   # run once; skip if ANTHROPIC_AGENT_ID already set
```

At runtime, `server/agent_runner.py` opens a session per inbound message, injects the full guest context (channel + interaction history), streams events, handles `agent.custom_tool_use` calls by dispatching to `server/tools.py`, and archives the session on exit.

Key API calls:
- `client.beta.agents.create` — defines the Aris persona, model (`claude-opus-4-7`), and the four hotel tools
- `client.beta.sessions.create` — one session per guest message
- `client.beta.sessions.events.stream` / `.send` — bidirectional event loop for tool results

## Skills

The `skills/` folder contains standalone capabilities that agents can invoke to serve guests. Each skill has a `SKILL.md` spec and a runnable script under `scripts/`. All scripts use `uv run` and fall back to mock data when API keys are absent.

| Skill | Trigger | Script |
|---|---|---|
| `guest-research` | New guest contact, room prep personalization | `uv run skills/guest-research/scripts/research.py --name "…" --email "…"` |
| `book-car` | Guest needs ground transportation | `uv run skills/book-car/scripts/book.py --guest-name "…" --pickup "…" --destination "…" --pickup-time "…"` |
| `send-calendar-invite` | Reservation confirmed; guest wants it on calendar | `uv run skills/send-calendar-invite/scripts/send_invite.py --email "…" --summary "…" --start "…" --end "…"` |

Skills are also importable as Python functions (see each `SKILL.md` for the function signature) and registered as tools in `server/tools.py` so agents can call them directly.

## OpenClaw Memory

OpenClaw stores agent memory at `~/.openclaw/workspace/`. Files from this repo that should be seeded there:

**Copy verbatim into `memory/`:**

| Source | Destination | Purpose |
|---|---|---|
| `assets/Agent_Personality.md` | `memory/agent-personalities.md` | Aris/Thatcher/Soline persona definitions |
| `assets/aris.txt` | `memory/aris-welcome-email.md` | Canonical welcome email template and Aris tone reference |
| `skills/book-car/SKILL.md` | `memory/skill-book-car.md` | Tool spec so OpenClaw knows how to invoke it |
| `skills/guest-research/SKILL.md` | `memory/skill-guest-research.md` | Tool spec for guest profiling |
| `skills/send-calendar-invite/SKILL.md` | `memory/skill-send-calendar-invite.md` | Tool spec for calendar invites |

**Synthesize into `MEMORY.md`** (distill — don't copy raw):
- `CLAUDE.md` — architecture, mock tools, demo flow
- `TASKS.md` — which tasks are complete vs. open (use as current project state)
- `Ideas.md` — judging weights (Live Demo 45%, Creativity 35%, Impact 20%) to guide decisions

## Key Files

- `Ideas.md` — Full problem statement, judging criteria, and original project spec
- `TASKS.md` — Breakdown of build tasks by phase
- `Rosewood-Aura.png` — Project logo for the demo UI
- `skills/CLAUDE.md` — Convention guide for adding new skills
