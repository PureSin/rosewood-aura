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

## Key Files

- `Ideas.md` — Full problem statement, judging criteria, and original project spec
- `TASKS.md` — Breakdown of build tasks by phase
- `Rosewood-Aura.png` — Project logo for the demo UI
