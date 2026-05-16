"""
Run once to create the Managed Agent + Environment.
Saves ANTHROPIC_AGENT_ID and ANTHROPIC_ENVIRONMENT_ID to .env.

Usage:
  cd server && python setup.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """\
You are Aris, the dedicated digital concierge for Rosewood Sand Hill — part of the Aura Concierge Network.

Style: The Frictionless Strategist. Direct, crisp, ultra-precise, computationally elegant. You strip away hospitality fluff in favor of flawless execution and cognitive ease. For this demographic — elite tech and venture capital — true luxury means protecting their time and maximizing their mental bandwidth.

Lexicon: velocity, optimize, micro-adjustments, calibrate, bandwidth, downtime, frictionless, choreograph.

Communication rules:
- Short, active sentence structures. Scannable. No filler.
- Always address the guest by name.
- When a guest requests a change, act immediately using your tools — do not just acknowledge. Confirm with exact specifics (times, items, confirmation details).
- Anticipate the next need. If rescheduling a massage, offer the next available slot unprompted.
- Honor all prior context across channels (email, SMS, phone). You are one omniscient entity, not separate systems.

Guest context will be injected at the start of each message: room number, active reservations, and full interaction history across all channels.

You have direct access to four hotel systems:
- check_spa_availability — query open slots for a given time and service
- update_spa_reservation — reschedule or cancel a spa booking
- update_pms_room_prep — calibrate room temperature, queue amenities, add housekeeping notes
- order_room_service — dispatch a food & beverage order (5-minute ETA)
"""

TOOLS = [
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
                "phone": {"type": "string", "description": "Guest phone number"},
                "action": {"type": "string", "enum": ["reschedule", "cancel"]},
                "new_time": {"type": "string", "description": "New time if rescheduling, e.g. '4:30 PM'"},
            },
            "required": ["phone", "action"],
        },
    },
    {
        "type": "custom",
        "name": "update_pms_room_prep",
        "description": "Update room settings in the Property Management System.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Guest phone number"},
                "temperature": {"type": "integer", "description": "Target room temperature in °F"},
                "amenity": {"type": "string", "description": "Welcome amenity to prepare"},
                "notes": {"type": "string", "description": "Additional notes for housekeeping"},
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
                "phone": {"type": "string", "description": "Guest phone number"},
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Items to order, e.g. ['double espresso']",
                },
                "note": {"type": "string", "description": "Special instructions"},
            },
            "required": ["phone", "items"],
        },
    },
]


def main():
    existing_agent = os.environ.get("ANTHROPIC_AGENT_ID")
    existing_env = os.environ.get("ANTHROPIC_ENVIRONMENT_ID")

    if existing_agent and existing_env:
        print(f"Agent already configured: {existing_agent}")
        print(f"Environment already configured: {existing_env}")
        print("Delete these from .env to recreate.")
        sys.exit(0)

    print("Creating environment...")
    environment = client.beta.environments.create(
        name="aura-concierge",
        config={"type": "cloud", "networking": {"type": "unrestricted"}},
    )
    print(f"  Environment ID: {environment.id}")

    print("Creating agent...")
    agent = client.beta.agents.create(
        name="Aris — Aura Concierge Network",
        model="claude-opus-4-7",
        system=SYSTEM_PROMPT,
        tools=TOOLS,
    )
    print(f"  Agent ID: {agent.id}  version: {agent.version}")

    env_path = ROOT / ".env"
    lines = env_path.read_text().splitlines()

    def set_var(lines: list[str], key: str, value: str) -> list[str]:
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                return lines
        lines.append(f"{key}={value}")
        return lines

    lines = set_var(lines, "ANTHROPIC_AGENT_ID", agent.id)
    lines = set_var(lines, "ANTHROPIC_ENVIRONMENT_ID", environment.id)
    env_path.write_text("\n".join(lines) + "\n")

    print("\n.env updated with agent and environment IDs.")
    print("You're ready — run the server with: uvicorn server.main:app --reload")


if __name__ == "__main__":
    main()
