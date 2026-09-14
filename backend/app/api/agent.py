from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import AgentConversation, AgentMessage

from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.ai_agent import chat_with_agent

router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest, db: Session = Depends(get_db)) -> AgentChatResponse:
    try:
        conversation = db.get(AgentConversation, payload.conversation_id) if payload.conversation_id else AgentConversation()
        if conversation is None:
            raise HTTPException(status_code=404, detail="La conversación no existe")
        if not conversation.id:
            db.add(conversation); db.flush()
        conversation.messages.clear()
        for item in payload.messages:
            db.add(AgentMessage(conversation_id=conversation.id, role=item.role, content=item.content))
        result = await chat_with_agent(payload)
        conversation.draft = result.draft.model_dump(); db.commit()
        result.conversation_id = conversation.id
        return result
    except Exception as error:
        raise HTTPException(status_code=503, detail="El asistente no está disponible en este momento. Usa el formulario guiado o inténtalo más tarde.") from error
