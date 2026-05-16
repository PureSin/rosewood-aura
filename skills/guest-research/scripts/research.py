#!/usr/bin/env python3
"""
Standalone CLI for the guest-research skill.

Usage:
  uv run skills/guest-research/scripts/research.py --name "Kelvin Ma" --email "k@example.com"
"""
import argparse
import json
import sys
from pathlib import Path

# Allow running from any working directory inside the project
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv
load_dotenv()

from skills.customer_research import research_guest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research a hotel guest's interests and preferences using Exa + Claude."
    )
    parser.add_argument("--name", required=True, help="Guest's full name")
    parser.add_argument("--email", help="Guest's email address")
    parser.add_argument("--twitter", help="Twitter/X handle, e.g. @KelvinHMa")
    parser.add_argument("--instagram", help="Instagram handle")
    parser.add_argument("--website", help="Personal website URL, helps resolve name collisions")
    args = parser.parse_args()

    social: dict[str, str] = {}
    if args.twitter:
        social["twitter"] = args.twitter
    if args.instagram:
        social["instagram"] = args.instagram
    if args.website:
        social["website"] = args.website

    result = research_guest(args.name, args.email, social or None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
