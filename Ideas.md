# Rosewood Hackathon

Status: Planning

## About this project

- https://cerebralvalley.ai/e/rosewood-hospitality-2030/details

Problem Statement:

**1. Hyper-Personalized Arrival Orchestration:** Rosewood’s “A Sense of Place” philosophy means every property is deeply tied to its local culture — but guests often experience a generic luxury arrival. The challenge: build a system that synthesizes guest history, real-time flight data, social signals, and local context to choreograph a truly bespoke arrival before the guest walks in the door. Think: the right room temperature, a locally-sourced welcome amenity, a pre-loaded itinerary based on past preferences - all triggered automatically.

**2. The Invisible Concierge:** Ultra-luxury guests increasingly don’t want to ask for things — they want needs anticipated. The challenge: design an ambient intelligence layer (using in-stay behavior, preferences, and subtle signals) that surfaces the right offer, experience, or assistance proactively — without feeling intrusive or surveillance-like. The hard design problem is the fine line between “they just knew” and “that’s creepy.”

**3. Post-Stay Relationship Continuity / Hyper-Personalized Guest Memory Engine:** For most hotels, the guest relationship effectively ends at checkout. The challenge: build a post-stay engagement system that maintains a genuine, non-spammy connection: remembering anniversaries, anticipating return trips, connecting guests with local Rosewood cultural programming even when they’re not on property.

Juging: 

- Impact Potential (20%) — What is the project’s long-term potential for success? Will this project have a long-lasting impact on the industry, world, or any other areas? How useful and substantial is this project beyond the scope of the hackathon?
- Live Demo (45%) — How well has the team implemented their core idea? Does it work well live? How is it presented?
- Creativity and Originality (35%) — Has this concept been seen before? In what ways does this project differentiate itself, and what innovations does it bring to its respective field? Does it tackle the problem statements in a unique way?

## Project tasks

**Aura** is an omnichannel personal concierge network that completely reinvents the guest journey by allowing travelers to interact seamlessly through their preferred medium—whether via phone call, text, or email.

1. **Phase 1: Pre-Arrival (Email)** * **The Action:** Show a mock automated email ingestion (e.g., parsing a flight confirmation landing at SFO).
    - **The Result:** Claude extracts the arrival time and pushes a service note to the PMS to pre-cool the room and prep a welcome amenity.
2. **Phase 2: In-Stay (Text/SMS)** * **The Action:** The guest texts the concierge line: *"Running late from a meeting on Sand Hill Rd, can I push my massage back?"*
    - **The Result:** Claude intercept the text, checks live spa availability via tool-calling, updates the reservation, and texts back a confirmation.
3. **Phase 3: The Pivot (Live Phone Call)** * **The Action:** The guest decides to call instead for an immediate, high-priority request: *"Actually, can I just get a double espresso sent to my room right now instead?"*
    - **The Result:** Play a live **ElevenLabs** audio stream picking up the conversation *with full context of the previous text and email interactions*: *"Of course, Mr. Ma. I've cancelled the spa adjustment and alerted the Madera team. Your double espresso will be at your door in 5 minutes."*

This perfectly executes on the "Invisible Concierge" problem statement by proving that no matter how the guest reaches out, the hotel behaves as a single, omniscient entity.

Setup text/email based on incoming person

For the actual agents: [https://platform.claude.com/docs/en/managed-agents/overview](https://platform.claude.com/docs/en/managed-agents/overview) 

[Tasks](Rosewood%20Hackathon/Tasks%20362cf52bc81180239d73e9e99541fbd3.csv)