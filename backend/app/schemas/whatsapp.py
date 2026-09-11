from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


MessageType = Literal[
    "text", "image", "video", "audio", "document", "sticker",
    "location", "contact", "poll", "reaction", "unknown",
]


class ConnectionStatus(BaseModel):
    state: str
    account_jid: str | None = None
    display_name: str | None = None
    safe_error: str | None = None


class ConversationSummary(BaseModel):
    id: UUID
    chat_jid: str
    kind: Literal["direct", "group"]
    title: str | None
    last_message_at: datetime | None

    model_config = {"from_attributes": True}


class MessageView(BaseModel):
    id: UUID
    conversation_id: UUID
    wa_message_id: str | None
    direction: Literal["inbound", "outbound"]
    message_type: MessageType
    sender_jid: str | None
    text_content: str | None
    caption: str | None
    quoted_message_id: UUID | None
    status: str
    metadata_json: dict[str, Any]
    occurred_at: datetime

    model_config = {"from_attributes": True}


class TextCommand(BaseModel):
    recipient: str
    text: str = Field(min_length=1, max_length=4096)
    quoted_message_id: UUID | None = None

    @field_validator("recipient")
    @classmethod
    def recipient_is_valid(cls, value: str) -> str:
        compact = value.strip().replace("+", "").replace(" ", "")
        if "@" not in compact and not compact.isdigit():
            raise ValueError("El destinatario debe ser un teléfono o JID válido")
        return compact


class LocationCommand(BaseModel):
    recipient: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)


class PollCommand(BaseModel):
    recipient: str
    question: str = Field(min_length=1, max_length=255)
    options: list[str] = Field(min_length=2, max_length=12)
    selectable_count: int = Field(default=1, ge=1)

    @field_validator("options")
    @classmethod
    def options_are_unique(cls, value: list[str]) -> list[str]:
        clean = [option.strip() for option in value]
        if any(not option for option in clean) or len(set(clean)) != len(clean):
            raise ValueError("Las opciones deben ser únicas y no vacías")
        return clean


class MediaCommand(BaseModel):
    recipient: str
    media_kind: Literal["image", "video", "audio", "document", "sticker"]
    storage_path: str = Field(min_length=1, max_length=1024)
    mime_type: str = Field(min_length=3, max_length=200)
    caption: str | None = Field(default=None, max_length=4096)
    quoted_message_id: UUID | None = None


class ContactCommand(BaseModel):
    recipient: str
    display_name: str = Field(min_length=1, max_length=200)
    vcard: str = Field(min_length=1, max_length=8192)


class ReactionCommand(BaseModel):
    message_id: UUID
    emoji: str = Field(min_length=0, max_length=16)


class BridgeEvent(BaseModel):
    event_id: UUID
    event_type: str
    occurred_at: datetime
    payload: dict[str, Any]


class Capabilities(BaseModel):
    admin_enabled: bool
    message_types: list[str]
