# Aura — Hackathon Task List

## 1. Backend Foundation
> Use Claude Managed Agents (https://platform.claude.com/docs/en/managed-agents/overview) as the agent layer.

- [ ] Spin up lightweight server (Node or Python)
- [ ] Set up shared **context store** (SQLite or in-memory) for guest state across all channels
- [ ] Define mock tools for Claude agents:
  - `update_pms_room_prep` — pre-cool room, queue welcome amenity
  - `check_spa_availability` — returns mock available slots
  - `update_spa_reservation` — reschedule or cancel booking
  - `order_room_service` — dispatch room service order
- [ ] Wire tools into a Claude Managed Agent with a guest-aware system prompt

---

## 2. Phase 1 — Pre-Arrival (Email)

- [ ] Set up inbound email webhook (SendGrid Inbound Parse or Postmark)
- [ ] Claude agent parses email, extracts flight info + arrival time
- [ ] Agent calls `update_pms_room_prep` and logs event to context store
- [ ] **Fallback:** button in UI that POSTs a mock email payload if webhook setup runs long

---

## 3. Phase 2 — In-Stay (SMS via Twilio)

- [ ] Configure Twilio number with webhook pointing to server
- [ ] On incoming SMS, load guest context from store and inject into agent prompt
- [ ] Claude agent calls `check_spa_availability` + `update_spa_reservation`
- [ ] Reply to guest via Twilio SMS API

---

## 4. Phase 3 — Live Phone Call (ElevenLabs)

- [ ] Connect Twilio phone number to ElevenLabs Conversational AI (or TwiML + ElevenLabs TTS)
- [ ] Inject full guest context (email + SMS history) into ElevenLabs system prompt before call
- [ ] Agent handles live conversation and calls `order_room_service`
- [ ] **Fallback:** pre-record ElevenLabs audio clip as backup if live call is unstable

---

## 5. Demo UI

- [ ] Single-page dashboard with real-time guest timeline (SSE or polling)
- [ ] Cards: guest profile, email event, SMS thread, phone transcript
- [ ] Apply Aura branding (logo: `Rosewood-Aura.png`)
- [ ] Keep it static/simple — working UI > broken animations

---

## Notes

- **Judging weights:** Live Demo 45% · Creativity 35% · Impact 20% — nail the demo above all else
- **Demo script:** email → SMS → phone call, each building on the last with full context
- Always have the pre-recorded audio fallback ready for Phase 3
