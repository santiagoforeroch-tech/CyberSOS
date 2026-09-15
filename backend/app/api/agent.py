from fastapi import APIRouter, HTTPException

from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.ai_agent import chat_with_agent

router = APIRouter(prefix="/v1/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest) -> AgentChatResponse:
    try:
        result = await chat_with_agent(payload)
        return result
    except Exception as error:
        raise HTTPException(status_code=503, detail="El asistente no está disponible en este momento. Usa el formulario guiado o inténtalo más tarde.") from error
