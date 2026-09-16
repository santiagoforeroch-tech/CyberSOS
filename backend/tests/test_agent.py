import pytest

from app.core.config import settings
from app.schemas.agent import AgentChatRequest
from app.services import ai_agent
from app.services.ai_agent import chat_with_agent


@pytest.mark.anyio
async def test_agent_requires_gemini_and_never_uses_local_flow(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(RuntimeError, match="Gemini no está configurado"):
        await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Necesito reportar un caso"}]))


@pytest.mark.anyio
async def test_agent_uses_gemini_response(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", True)
    monkeypatch.setattr(settings, "ai_local_mode", False)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": '{"message":"Entiendo lo ocurrido. ¿Cuándo pasó y en qué aplicación?","draft":{"category":"phishing","priority":"Alta","summary":"Mensaje sospechoso","facts":["Mensaje sospechoso"],"missing_information":["Fecha y canal"],"evidence_requested":["Capturas"],"needs_human_review":true},"ready_to_confirm":false}'}]}}]}

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(ai_agent.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Me llegó un enlace sospechoso"}]))
    assert result.message.startswith("Entiendo")
    assert result.draft.category == "phishing"
    assert result.ready_to_confirm is False


def test_agent_message_contract_rejects_unknown_roles():
    with pytest.raises(ValueError):
        AgentChatRequest(messages=[{"role": "system", "content": "no"}])
