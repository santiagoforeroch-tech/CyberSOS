import json

import httpx

from app.core.config import settings
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentDraft


SYSTEM_PROMPT = """Eres el agente ciudadano de CyberSOS en Colombia. Ayudas a describir incidentes digitales y preparar un reporte para revisión humana. Responde en español sencillo, con empatía y sin culpar. Puedes contestar preguntas generales de seguridad digital, pero no des asesoría legal definitiva. Nunca pidas contraseñas, códigos MFA, números completos de tarjetas ni dinero. Si hay peligro físico o una emergencia, indica contactar inmediatamente a emergencias y continúa solo si la persona lo desea.

Analiza la conversación y devuelve JSON válido con estas claves: message (respuesta natural), draft (category usando exactamente una categoría válida o null, priority entre Baja/Media/Alta/Crítica, summary, facts, missing_information, evidence_requested, needs_human_review), ready_to_confirm (true solo cuando haya descripción suficiente y datos de contacto confirmados). No inventes hechos. Categorías válidas: phishing, fraude/estafa digital, suplantación, robo o acceso no autorizado a cuenta, robo de información, amenaza/acoso digital, extorsión cibernética, malware, otro."""


async def chat_with_agent(payload: AgentChatRequest) -> AgentChatResponse:
    if settings.ai_provider == "openai":
        return await _chat_openai(payload)
    if not settings.ai_agent_enabled or not settings.gemini_api_key:
        return AgentChatResponse(
            message="El asistente IA está pendiente de configuración. Mientras tanto, puedes usar el formulario guiado para registrar tu caso.",
            draft=AgentDraft(),
        )
    contents = [{"role": "user" if item.role == "user" else "model", "parts": [{"text": item.content}]} for item in payload.messages[-settings.ai_agent_max_history_messages:]]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    body = {"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]}, "contents": contents, "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers={"x-goog-api-key": settings.gemini_api_key}, json=body)
        response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    return AgentChatResponse.model_validate(result)


async def _chat_openai(payload: AgentChatRequest) -> AgentChatResponse:
    if not settings.ai_agent_enabled or not settings.openai_api_key:
        return AgentChatResponse(message="El asistente IA está pendiente de configuración. Mientras tanto, puedes usar el formulario guiado.", draft=AgentDraft())
    input_items = [{"role": item.role, "content": item.content} for item in payload.messages[-settings.ai_agent_max_history_messages:]]
    body = {"model": settings.openai_model, "instructions": SYSTEM_PROMPT, "input": input_items, "store": False, "text": {"format": {"type": "json_object"}}}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {settings.openai_api_key}"}, json=body)
        response.raise_for_status()
    data = response.json()
    text = data.get("output_text")
    if not text:
        text = next(part["text"] for item in data.get("output", []) for part in item.get("content", []) if part.get("type") == "output_text")
    return AgentChatResponse.model_validate(json.loads(text))
