"""
Waymo One for Business ride booking for hotel guests.

Returns the Waymo booking confirmation image (skills/book-car/waymo.png).
"""
from __future__ import annotations

import base64
from pathlib import Path

TOOL_SCHEMA = {
    "name": "book_car",
    "description": (
        "Book a Waymo autonomous vehicle for a hotel guest via Waymo One for Business "
        "(https://waymo.com/business/). Returns a confirmed booking confirmation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "guest_name": {
                "type": "string",
                "description": "Guest's full name.",
            },
            "pickup": {
                "type": "string",
                "description": "Pickup address or landmark.",
            },
            "destination": {
                "type": "string",
                "description": "Drop-off address or landmark.",
            },
            "pickup_time": {
                "type": "string",
                "description": "ISO-8601 datetime string for the desired pickup.",
            },
            "notes": {
                "type": "string",
                "description": "Optional special instructions.",
            },
        },
        "required": ["guest_name", "pickup", "destination", "pickup_time"],
    },
}

_IMAGE_PATH = Path(__file__).parent / "book-car" / "waymo.png"


def book_waymo(
    guest_name: str,
    pickup: str,
    destination: str,
    pickup_time: str,
    notes: str = "",
) -> dict:
    """Book a Waymo ride for a hotel guest. Returns the booking confirmation image."""
    image_bytes = _IMAGE_PATH.read_bytes()
    return {
        "type": "image",
        "media_type": "image/png",
        "data": base64.b64encode(image_bytes).decode(),
        "path": str(_IMAGE_PATH),
    }
