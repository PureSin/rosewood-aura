import json
from datetime import datetime
from typing import Optional
from server.context_store import context_store
from skills.customer_research import TOOL_SCHEMA as _RESEARCH_SCHEMA, research_guest
from skills.create_guest_agent import TOOL_SCHEMA as _CREATE_AGENT_SCHEMA, create_guest_agent

# Tool schemas — passed to agents.create()
TOOL_SCHEMAS = [
    _RESEARCH_SCHEMA,
    _CREATE_AGENT_SCHEMA,
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
                "action": {"type": "string", "enum": ["reschedule", "cancel"], "description": "What to do"},
                "new_time": {"type": "string", "description": "New time if rescheduling, e.g. '4:30 PM'"},
            },
            "required": ["phone", "action"],
        },
    },
    {
        "type": "custom",
        "name": "update_pms_room_prep",
        "description": "Update room settings in the Property Management System — temperature, welcome amenity, special notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phone": {"type": "string", "description": "Guest phone number"},
                "temperature": {"type": "integer", "description": "Target room temperature in °F"},
                "amenity": {"type": "string", "description": "Welcome amenity to prepare, e.g. 'local honey and lavender tea'"},
                "notes": {"type": "string", "description": "Additional notes for housekeeping or front desk"},
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
                    "description": "List of items to order, e.g. ['double espresso', 'still water']",
                },
                "note": {"type": "string", "description": "Special instructions"},
            },
            "required": ["phone", "items"],
        },
    },
]


# Mock implementations

def check_spa_availability(time: str, service: str = "massage") -> dict:
    busy = ["2:00 PM", "2:30 PM", "5:00 PM"]
    available = time not in busy
    return {
        "available": available,
        "time": time,
        "service": service,
        "next_available": "4:30 PM" if not available else None,
    }


def update_spa_reservation(phone: str, action: str, new_time: Optional[str] = None) -> dict:
    guest = context_store.get(phone)
    if not guest or not guest.spa_reservation:
        return {"success": False, "error": "No spa reservation found for this guest."}

    old_time = guest.spa_reservation.time
    if action == "cancel":
        guest.spa_reservation.status = "cancelled"
        return {"success": True, "action": "cancelled", "previous_time": old_time}
    elif action == "reschedule" and new_time:
        guest.spa_reservation.time = new_time
        guest.spa_reservation.status = "rescheduled"
        return {"success": True, "action": "rescheduled", "old_time": old_time, "new_time": new_time}

    return {"success": False, "error": "Invalid action or missing new_time for reschedule."}


def update_pms_room_prep(phone: str, temperature: Optional[int] = None, amenity: Optional[str] = None, notes: Optional[str] = None) -> dict:
    guest = context_store.get(phone)
    if not guest:
        return {"success": False, "error": "Guest not found."}

    updates = {}
    if temperature is not None:
        guest.room_temp = temperature
        updates["temperature"] = f"{temperature}°F"
    if amenity:
        updates["amenity"] = amenity
    if notes:
        updates["notes"] = notes

    return {"success": True, "room": guest.room, "updates_applied": updates}


def order_room_service(phone: str, items: list, note: Optional[str] = None) -> dict:
    guest = context_store.get(phone)
    room = guest.room if guest else "unknown"
    order_id = f"RS-{datetime.now().strftime('%H%M%S')}"
    return {
        "success": True,
        "order_id": order_id,
        "room": room,
        "items": items,
        "eta_minutes": 5,
        "note": note,
    }


def execute_tool(name: str, inputs: dict) -> str:
    handlers = {
        "research_guest": research_guest,
        "create_guest_agent": create_guest_agent,
        "check_spa_availability": check_spa_availability,
        "update_spa_reservation": update_spa_reservation,
        "update_pms_room_prep": update_pms_room_prep,
        "order_room_service": order_room_service,
    }
    fn = handlers.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = fn(**inputs)
    return json.dumps(result)
