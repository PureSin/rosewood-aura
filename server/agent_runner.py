import os
import anthropic
from server.context_store import context_store
from server.tools import execute_tool

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

AGENT_ID = os.environ.get("ANTHROPIC_AGENT_ID", "")
ENVIRONMENT_ID = os.environ.get("ANTHROPIC_ENVIRONMENT_ID", "")


def run_session(phone: str, user_message: str, channel: str = "sms") -> str:
    """Run one agent session for an incoming guest message. Returns Aura's reply."""
    context_summary = context_store.get_summary(phone)
    full_message = (
        f"[Channel: {channel.upper()}]\n"
        f"[Guest context]\n{context_summary}\n\n"
        f"Guest message: {user_message}"
    )

    session = client.beta.sessions.create(
        agent={"type": "agent", "id": AGENT_ID},
        environment_id=ENVIRONMENT_ID,
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

    reply = response_text.strip()
    context_store.add_interaction(phone, channel, user_message, reply)
    return reply
