#!/usr/bin/env python3
"""
Standalone CLI for the create-guest-agent skill.

Usage:
  uv run skills/create-guest-agent/scripts/create_agent.py \
    --guest-name "Kelvin Ma" \
    --email "kelvin.ma23@gmail.com" \
    --room "412" \
    --check-in "2026-05-17T15:00:00-07:00" \
    --check-out "2026-05-20T11:00:00-07:00" \
    --persona aris

  # With a pre-built profile JSON file:
  uv run skills/create-guest-agent/scripts/create_agent.py \
    --guest-name "Kelvin Ma" \
    --profile-file /tmp/guest_profile.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv
load_dotenv()

from skills.create_guest_agent import create_guest_agent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision a dedicated Claude Managed Agent for a hotel guest."
    )
    parser.add_argument("--guest-name", required=True, help="Guest's full name")
    parser.add_argument("--email", help="Guest's email address")
    parser.add_argument("--room", help="Assigned room or suite number")
    parser.add_argument("--check-in", help="Check-in datetime (ISO-8601)")
    parser.add_argument("--check-out", help="Check-out datetime (ISO-8601)")
    parser.add_argument(
        "--persona",
        choices=["aris", "thatcher", "soline"],
        default="aris",
        help="Agent persona (default: aris)",
    )
    parser.add_argument(
        "--profile-file",
        help="Path to a JSON file containing a guest profile (output of guest-research skill)",
    )
    args = parser.parse_args()

    profile = None
    if args.profile_file:
        profile = json.loads(Path(args.profile_file).read_text())

    result = create_guest_agent(
        guest_name=args.guest_name,
        guest_email=args.email,
        room=args.room,
        check_in=args.check_in,
        check_out=args.check_out,
        profile=profile,
        persona=args.persona,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
