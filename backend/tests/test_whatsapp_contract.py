import asyncio
import hmac
import json
import time
import uuid
from hashlib import sha256

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import settings
from app.db.session import get_engine
from app.main import app
from app.models import Report
from app.models.base import Base
from app.models.whatsapp import WhatsAppMessage, WhatsAppProcessedEvent
from app.services.whatsapp import normalize_jid
from app.services.whatsapp_storage import WhatsAppStorage


def test_normalize_phone_to_jid() -> None:
    assert normalize_jid("+57 3001234567") == "573001234567@s.whatsapp.net"


def test_preserve_group_jid() -> None:
    assert normalize_jid("12345@g.us") == "12345@g.us"


def test_sanitize_media_filename() -> None:
    assert WhatsAppStorage._safe_filename("../foto del grupo.png") == "foto_del_grupo.png"


def test_signed_bridge_event_is_idempotent_and_creates_a_report(monkeypatch) -> None:
    """El webhook acepta solo una firma actual y no duplica su efecto."""
    monkeypatch.setattr(settings, "whatsapp_webhook_secret", "test-webhook-secret")
    Base.metadata.create_all(get_engine())
    event_id = uuid.uuid4()
    payload = {
        "event_id": str(event_id),
        "event_type": "message.received",
        "occurred_at": "2026-09-05T12:00:00Z",
        "payload": {
            "wa_message_id": f"ficticio-{event_id}",
            "chat_jid": f"573001234567-{event_id.hex[:8]}@s.whatsapp.net",
            "sender_jid": "573001234567@s.whatsapp.net",
            "message_type": "text",
            "text": "Este es un reporte ficticio para verificar el webhook firmado.",
        },
    }
    raw = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        settings.whatsapp_webhook_secret.encode(),
        timestamp.encode() + b"." + raw,
        sha256,
    ).hexdigest()

    async def send_event() -> tuple[int, int]:
        transport = ASGITransport(app=app)
        headers = {
            "Content-Type": "application/json",
            "X-WhatsApp-Timestamp": timestamp,
            "X-WhatsApp-Signature": f"sha256={signature}",
        }
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/api/internal/whatsapp/events", content=raw, headers=headers)
            repeated = await client.post("/api/internal/whatsapp/events", content=raw, headers=headers)
            return first.status_code, repeated.status_code

    assert asyncio.run(send_event()) == (202, 202)
    with get_engine().connect() as connection:
        assert connection.execute(select(WhatsAppProcessedEvent).where(WhatsAppProcessedEvent.event_id == event_id)).one()
        assert connection.execute(select(WhatsAppMessage).where(WhatsAppMessage.wa_message_id == payload["payload"]["wa_message_id"])).one()
        assert connection.execute(select(Report).where(Report.source == "whatsapp", Report.channel == payload["payload"]["chat_jid"])).one()
