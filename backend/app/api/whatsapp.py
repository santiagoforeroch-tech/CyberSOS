from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_admin
from app.db.session import get_db
from app.schemas.whatsapp import (
    BridgeEvent,
    Capabilities,
    ContactCommand,
    ConnectionStatus,
    ConversationSummary,
    LocationCommand,
    MediaCommand,
    MessageView,
    PollCommand,
    ReactionCommand,
    TextCommand,
)
from app.services.whatsapp import BridgeAdminClient, WhatsAppService, verify_bridge_signature
from app.services.whatsapp_storage import WhatsAppStorage


admin_router = APIRouter(prefix="/whatsapp/admin", tags=["whatsapp-admin"], dependencies=[Depends(require_admin)])
internal_router = APIRouter(prefix="/internal/whatsapp", tags=["whatsapp-internal"])


def ensure_local_admin(request: Request) -> None:
    host = request.client.host if request.client else ""
    if settings.app_env != "development" or not settings.whatsapp_admin_local or host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=404, detail="Not found")


@admin_router.get("/capabilities", response_model=Capabilities, dependencies=[Depends(ensure_local_admin)])
def capabilities() -> Capabilities:
    return Capabilities(
        admin_enabled=True,
        message_types=["text", "image", "video", "audio", "document", "sticker", "location", "contact", "poll", "reaction"],
    )


@admin_router.get("/connection", response_model=ConnectionStatus, dependencies=[Depends(ensure_local_admin)])
def connection_status() -> ConnectionStatus:
    try:
        return ConnectionStatus(**BridgeAdminClient().request("GET", "/admin/connection"))
    except httpx.HTTPError:
        return ConnectionStatus(
            state="disconnected",
            safe_error="La central local aún no está iniciada o requiere su configuración privada.",
        )


@admin_router.post("/connection/start", dependencies=[Depends(ensure_local_admin)])
def start_connection() -> dict:
    try:
        return BridgeAdminClient().request("POST", "/admin/connection/start")
    except httpx.HTTPError as error:
        raise HTTPException(503, "La central de WhatsApp no está disponible localmente.") from error


@admin_router.post("/connection/reconnect", dependencies=[Depends(ensure_local_admin)])
def reconnect() -> dict:
    try:
        return BridgeAdminClient().request("POST", "/admin/connection/reconnect")
    except httpx.HTTPError as error:
        raise HTTPException(503, "La central de WhatsApp no está disponible localmente.") from error


@admin_router.get("/connection/qr", dependencies=[Depends(ensure_local_admin)])
def qr(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return BridgeAdminClient().request("GET", "/admin/connection/qr")


@admin_router.delete("/connection/session", dependencies=[Depends(ensure_local_admin)])
def logout() -> dict:
    return BridgeAdminClient().request("DELETE", "/admin/connection/session")


@admin_router.get("/conversations", response_model=list[ConversationSummary], dependencies=[Depends(ensure_local_admin)])
def conversations(limit: int = 30, db: Session = Depends(get_db)) -> list[ConversationSummary]:
    return [ConversationSummary.model_validate(item) for item in WhatsAppService(db).list_conversations(limit)]


@admin_router.get("/conversations/{conversation_id}/messages", response_model=list[MessageView], dependencies=[Depends(ensure_local_admin)])
def messages(conversation_id: UUID, limit: int = 50, db: Session = Depends(get_db)) -> list[MessageView]:
    try:
        items = WhatsAppService(db).get_messages(conversation_id, limit)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return [MessageView.model_validate(item) for item in items]


@admin_router.post("/messages/text", response_model=MessageView, dependencies=[Depends(ensure_local_admin)])
def send_text(command: TextCommand, db: Session = Depends(get_db)) -> MessageView:
    return MessageView.model_validate(WhatsAppService(db).send_text(command))


@admin_router.post("/messages/location", response_model=MessageView, dependencies=[Depends(ensure_local_admin)])
def send_location(command: LocationCommand, db: Session = Depends(get_db)) -> MessageView:
    return MessageView.model_validate(WhatsAppService(db).send_location(command))


@admin_router.post("/messages/contact", response_model=MessageView, dependencies=[Depends(ensure_local_admin)])
def send_contact(command: ContactCommand, db: Session = Depends(get_db)) -> MessageView:
    return MessageView.model_validate(WhatsAppService(db).send_contact(command))


@admin_router.post("/messages/reaction", response_model=MessageView, dependencies=[Depends(ensure_local_admin)])
def send_reaction(command: ReactionCommand, db: Session = Depends(get_db)) -> MessageView:
    try:
        return MessageView.model_validate(WhatsAppService(db).react(command))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@admin_router.post("/messages/poll", response_model=MessageView, dependencies=[Depends(ensure_local_admin)])
def send_poll(command: PollCommand, db: Session = Depends(get_db)) -> MessageView:
    try:
        return MessageView.model_validate(WhatsAppService(db).send_poll(command))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@admin_router.post("/messages/media", response_model=MessageView, dependencies=[Depends(ensure_local_admin)])
async def send_media(
    recipient: str = Form(...),
    media_kind: str = Form(...),
    caption: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> MessageView:
    if media_kind not in {"image", "video", "audio", "document", "sticker"}:
        raise HTTPException(status_code=422, detail="Tipo de medio no soportado")
    try:
        stored = await WhatsAppStorage().upload(file, conversation_key=recipient)
        command = MediaCommand(
            recipient=recipient,
            media_kind=media_kind,  # type: ignore[arg-type]
            storage_path=stored["storage_path"],
            mime_type=stored["mime_type"],
            caption=caption,
        )
        return MessageView.model_validate(WhatsAppService(db).send_media(command))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@internal_router.post("/events", status_code=202)
async def bridge_event(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    raw = await request.body()
    if not verify_bridge_signature(
        raw,
        request.headers.get("X-WhatsApp-Timestamp"),
        request.headers.get("X-WhatsApp-Signature"),
    ):
        raise HTTPException(status_code=401, detail="Firma inválida")
    event = BridgeEvent.model_validate_json(raw)
    WhatsAppService(db).process_bridge_event(event)
    return {"accepted": True}
