import pytest

from app.core.config import settings
from app.schemas.agent import AgentChatRequest
from app.services import ai_agent
from app.services.ai_agent import _local_chat, chat_with_agent


@pytest.mark.parametrize("category, message", [
    ("phishing", "Me llegó un enlace falso del banco"),
    ("fraude/estafa digital", "Me estafaron y perdí dinero"),
    ("suplantación", "Crearon un perfil falso con mi foto"),
    ("robo o acceso no autorizado a cuenta", "Hackearon mi cuenta"),
    ("robo de información", "Publicaron mis datos personales"),
    ("amenaza/acoso digital", "Me están acosando y escriben sin parar"),
    ("extorsión cibernética", "Me chantajean con publicar mis fotos"),
    ("malware", "Mi computador tiene un virus y bloqueó mis archivos"),
])
def test_local_agent_recognizes_each_incident_category(category, message):
    result = _local_chat(AgentChatRequest(messages=[{"role": "user", "content": message}]))
    assert result.draft.category == category
    assert result.message


@pytest.mark.anyio
async def test_agent_uses_safe_local_fallback_without_gemini(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Necesito reportar un caso"}]))
    assert result.message
    assert result.draft.needs_human_review is True


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


@pytest.mark.anyio
async def test_agent_falls_back_when_gemini_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")

    class FailingClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            raise TimeoutError("provider unavailable")

    monkeypatch.setattr(ai_agent.httpx, "AsyncClient", lambda **kwargs: FailingClient())
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Me hackearon la cuenta"}]))
    assert result.draft.category == "robo o acceso no autorizado a cuenta"
    assert result.message


@pytest.mark.anyio
async def test_agent_prioritizes_extortion_over_general_threat(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Me amenazan con publicar mis fotos y me exigen dinero"}]))
    assert result.draft.category == "extorsión cibernética"


def test_agent_message_contract_rejects_unknown_roles():
    with pytest.raises(ValueError):
        AgentChatRequest(messages=[{"role": "system", "content": "no"}])
