from __future__ import annotations

import hmac
import json
import time
import uuid
from hashlib import sha256
from typing import Any

import httpx
from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.whatsapp import (
    WhatsAppConversation,
    WhatsAppMedia,
    WhatsAppMessage,
    WhatsAppMessageEvent,
    WhatsAppOutbox,
    WhatsAppPoll,
    WhatsAppPollOption,
    WhatsAppPollVote,
    WhatsAppProcessedEvent,
)
from app.models import CaseHistory, Report
from app.schemas.reports import ReportCreate
from app.services.reports import create_report
from app.schemas.whatsapp import (
    BridgeEvent,
    ContactCommand,
    LocationCommand,
    MediaCommand,
    PollCommand,
    ReactionCommand,
    TextCommand,
)


def normalize_jid(recipient: str) -> str:
    compact = recipient.strip().replace("+", "").replace(" ", "")
    return compact if "@" in compact else f"{compact}@s.whatsapp.net"


def verify_bridge_signature(raw_body: bytes, timestamp: str | None, signature: str | None) -> bool:
    if not timestamp or not signature or not settings.whatsapp_webhook_secret:
        return False
    try:
        sent_at = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - sent_at) > 300:
        return False
    signed = timestamp.encode() + b"." + raw_body
    expected = hmac.new(settings.whatsapp_webhook_secret.encode(), signed, sha256).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256="))


class WhatsAppService:
    def __init__(self, db: Session):
        self.db = db

    def list_conversations(self, limit: int = 30) -> list[WhatsAppConversation]:
        statement = select(WhatsAppConversation).order_by(
            WhatsAppConversation.last_message_at.desc().nullslast(),
            WhatsAppConversation.id,
        ).limit(min(max(limit, 1), 100))
        return list(self.db.scalars(statement))

    def get_messages(self, conversation_id: uuid.UUID, limit: int = 50) -> list[WhatsAppMessage]:
        statement: Select[tuple[WhatsAppMessage]] = (
            select(WhatsAppMessage)
            .where(WhatsAppMessage.conversation_id == conversation_id)
            .order_by(WhatsAppMessage.occurred_at.desc(), WhatsAppMessage.id.desc())
            .limit(min(max(limit, 1), 100))
        )
        return list(reversed(list(self.db.scalars(statement))))

    def get_conversation_context(self, conversation_id: uuid.UUID, limit: int = 50) -> dict[str, Any]:
        conversation = self.db.get(WhatsAppConversation, conversation_id)
        if not conversation:
            raise LookupError("Conversación no encontrada")
        messages = self.get_messages(conversation_id, limit)
        return {
            "conversation": {
                "id": str(conversation.id),
                "chat_jid": conversation.chat_jid,
                "kind": conversation.kind,
                "title": conversation.title,
            },
            "messages": [
                {
                    "id": str(message.id),
                    "direction": message.direction,
                    "type": message.message_type,
                    "text": message.text_content,
                    "caption": message.caption,
                    "status": message.status,
                    "occurred_at": message.occurred_at.isoformat(),
                    "metadata": message.metadata_json,
                }
                for message in messages
            ],
        }

    def send_text(self, command: TextCommand) -> WhatsAppMessage:
        return self._enqueue(
            recipient=command.recipient,
            kind="text",
            text=command.text,
            quoted_message_id=command.quoted_message_id,
            payload={"text": command.text},
        )

    def reply(self, message_id: uuid.UUID, text: str) -> WhatsAppMessage:
        target = self.db.get(WhatsAppMessage, message_id)
        if not target:
            raise LookupError("Mensaje citado no encontrado")
        conversation = self.db.get(WhatsAppConversation, target.conversation_id)
        if not conversation:
            raise LookupError("Conversación no encontrada")
        return self.send_text(TextCommand(
            recipient=conversation.chat_jid,
            text=text,
            quoted_message_id=message_id,
        ))

    def send_location(self, command: LocationCommand) -> WhatsAppMessage:
        return self._enqueue(
            recipient=command.recipient,
            kind="location",
            payload={
                "latitude": command.latitude,
                "longitude": command.longitude,
                "name": command.name,
                "address": command.address,
            },
        )

    def send_media(self, command: MediaCommand) -> WhatsAppMessage:
        try:
            message = self._enqueue(
                recipient=command.recipient,
                kind=command.media_kind,
                payload={
                    "storage_path": command.storage_path,
                    "mime_type": command.mime_type,
                    "caption": command.caption,
                },
                quoted_message_id=command.quoted_message_id,
                commit=False,
            )
            self.db.add(WhatsAppMedia(
                message_id=message.id,
                media_kind=command.media_kind,
                storage_path=command.storage_path,
                mime_type=command.mime_type,
            ))
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception:
            self.db.rollback()
            raise

    def send_contact(self, command: ContactCommand) -> WhatsAppMessage:
        return self._enqueue(
            recipient=command.recipient,
            kind="contact",
            text=command.display_name,
            payload={"display_name": command.display_name, "vcard": command.vcard},
        )

    def react(self, command: ReactionCommand) -> WhatsAppMessage:
        target = self.db.get(WhatsAppMessage, command.message_id)
        if not target or not target.wa_message_id:
            raise LookupError("Mensaje de WhatsApp no encontrado")
        conversation = self.db.get(WhatsAppConversation, target.conversation_id)
        if not conversation:
            raise LookupError("Conversación no encontrada")
        return self._enqueue(
            recipient=conversation.chat_jid,
            kind="reaction",
            payload={"target_wa_message_id": target.wa_message_id, "emoji": command.emoji},
        )

    def send_poll(self, command: PollCommand) -> WhatsAppMessage:
        if command.selectable_count > len(command.options):
            raise ValueError("selectable_count no puede superar el número de opciones")
        try:
            message = self._enqueue(
                recipient=command.recipient,
                kind="poll",
                text=command.question,
                payload={
                    "question": command.question,
                    "options": command.options,
                    "selectable_count": command.selectable_count,
                },
                commit=False,
            )
            poll = WhatsAppPoll(
                message_id=message.id,
                question=command.question,
                selectable_count=command.selectable_count,
            )
            self.db.add(poll)
            self.db.flush()
            self.db.add_all([
                WhatsAppPollOption(poll_id=poll.id, option_index=index, label=label)
                for index, label in enumerate(command.options)
            ])
            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception:
            self.db.rollback()
            raise

    def _enqueue(
        self,
        *,
        recipient: str,
        kind: str,
        payload: dict[str, Any],
        text: str | None = None,
        quoted_message_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> WhatsAppMessage:
        jid = normalize_jid(recipient)
        conversation = self.db.scalar(select(WhatsAppConversation).where(WhatsAppConversation.chat_jid == jid))
        if not conversation:
            conversation = WhatsAppConversation(
                chat_jid=jid,
                kind="group" if jid.endswith("@g.us") else "direct",
                participant_jid=None if jid.endswith("@g.us") else jid,
            )
            self.db.add(conversation)
            self.db.flush()
        message = WhatsAppMessage(
            conversation_id=conversation.id,
            direction="outbound",
            message_type=kind,
            text_content=text,
            quoted_message_id=quoted_message_id,
            status="queued",
            metadata_json={},
        )
        self.db.add(message)
        self.db.flush()
        quoted_wa_message_id: str | None = None
        if quoted_message_id:
            quoted = self.db.get(WhatsAppMessage, quoted_message_id)
            if not quoted or not quoted.wa_message_id or quoted.conversation_id != conversation.id:
                raise ValueError("El mensaje citado no pertenece a esta conversación o aún no fue enviado")
            quoted_wa_message_id = quoted.wa_message_id
            message.quoted_wa_message_id = quoted_wa_message_id
        self.db.add(WhatsAppOutbox(
            message_id=message.id,
            command={
                "kind": kind,
                "recipient": jid,
                **payload,
                **({"quoted_wa_message_id": quoted_wa_message_id} if quoted_wa_message_id else {}),
            },
        ))
        if commit:
            self.db.commit()
            self.db.refresh(message)
        return message

    def process_bridge_event(self, event: BridgeEvent) -> None:
        if self.db.get(WhatsAppProcessedEvent, event.event_id):
            return
        self.db.add(WhatsAppProcessedEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
        ))
        try:
            if event.event_type == "message.status":
                self._process_status_event(event)
            elif event.event_type == "poll.updated":
                self._process_poll_event(event)
            elif event.event_type == "message.received":
                self._process_message_event(event)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _process_message_event(self, event: BridgeEvent) -> None:
        payload = event.payload
        chat_jid = str(payload["chat_jid"])
        conversation = self.db.scalar(select(WhatsAppConversation).where(WhatsAppConversation.chat_jid == chat_jid))
        if not conversation:
            conversation = WhatsAppConversation(
                chat_jid=chat_jid,
                kind="group" if chat_jid.endswith("@g.us") else "direct",
                participant_jid=payload.get("sender_jid"),
            )
            self.db.add(conversation)
            self.db.flush()
        wa_message_id = str(payload["wa_message_id"])
        duplicate = self.db.scalar(
            select(WhatsAppMessage.id).where(
                WhatsAppMessage.conversation_id == conversation.id,
                WhatsAppMessage.wa_message_id == wa_message_id,
                WhatsAppMessage.direction == "inbound",
            )
        )
        if duplicate:
            return
        message = WhatsAppMessage(
            conversation_id=conversation.id,
            wa_message_id=wa_message_id,
            direction="inbound",
            message_type=str(payload.get("message_type", "unknown")),
            sender_jid=payload.get("sender_jid"),
            text_content=payload.get("text"),
            caption=payload.get("caption"),
            quoted_wa_message_id=payload.get("quoted_wa_message_id"),
            status="delivered",
            metadata_json=payload.get("metadata", {}),
            occurred_at=event.occurred_at,
        )
        self.db.add(message)
        self.db.flush()
        media = payload.get("media")
        if isinstance(media, dict) and media.get("storage_path"):
            self.db.add(WhatsAppMedia(
                message_id=message.id,
                media_kind=str(media.get("media_kind", message.message_type)),
                storage_bucket=str(media.get("storage_bucket", "whatsapp-media")),
                storage_path=str(media["storage_path"]),
                mime_type=str(media.get("mime_type", "application/octet-stream")),
                size_bytes=media.get("size_bytes"),
                sha256=media.get("sha256"),
            ))
        if message.message_type == "poll":
            options = message.metadata_json.get("options", [])
            poll = WhatsAppPoll(
                message_id=message.id,
                question=message.text_content or "Encuesta",
                selectable_count=int(message.metadata_json.get("selectable_count", 1)),
            )
            self.db.add(poll)
            self.db.flush()
            self.db.add_all([
                WhatsAppPollOption(poll_id=poll.id, option_index=index, label=str(label))
                for index, label in enumerate(options)
            ])
        conversation.last_message_at = event.occurred_at
        self._attach_message_to_report(conversation, message)

    def _attach_message_to_report(self, conversation: WhatsAppConversation, message: WhatsAppMessage) -> None:
        """Crea un caso solo para un chat directo y enlaza sus mensajes posteriores."""
        if conversation.kind != "direct":
            return
        sender = (message.sender_jid or conversation.chat_jid).split("@", 1)[0]
        report = self.db.scalar(select(Report).where(
            Report.source == "whatsapp",
            Report.channel == conversation.chat_jid,
        ).order_by(Report.created_at.desc()))
        text = (message.text_content or message.caption or "Mensaje recibido mediante WhatsApp.").strip()
        if not report:
            description = text if len(text) >= 20 else f"Reporte recibido por WhatsApp: {text}"
            report = create_report(self.db, ReportCreate(
                category="otro",
                description=description[:5000],
                channel=conversation.chat_jid,
                related_information={"whatsapp_conversation_id": str(conversation.id)},
                reporter_name="Persona por WhatsApp",
                contact_type="phone",
                contact_value=sender,
            ), source="whatsapp", commit=False)
        else:
            self.db.add(CaseHistory(
                report_id=report.id,
                action="Mensaje de seguimiento recibido por WhatsApp",
                details={"whatsapp_message_id": str(message.id)},
                actor_type="whatsapp",
            ))

    def _process_status_event(self, event: BridgeEvent) -> None:
        payload = event.payload
        message = self.db.scalar(select(WhatsAppMessage).where(WhatsAppMessage.wa_message_id == payload.get("wa_message_id")))
        if not message:
            return
        status = {0: "failed", 1: "sending", 2: "sent", 3: "delivered", 4: "read", 5: "read"}.get(
            int(payload.get("status_code", -1)),
            message.status,
        )
        message.status = status
        self.db.add(WhatsAppMessageEvent(
            event_id=event.event_id,
            message_id=message.id,
            status=status,
            occurred_at=event.occurred_at,
        ))

    def _process_poll_event(self, event: BridgeEvent) -> None:
        message = self.db.scalar(select(WhatsAppMessage).where(WhatsAppMessage.wa_message_id == event.payload.get("wa_message_id")))
        if not message:
            return
        poll = self.db.scalar(select(WhatsAppPoll).where(WhatsAppPoll.message_id == message.id))
        if not poll:
            return
        options = list(self.db.scalars(
            select(WhatsAppPollOption)
            .where(WhatsAppPollOption.poll_id == poll.id)
            .order_by(WhatsAppPollOption.option_index)
        ))
        votes = event.payload.get("votes", [])
        if not isinstance(votes, list):
            votes = []
        by_label = {option.label: option for option in options}
        selections: dict[str, set[int]] = {}
        for option in options:
            option.vote_count = 0
        for aggregate in votes:
            if not isinstance(aggregate, dict):
                continue
            option = by_label.get(str(aggregate.get("name", "")))
            voters = aggregate.get("voters", [])
            if not option or not isinstance(voters, list):
                continue
            unique_voters = {str(voter) for voter in voters if voter}
            option.vote_count = len(unique_voters)
            for voter in unique_voters:
                selections.setdefault(voter, set()).add(option.option_index)
        self.db.execute(delete(WhatsAppPollVote).where(WhatsAppPollVote.poll_id == poll.id))
        self.db.add_all([
            WhatsAppPollVote(
                poll_id=poll.id,
                voter_jid=voter,
                selected_option_indexes=sorted(indexes),
            )
            for voter, indexes in selections.items()
        ])
        message.metadata_json = {**message.metadata_json, "votes": votes}


class BridgeAdminClient:
    def __init__(self) -> None:
        self.base_url = settings.whatsapp_bridge_url.rstrip("/")

    def request(self, method: str, path: str) -> dict[str, Any]:
        with httpx.Client(timeout=10) as client:
            response = client.request(method, f"{self.base_url}{path}")
            response.raise_for_status()
            return response.json()
