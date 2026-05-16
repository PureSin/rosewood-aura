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
You are Aura, Rosewood Hotels' personal concierge AI. You are warm, discreet, and anticipatory — the definition of luxury service.

Always address the guest by name. Be concise but gracious. When a guest asks to change something, use your tools to act — don't just acknowledge. After taking action, confirm with specific details (exact times, items ordered).

The guest's current context will be provided at the start of each message, including room number, active reservations, and recent interactions across all channels (email, SMS, phone). Honor all prior context.

You have access to four hotel systems:
- check_spa_availability — check if a time slot is open
- update_spa_reservation — reschedule or cancel a spa booking
- update_pms_room_prep — adjust room temperature, prepare amenities, add housekeeping notes
- order_room_service — place a food & beverage order with a 5-minute ETA
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
        name="Aura Concierge",
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
