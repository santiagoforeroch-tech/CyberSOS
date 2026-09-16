import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import AgentConversation, AgentMessage
from app.schemas.agent import AgentChatRequest
from app.schemas.reports import ReportCreate
from app.services.ai_agent import chat_with_agent
from app.services.reports import create_report

router = APIRouter(prefix="/v1/telegram", tags=["telegram"])

async def _send_message(chat_id: int, text: str) -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("Telegram no está configurado")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage", json={"chat_id": chat_id, "text": text})
        response.raise_for_status()

@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db), secret_header: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token")) -> dict:
    if not settings.telegram_enabled:
        raise HTTPException(status_code=404, detail="Telegram no está habilitado")
    if settings.telegram_webhook_secret and secret_header != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook no autorizado")
    update = await request.json()
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return {"ok": True}
    external_key = f"telegram:{chat_id}"
    conversation = db.execute(select(AgentConversation).where(AgentConversation.external_key == external_key)).scalar_one_or_none()
    if text.lower() in {"/start", "/reiniciar", "/restart"}:
        if conversation:
            conversation.status = "open"
            conversation.report_id = None
            conversation.draft = {}
        else:
            conversation = AgentConversation(external_key=external_key)
            db.add(conversation)
            db.flush()
        reply = "Hola. Soy el asistente de CyberSOS. Cuéntame qué ocurrió y te ayudaré a preparar un reporte. No compartas contraseñas ni códigos."
        db.add(AgentMessage(conversation_id=conversation.id, role="assistant", content=reply))
        db.commit()
        await _send_message(chat_id, reply)
        return {"ok": True}
    if not conversation:
        conversation = AgentConversation(external_key=external_key)
        db.add(conversation)
        db.flush()
    if text.lower() in {"cancelar", "/cancelar", "cancel"}:
        conversation.status = "abandoned"
        db.commit()
        await _send_message(chat_id, "De acuerdo, no enviaré ningún reporte. Puedes escribir /start cuando quieras comenzar de nuevo.")
        return {"ok": True}
    db.add(AgentMessage(conversation_id=conversation.id, role="user", content=text))
    db.flush()
    history = db.execute(select(AgentMessage).where(AgentMessage.conversation_id == conversation.id).order_by(AgentMessage.created_at)).scalars().all()
    result = await chat_with_agent(AgentChatRequest(conversation_id=conversation.id, messages=[{"role": item.role, "content": item.content} for item in history]))
    conversation.draft = result.draft.model_dump()
    reply = result.message
    if result.ready_to_confirm:
        reply += "\n\nSi el resumen es correcto, responde CONFIRMAR. Para empezar de nuevo, escribe /start."
    db.add(AgentMessage(conversation_id=conversation.id, role="assistant", content=reply))
    db.commit()
    if text.upper() == "CONFIRMAR" and result.draft.category:
        username = (message.get("from") or {}).get("username") or f"Usuario de Telegram {chat_id}"
        report = create_report(db, ReportCreate(category=result.draft.category, description=result.draft.summary or "Reporte recibido por Telegram.", channel="Telegram", related_information={"telegram_chat_id": str(chat_id), "facts": result.draft.facts}, reporter_name=username[:160], contact_type="phone", contact_value=str(chat_id)), source="telegram")
        conversation.status = "confirmed"
        conversation.report_id = report.id
        db.commit()
        reply = f"Tu reporte fue registrado correctamente. Número de caso: {report.case_number}. Quedará para revisión humana."
        db.add(AgentMessage(conversation_id=conversation.id, role="assistant", content=reply))
        db.commit()
    await _send_message(chat_id, reply)
    return {"ok": True}
