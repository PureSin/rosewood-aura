#!/usr/bin/env python3
"""
Standalone CLI for the guest-agent-session skill.

Usage:
  # Check whether a guest agent exists:
  uv run skills/guest-agent-session/scripts/session.py --guest-name "Kelvin Ma"

  # Find and send a message:
  uv run skills/guest-agent-session/scripts/session.py \
    --guest-name "Kelvin Ma" \
    --message "Can you reschedule my 3pm massage to 4:30pm?" \
    --phone "+14155551234" \
    --channel sms
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv
load_dotenv()

from skills.guest_agent_session import guest_agent_session


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find a guest's dedicated Managed Agent and optionally send it a message."
    )
    parser.add_argument("--guest-name", required=True, help="Guest's full name")
    parser.add_argument("--message", help="Message to send to the agent (optional — omit to just look up)")
    parser.add_argument("--phone", help="Guest phone number for context injection")
    parser.add_argument(
        "--channel",
        choices=["email", "sms", "phone"],
        default="sms",
        help="Inbound channel (default: sms)",
    )
    args = parser.parse_args()

    result = guest_agent_session(
        guest_name=args.guest_name,
        message=args.message,
        phone=args.phone,
        channel=args.channel,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
