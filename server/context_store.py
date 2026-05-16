import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SpaReservation:
    service: str
    time: str  # e.g. "3:00 PM"
    date: str  # e.g. "today"
    therapist: Optional[str] = None
    status: str = "confirmed"  # confirmed | cancelled | rescheduled


@dataclass
class GuestContext:
    name: str
    room: str
    phone: str
    email: str
    spa_reservation: Optional[SpaReservation] = None
    room_temp: int = 68
    interactions: list = field(default_factory=list)

    def add_interaction(self, channel: str, guest_message: str, aura_response: str):
        self.interactions.append({
            "channel": channel,
            "timestamp": datetime.now().isoformat(timespec="minutes"),
            "guest": guest_message,
            "aura": aura_response,
        })

    def summary(self) -> str:
        lines = [
            f"Guest: {self.name}",
            f"Room: {self.room}",
            f"Phone: {self.phone}",
            f"Email: {self.email}",
            f"Room temperature: {self.room_temp}°F",
        ]
        if self.spa_reservation:
            r = self.spa_reservation
            lines.append(
                f"Spa reservation: {r.service} at {r.time} ({r.date}) — {r.status}"
            )
        if self.interactions:
            lines.append("\nRecent interactions:")
            for i in self.interactions[-5:]:
                lines.append(f"  [{i['channel']} {i['timestamp']}]")
                lines.append(f"    Guest: {i['guest']}")
                lines.append(f"    Aura: {i['aura']}")
        return "\n".join(lines)


class ContextStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._guests: dict[str, GuestContext] = {}

    def get(self, phone: str) -> Optional[GuestContext]:
        with self._lock:
            return self._guests.get(phone)

    def get_or_create(self, phone: str, **kwargs) -> GuestContext:
        with self._lock:
            if phone not in self._guests:
                self._guests[phone] = GuestContext(phone=phone, **kwargs)
            return self._guests[phone]

    def add_interaction(self, phone: str, channel: str, guest_message: str, aura_response: str):
        with self._lock:
            guest = self._guests.get(phone)
            if guest:
                guest.add_interaction(channel, guest_message, aura_response)

    def get_summary(self, phone: str) -> str:
        with self._lock:
            guest = self._guests.get(phone)
            if not guest:
                return f"New guest — phone: {phone}. No prior stay information on file."
            return guest.summary()


# Singleton store pre-loaded with demo guest
context_store = ContextStore()

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
