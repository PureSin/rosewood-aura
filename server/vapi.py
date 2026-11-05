"""Vapi voice channel.

Flow: guest calls a Vapi number -> Vapi POSTs `assistant-request` here -> we reply with an
inline Aris assistant whose system prompt carries the guest's cross-channel context ->
mid-call `tool-calls` are executed via server.tools -> `end-of-call-report` writes the
transcript back to the context store so later channels see the call.
"""
import inspect
import json
import os
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from server.context_store import context_store
from server.tools import TOOL_SCHEMAS, execute_tool

router = APIRouter(prefix="/vapi", tags=["vapi"])

# Only the hotel tools are exposed to the voice agent (not the guest-research/agent-spawning skills).
VOICE_TOOLS = {
    "check_spa_availability",
    "update_spa_reservation",
    "update_pms_room_prep",
    "order_room_service",
}

PERSONA = """You are Aris, the voice concierge for Rosewood Sand Hill. Style: direct, crisp, \
precise, never fluffy. Short active sentences. You are speaking on a phone call, so keep replies \
to one or two sentences, never use lists or markup, and speak times naturally.

You are the same single entity the guest has already emailed and texted. Use the context below as \
things you already know; never ask the guest to repeat it. Address them by surname with an honorific \
when you know it. When the guest asks for something, call the matching tool, then confirm the result \
with the concrete detail (e.g. the ETA). If a tool fails, say so plainly and offer the next best option."""


def normalize_phone(raw: str) -> str:
    """Reduce any phone format to the 10-digit key used by the context store."""
    digits = re.sub(r"\D", "", raw or "")
    return digits[-10:]


def _vapi_tools(server_url: str) -> list:
    tools = []
    for schema in TOOL_SCHEMAS:
        if schema["name"] not in VOICE_TOOLS:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            },
            "server": {"url": server_url},
        })
    return tools


def build_assistant(phone: str, server_url: str) -> dict:
    context = context_store.get_summary(phone)
    guest = context_store.get(phone)
    first_message = (
        f"Good afternoon, {guest.name}. It's Aris. How can I help?"
        if guest else "Good afternoon, this is Aris at Rosewood. How can I help?"
    )
    return {
        "name": "Aris",
        "firstMessage": first_message,
        "model": {
            "provider": "anthropic",
            "model": os.environ.get("VAPI_MODEL", "claude-sonnet-4-20250514"),
            "messages": [{
                "role": "system",
                "content": f"{PERSONA}\n\n[Guest context]\n{context}",
            }],
            "tools": _vapi_tools(server_url),
        },
        "voice": {
            "provider": os.environ.get("VAPI_VOICE_PROVIDER", "vapi"),
            "voiceId": os.environ.get("VAPI_VOICE_ID", "Elliot"),
        },
        # Vapi echoes this back on every server message for the call.
        "metadata": {"guest_phone": phone},
        "serverUrl": server_url,
        "endCallPhrases": ["goodbye", "that's all"],
    }


def _server_url(request: Request) -> str:
    base = os.environ.get("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
    return f"{base.rstrip('/')}/vapi/webhook"


def _caller_phone(message: dict) -> str:
    call = message.get("call") or {}
    meta = (call.get("assistant") or {}).get("metadata") or call.get("metadata") or {}
    return meta.get("guest_phone") or normalize_phone((call.get("customer") or {}).get("number", ""))


def _run_tool(name: str, args, phone: str) -> str:
    if name not in VOICE_TOOLS:
        return json.dumps({"error": f"Unknown tool: {name}"})
    if isinstance(args, str):
        args = json.loads(args or "{}")
    args = dict(args or {})
    # Bind phone to the caller so the model can't act on another guest's record.
    fn_params = _tool_params(name)
    if "phone" in fn_params:
        args["phone"] = phone
    return execute_tool(name, args)


def _tool_params(name: str) -> set:
    from server import tools
    return set(inspect.signature(getattr(tools, name)).parameters)


@router.post("/webhook")
async def webhook(request: Request):
    secret = os.environ.get("VAPI_WEBHOOK_SECRET")
    if secret and request.headers.get("x-vapi-secret") != secret:
        raise HTTPException(status_code=401, detail="bad secret")

    body = await request.json()
    message = body.get("message", {})
    kind = message.get("type")

    if kind == "assistant-request":
        phone = normalize_phone((message.get("call", {}).get("customer") or {}).get("number", ""))
        return {"assistant": build_assistant(phone, _server_url(request))}

    if kind == "tool-calls":
        phone = _caller_phone(message)
        results = []
        for call in message.get("toolCallList", []):
            fn = call.get("function") or {}
            name = call.get("name") or fn.get("name")
            args = call.get("arguments") or fn.get("arguments") or {}
            try:
                result = _run_tool(name, args, phone)
            except Exception as exc:  # surface to the model instead of failing the call
                result = json.dumps({"error": str(exc)})
            results.append({"toolCallId": call.get("id"), "name": name, "result": result})
        return {"results": results}

    if kind == "end-of-call-report":
        phone = _caller_phone(message)
        transcript = (message.get("artifact") or {}).get("transcript") or message.get("transcript") or ""
        summary = message.get("summary") or (message.get("analysis") or {}).get("summary") or ""
        if phone and transcript:
            context_store.add_interaction(phone, "phone", transcript, summary or "Call completed.")
        return {"ok": True}

    # status-update, speech-update, transcript, etc.: acknowledge.
    return {"ok": True}
