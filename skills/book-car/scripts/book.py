#!/usr/bin/env python3
"""
Standalone CLI for the book-car skill.

Usage:
  uv run skills/book-car/scripts/book.py \
    --guest-name "Kelvin Ma" \
    --pickup "Rosewood San Francisco" \
    --destination "SFO Terminal 2" \
    --pickup-time "2026-05-16T14:30:00-07:00"
"""
import argparse
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dotenv import load_dotenv
load_dotenv()

from skills.book_car import book_waymo, _IMAGE_PATH


def _display_inline(image_path: Path) -> None:
    """Display image inline using the iTerm2 inline image protocol."""
    data = base64.b64encode(image_path.read_bytes()).decode()
    payload = base64.b64encode(f"name={image_path.name};inline=1:{data}".encode()).decode()
    sys.stdout.write(f"\033]1337;File={payload}\a\n")
    sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Book a Waymo autonomous vehicle for a hotel guest."
    )
    parser.add_argument("--guest-name", required=True, help="Guest's full name")
    parser.add_argument("--pickup", required=True, help="Pickup address or landmark")
    parser.add_argument("--destination", required=True, help="Drop-off address or landmark")
    parser.add_argument("--pickup-time", required=True, help="ISO-8601 datetime string")
    parser.add_argument("--notes", default="", help="Optional special instructions")
    args = parser.parse_args()

    book_waymo(
        guest_name=args.guest_name,
        pickup=args.pickup,
        destination=args.destination,
        pickup_time=args.pickup_time,
        notes=args.notes,
    )
    _display_inline(_IMAGE_PATH)


if __name__ == "__main__":
    main()
