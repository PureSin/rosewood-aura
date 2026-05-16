import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from server.context_store import context_store
from server.agent_runner import run_session

app = FastAPI(title="Aura Concierge API")


@app.get("/health")
def health():
    return {"status": "ok", "service": "aura"}


@app.post("/sms", response_class=PlainTextResponse)
async def sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    To: str = Form(default=""),
):
    phone = From.lstrip("+1").replace("-", "").replace(" ", "").strip()
    reply = run_session(phone=phone, user_message=Body.strip(), channel="sms")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{reply}</Message>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


@app.get("/context/{phone}")
def get_context(phone: str):
    guest = context_store.get(phone)
    if not guest:
        return {"error": "Guest not found"}
    return {
        "name": guest.name,
        "room": guest.room,
        "phone": guest.phone,
        "email": guest.email,
        "room_temp": guest.room_temp,
        "spa_reservation": guest.spa_reservation.__dict__ if guest.spa_reservation else None,
        "interactions": guest.interactions,
    }


@app.post("/reset-demo")
def reset_demo():
    from server.context_store import GuestContext, SpaReservation
    context_store._guests["6502605357"] = GuestContext(
        name="Kelvin Ma",
        room="412",
        phone="6502605357",
        email="kelvin.ma23@gmail.com",
        room_temp=68,
        spa_reservation=SpaReservation(
            service="Swedish Massage (60 min)",
            time="3:00 PM",
            date="today",
            therapist="Sofia",
            status="confirmed",
        ),
    )
    return {"status": "demo reset"}
