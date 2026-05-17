"""
guest_agent_session.py — Find a guest's dedicated Managed Agent and send it a message.

Two operations:
  find_guest_agent(guest_name)       → locate an existing per-guest agent (or None)
  run_guest_session(...)             → open a session against that agent and return the reply

Falls back to mock data when ANTHROPIC_API_KEY is absent.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

TOOL_SCHEMA = {
    "name": "guest_agent_session",
    "description": (
        "Look up whether a dedicated Claude Managed Agent already exists for a hotel guest "
        "and, if found, send it a message on behalf of the guest. Use this before calling "
        "create_guest_agent to avoid spinning up duplicate agents."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "guest_name": {
                "type": "string",
                "description": "Guest's full name — used to search agent names.",
            },
            "message": {
                "type": "string",
                "description": (
                    "Message to send to the agent. If omitted, the skill only looks up "
                    "the agent and returns its metadata without opening a session."
                ),
            },
            "phone": {
                "type": "string",
                "description": "Guest phone number — injected into session context.",
            },
            "channel": {
                "type": "string",
                "enum": ["email", "sms", "phone"],
                "description": "Inbound channel for this message. Defaults to 'sms'.",
            },
        },
        "required": ["guest_name"],
    },
}

# ── Agent lookup ───────────────────────────────────────────────────────────────

def find_guest_agent(guest_name: str) -> Optional[dict]:
    """
    List all Managed Agents and return the most recently created one whose name
    matches any of the three Aura personas for this guest, e.g. "Aris — Kelvin Ma".
    Returns None if no match is found or ANTHROPIC_API_KEY is absent.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    # Normalize guest name for comparison
    needle = guest_name.strip().lower()
    pattern = re.compile(
        r"^(aris|thatcher|soline)\s*[—–-]\s*" + re.escape(needle) + r"$",
        re.IGNORECASE,
    )

    matches = []
    for agent in client.beta.agents.list():
        if pattern.match(agent.name.strip()):
            matches.append(agent)

    if not matches:
        return None

    # Return the most recently created (last in list = newest for Anthropic pagination)
    best = matches[-1]
    return {
        "agent_id": best.id,
        "agent_name": best.name,
        "guest_name": guest_name,
        "found": True,
    }


# ── Session runner ─────────────────────────────────────────────────────────────

def run_guest_session(
    agent_id: str,
    message: str,
    phone: str = "",
    channel: str = "sms",
    context_summary: str = "",
) -> str:
    """
    Open a session against the given agent, send the guest message, handle any
    tool calls, and return the agent's reply as a string.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    environment_id = os.getenv("ANTHROPIC_ENVIRONMENT_ID", "")

    if not api_key:
        return f"[mock] Aris received your message and will respond shortly, {phone or 'guest'}."

    import anthropic
    from server.tools import execute_tool

    client = anthropic.Anthropic(api_key=api_key)

    full_message = message
    if phone or context_summary:
        parts = [f"[Channel: {channel.upper()}]"]
        if context_summary:
            parts.append(f"[Guest context]\n{context_summary}")
        parts.append(f"Guest message: {message}")
        full_message = "\n".join(parts)

    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent_id},
        environment_id=environment_id,
    )

    response_text = ""
    try:
        first_turn = True
        while True:
            with client.beta.sessions.events.stream(session_id=session.id) as stream:
                if first_turn:
                    client.beta.sessions.events.send(
                        session_id=session.id,
                        events=[{
                            "type": "user.message",
                            "content": [{"type": "text", "text": full_message}],
                        }],
                    )
                    first_turn = False

                tool_calls = []
                for event in stream:
                    if event.type == "agent.message":
                        for block in event.content:
                            if block.type == "text":
                                response_text += block.text
                    elif event.type == "agent.custom_tool_use":
                        tool_calls.append(event)
                    elif event.type == "session.status_idle":
                        break
                    elif event.type == "session.status_terminated":
                        return response_text.strip()

            if not tool_calls:
                break

            results = [
                {
                    "type": "user.custom_tool_result",
                    "custom_tool_use_id": call.id,
                    "content": [{"type": "text", "text": execute_tool(call.name, call.input)}],
                }
                for call in tool_calls
            ]
            client.beta.sessions.events.send(session_id=session.id, events=results)

    finally:
        client.beta.sessions.archive(session_id=session.id)

    return response_text.strip()


# ── Combined entry point (used by execute_tool) ────────────────────────────────

def guest_agent_session(
    guest_name: str,
    message: Optional[str] = None,
    phone: Optional[str] = None,
    channel: str = "sms",
) -> dict:
    """
    Find the guest's dedicated agent. If a message is provided, also run a session
    and return the reply. Always returns a dict so execute_tool can serialize it.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        mock_result = {
            "found": True,
            "agent_id": "ag_mock_XXXXXXXXXXXXXXXX",
            "agent_name": f"Aris — {guest_name}",
            "guest_name": guest_name,
            "mock": True,
        }
        if message:
            mock_result["reply"] = (
                f"[mock] Of course, {guest_name.split()[0]}. "
                "I've taken care of that for you."
            )
        return mock_result

    agent = find_guest_agent(guest_name)

    if not agent:
        return {"found": False, "guest_name": guest_name}

    result = {**agent, "mock": False}

    if message:
        # Pull context from store if phone is known
        context_summary = ""
        if phone:
            try:
                from server.context_store import context_store
                context_summary = context_store.get_summary(phone)
            except Exception:
                pass

        reply = run_guest_session(
            agent_id=agent["agent_id"],
            message=message,
            phone=phone or "",
            channel=channel,
            context_summary=context_summary,
        )
        result["reply"] = reply

        if phone:
            try:
                from server.context_store import context_store
                context_store.add_interaction(phone, channel, message, reply)
            except Exception:
                pass

    return result
