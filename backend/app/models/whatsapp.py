from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")
INTEGER_LIST = JSON().with_variant(ARRAY(Integer), "postgresql")


class WhatsAppConnection(Base):
    __tablename__ = "whatsapp_connections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_key: Mapped[str] = mapped_column(String, unique=True, default="central")
    account_jid: Mapped[str | None] = mapped_column(String)
    display_name: Mapped[str | None] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default="disconnected")
    safe_error: Mapped[str | None] = mapped_column(Text)
    bridge_instance_id: Mapped[str | None] = mapped_column(String)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_jid: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    participant_jid: Mapped[str | None] = mapped_column(String)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list[WhatsAppMessage]] = relationship(back_populates="conversation")


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        Index("whatsapp_messages_page_idx", "conversation_id", "occurred_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_conversations.id"))
    wa_message_id: Mapped[str | None] = mapped_column(String)
    direction: Mapped[str] = mapped_column(String)
    message_type: Mapped[str] = mapped_column(String)
    sender_jid: Mapped[str | None] = mapped_column(String)
    text_content: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    quoted_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("whatsapp_messages.id"))
    quoted_wa_message_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    safe_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_DOCUMENT, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[WhatsAppConversation] = relationship(back_populates="messages")
    media: Mapped[list[WhatsAppMedia]] = relationship(back_populates="message")


class WhatsAppMedia(Base):
    __tablename__ = "whatsapp_media"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_messages.id", ondelete="CASCADE"))
    media_kind: Mapped[str] = mapped_column(String)
    storage_bucket: Mapped[str] = mapped_column(String, default="whatsapp-media")
    storage_path: Mapped[str] = mapped_column(String, unique=True)
    mime_type: Mapped[str] = mapped_column(String)
    original_filename: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped[WhatsAppMessage] = relationship(back_populates="media")


class WhatsAppMessageEvent(Base):
    __tablename__ = "whatsapp_message_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_messages.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String)
    safe_error: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsAppProcessedEvent(Base):
    __tablename__ = "whatsapp_processed_events"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsAppPoll(Base):
    __tablename__ = "whatsapp_polls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_messages.id", ondelete="CASCADE"), unique=True)
    question: Mapped[str] = mapped_column(Text)
    selectable_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsAppPollOption(Base):
    __tablename__ = "whatsapp_poll_options"
    __table_args__ = (UniqueConstraint("poll_id", "option_index"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_polls.id", ondelete="CASCADE"))
    option_index: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(Text)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)


class WhatsAppPollVote(Base):
    __tablename__ = "whatsapp_poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "voter_jid"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_polls.id", ondelete="CASCADE"))
    voter_jid: Mapped[str] = mapped_column(String)
    selected_option_indexes: Mapped[list[int]] = mapped_column(INTEGER_LIST, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WhatsAppOutbox(Base):
    __tablename__ = "whatsapp_outbox"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("whatsapp_messages.id", ondelete="CASCADE"), unique=True)
    command: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    state: Mapped[str] = mapped_column(String, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lease_owner: Mapped[str | None] = mapped_column(String)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    safe_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
