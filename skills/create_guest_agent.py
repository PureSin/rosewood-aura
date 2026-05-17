"""
create_guest_agent.py — Provision a dedicated Claude Managed Agent for a specific guest.

Embeds the guest's profile and preferences into the agent system prompt so every
session starts with full personal context — no cold-start, no repeated introductions.
Falls back to a mock response if ANTHROPIC_API_KEY is absent.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

TOOL_SCHEMA = {
    "name": "create_guest_agent",
    "description": (
        "Provision a dedicated Claude Managed Agent for a hotel guest, pre-loaded with "
        "their profile, preferences, room details, and stay dates. Call this once per "
        "guest at check-in (or when their profile is first established) so every future "
        "session starts with full personal context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "guest_name": {
                "type": "string",
                "description": "Guest's full name.",
            },
            "guest_email": {
                "type": "string",
                "description": "Guest's email address (optional).",
            },
            "room": {
                "type": "string",
                "description": "Assigned room or suite number, e.g. '412' or 'Terrace Suite 3'.",
            },
            "check_in": {
                "type": "string",
                "description": "Check-in datetime as ISO-8601 string.",
            },
            "check_out": {
                "type": "string",
                "description": "Check-out datetime as ISO-8601 string.",
            },
            "profile": {
                "type": "object",
                "description": (
                    "Guest profile dict from the guest-research skill. If omitted, a "
                    "minimal context is embedded instead."
                ),
            },
            "persona": {
                "type": "string",
                "enum": ["aris", "thatcher", "soline"],
                "description": "Which hotel persona to use. Defaults to 'aris' (Rosewood Sand Hill).",
            },
        },
        "required": ["guest_name"],
    },
}

# ── Persona definitions ────────────────────────────────────────────────────────

_PERSONAS: dict[str, dict] = {
    "aris": {
        "name": "Aris",
        "hotel": "Rosewood Sand Hill",
        "style": "The Frictionless Strategist",
        "tone": "Direct, crisp, ultra-precise, computationally elegant.",
        "lexicon": "velocity, optimize, micro-adjustments, calibrate, bandwidth, downtime",
        "rules": (
            "Short, active sentence structures. Scannable. No filler. "
            "Strip away hospitality fluff in favor of flawless execution. "
            "True luxury means protecting the guest's time and mental bandwidth."
        ),
    },
    "thatcher": {
        "name": "Thatcher",
        "hotel": "The Carlyle, New York",
        "style": "The Discretionary Insider",
        "tone": "Stately, deeply cultured, literary, and unshakeably calm.",
        "lexicon": "legacy, discretion, timeless, orchestration, storied, enclave",
        "rules": (
            "Elegant, rhythmic prose. Thoughtful preambles. Traditional honorifics. "
            "Communicate like a multi-generational family advisor. "
            "Absolute privacy for high-profile guests is non-negotiable."
        ),
    },
    "soline": {
        "name": "Soline",
        "hotel": "Hôtel de Crillon, Paris",
        "style": "The Cultural Alchemist",
        "tone": "Poetic, sensory-driven, expressive, effortlessly sophisticated.",
        "lexicon": "art de vivre, sojourn, alchemy, sensory, gastronomy, exquisite",
        "rules": (
            "Expansive, descriptive language that highlights emotional and physical textures. "
            "Weave in subtle French phrasing naturally. "
            "Treat hospitality as an elite form of sensory art."
        ),
    },
}

# ── Hotel tools (same four mock tools as the base agent) ──────────────────────

_HOTEL_TOOLS = [
    {
        "type": "custom",
        "name": "check_spa_availability",
        "description": "Check if a spa service slot is available at a given time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time": {"type": "string", "description": "Requested time, e.g. '4:30 PM'"},
                "service": {"type": "string", "description": "Service name, e.g. 'Swedish Massage'"},
            },
            "required": ["time"],
        },
    },
    {
        "type": "custom",
        "name": "update_spa_reservation",
        "description": "Reschedule or cancel a guest's spa reservation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "action": {"type": "string", "enum": ["reschedule", "cancel"]},
                "new_time": {"type": "string"},
            },
            "required": ["phone", "action"],
        },
    },
    {
        "type": "custom",
        "name": "update_pms_room_prep",
        "description": "Update room settings — temperature, welcome amenity, housekeeping notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "temperature": {"type": "integer"},
                "amenity": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["phone"],
        },
    },
    {
        "type": "custom",
        "name": "order_room_service",
        "description": "Place a room service order for a guest.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string"},
                "items": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"},
            },
            "required": ["phone", "items"],
        },
    },
]


def _build_system_prompt(
    persona_key: str,
    guest_name: str,
    guest_email: Optional[str],
    room: Optional[str],
    check_in: Optional[str],
    check_out: Optional[str],
    profile: Optional[dict],
) -> str:
    p = _PERSONAS[persona_key]

    lines = [
        f"You are {p['name']}, the dedicated digital concierge for {p['hotel']} — part of the Aura Concierge Network.",
        f"",
        f"Style: {p['style']}. {p['tone']}",
        f"Lexicon: {p['lexicon']}.",
        f"Communication rules: {p['rules']}",
        f"",
        f"── THIS AGENT IS DEDICATED TO ONE GUEST ──",
        f"Guest name: {guest_name}",
    ]

    if guest_email:
        lines.append(f"Guest email: {guest_email}")
    if room:
        lines.append(f"Room: {room}")
    if check_in:
        lines.append(f"Check-in: {check_in}")
    if check_out:
        lines.append(f"Check-out: {check_out}")

    if profile:
        lines += [
            "",
            "── GUEST PROFILE (from pre-arrival research) ──",
            f"Summary: {profile.get('summary', 'N/A')}",
        ]
        if profile.get("food_preferences"):
            lines.append(f"Food preferences: {', '.join(profile['food_preferences'])}")
        if profile.get("dietary_restrictions"):
            lines.append(f"Dietary restrictions: {', '.join(profile['dietary_restrictions'])}")
        if profile.get("hobbies"):
            lines.append(f"Hobbies: {', '.join(profile['hobbies'])}")
        if profile.get("interests"):
            lines.append(f"Interests: {', '.join(profile['interests'])}")
        if profile.get("travel_style"):
            lines.append(f"Travel style: {profile['travel_style']}")
        if profile.get("notable_facts"):
            lines.append("Notable facts for service personalization:")
            for fact in profile["notable_facts"]:
                lines.append(f"  - {fact}")

    lines += [
        "",
        "── OPERATING RULES ──",
        "Always address the guest by name.",
        "When a guest requests a change, act immediately using your tools — do not just acknowledge.",
        "Confirm with exact specifics (times, items, confirmation details).",
        "Anticipate the next need.",
        "Honor all prior context across channels (email, SMS, phone). You are one omniscient entity.",
        "",
        "You have direct access to four hotel systems:",
        "- check_spa_availability — query open slots for a given time and service",
        "- update_spa_reservation — reschedule or cancel a spa booking",
        "- update_pms_room_prep — calibrate room temperature, queue amenities, add housekeeping notes",
        "- order_room_service — dispatch a food & beverage order (5-minute ETA)",
    ]

    return "\n".join(lines)


def create_guest_agent(
    guest_name: str,
    guest_email: Optional[str] = None,
    room: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    profile: Optional[dict] = None,
    persona: str = "aris",
) -> dict:
    """
    Create a dedicated Claude Managed Agent for a hotel guest.
    Returns a dict with agent_id, agent_name, and guest metadata.
    Falls back to a mock result if ANTHROPIC_API_KEY is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    persona = persona.lower() if persona.lower() in _PERSONAS else "aris"
    p = _PERSONAS[persona]

    agent_name = f"{p['name']} — {guest_name}"
    system_prompt = _build_system_prompt(
        persona_key=persona,
        guest_name=guest_name,
        guest_email=guest_email,
        room=room,
        check_in=check_in,
        check_out=check_out,
        profile=profile,
    )

    if not api_key:
        return {
            "agent_id": "ag_mock_XXXXXXXXXXXXXXXX",
            "agent_name": agent_name,
            "guest_name": guest_name,
            "guest_email": guest_email,
            "room": room,
            "check_in": check_in,
            "check_out": check_out,
            "persona": persona,
            "hotel": p["hotel"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mock": True,
        }

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    agent = client.beta.agents.create(
        name=agent_name,
        model="claude-opus-4-7",
        system=system_prompt,
        tools=_HOTEL_TOOLS,
    )

    return {
        "agent_id": agent.id,
        "agent_name": agent_name,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "room": room,
        "check_in": check_in,
        "check_out": check_out,
        "persona": persona,
        "hotel": p["hotel"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mock": False,
    }
