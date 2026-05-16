---
name: book-car
description: >
  Book a Waymo autonomous vehicle for a hotel guest via the Waymo One for Business API
  (https://waymo.com/business/). Use this skill whenever a guest needs airport pickup,
  a ride to a restaurant, a day-trip transfer, or any ground transportation request.
compatibility: Requires Python 3.9+, uv, and WAYMO_API_KEY in the environment (falls back to mock data if absent).
metadata:
  author: rosewood-aura
  version: "1.0"
---

## Overview

This skill calls the Waymo One for Business API to dispatch an autonomous vehicle for a
named hotel guest. It takes a pickup location, destination, and desired pickup time, then
returns a confirmed booking with vehicle details and estimated arrival. If `WAYMO_API_KEY`
is not set, it falls back to rich mock data so the demo always works.

## When to activate

- A guest asks for a ride to the airport, restaurant, or attraction
- Aura calls `update_pms_room_prep` and wants to pre-arrange arrival transportation
- A guest's email contains a flight itinerary and needs an airport pickup
- A concierge request involves ground transportation of any kind

## Inputs

| Field           | Required | Description                                                  |
|-----------------|----------|--------------------------------------------------------------|
| `guest_name`    | Yes      | Guest's full name (used to personalise the in-car greeting)  |
| `pickup`        | Yes      | Pickup address or landmark (e.g. "Rosewood San Francisco")   |
| `destination`   | Yes      | Drop-off address or landmark (e.g. "SFO Terminal 2")         |
| `pickup_time`   | Yes      | ISO-8601 datetime string (e.g. "2026-05-16T14:30:00-07:00") |
| `notes`         | No       | Special instructions (e.g. "guest has two large suitcases")  |

## Outputs

The script prints a JSON object:

```json
{
  "booking_id": "WMO-2026-88421",
  "status": "confirmed",
  "guest_name": "Kelvin Ma",
  "pickup": "Rosewood San Francisco, 495 Geary St, San Francisco, CA 94102",
  "destination": "SFO Terminal 2",
  "pickup_time": "2026-05-16T14:30:00-07:00",
  "estimated_arrival_minutes": 4,
  "vehicle": {
    "model": "Jaguar I-PACE",
    "color": "Midnight Black",
    "license_plate": "WMO-4821"
  },
  "waymo_tracking_url": "https://waymo.com/ride/WMO-2026-88421",
  "notes": "guest has two large suitcases"
}
```

## How to use

### Run as a script

```bash
uv run skills/book-car/scripts/book.py \
  --guest-name "Kelvin Ma" \
  --pickup "Rosewood San Francisco" \
  --destination "SFO Terminal 2" \
  --pickup-time "2026-05-16T14:30:00-07:00" \
  --notes "guest has two large suitcases"
```

### Call as a Python function (server integration)

```python
from skills.book_car import book_waymo

booking = book_waymo(
    guest_name="Kelvin Ma",
    pickup="Rosewood San Francisco",
    destination="SFO Terminal 2",
    pickup_time="2026-05-16T14:30:00-07:00",
    notes="guest has two large suitcases",
)
# booking is a dict with the fields above
```

The `book_waymo` function is also registered as the `book_car` tool in
`server/tools.py`, so Aura can call it directly during an agent session.

## Steps

1. Validate inputs — ensure `pickup_time` is a valid ISO-8601 string and not in the past.
2. If `WAYMO_API_KEY` is set, POST to the Waymo One for Business booking endpoint with
   guest name, pickup, destination, and pickup time.
3. Parse the response into a `BookingResult` dataclass and return it serialised to dict.
4. If `WAYMO_API_KEY` is absent or the API returns an error, return a realistic mock
   booking so the demo always completes without a real API key.

## How to use the result in Aura

After calling `book_waymo`, weave the booking into the guest's response:

- Confirm the ride in the reply channel ("Your Waymo will arrive at 2:30 PM — a black Jaguar I-PACE, plate WMO-4821.")
- Store `booking_id` in the guest's PMS notes for front-desk visibility
- If the pickup is airport arrival, chain directly into `update_pms_room_prep` to pre-cool the room

## Edge cases

- **Pickup time in the past**: Raise a `ValueError` and ask the guest to confirm the time.
- **No service area**: Waymo currently operates in select US cities. Return a helpful error
  and suggest a hotel-arranged town car as a fallback.
- **API unavailable**: Fall back to mock data; log the error for ops review.
