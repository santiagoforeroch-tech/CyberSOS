import pytest

from app.core.config import settings
from app.schemas.agent import AgentChatRequest
from app.services.ai_agent import chat_with_agent


@pytest.mark.anyio
async def test_agent_has_local_predetermined_flow_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Recibí un enlace falso del banco"}]))
    assert "phishing" in result.message.lower()
    assert "correo, sms, whatsapp" in result.message.lower()
    assert result.draft.category == "phishing"
    assert result.draft.needs_human_review is True


@pytest.mark.anyio
async def test_local_agent_organizes_report_after_two_messages(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = await chat_with_agent(AgentChatRequest(messages=[
        {"role": "user", "content": "Me hicieron una estafa y perdí dinero"},
        {"role": "user", "content": "Ocurrió ayer por WhatsApp; tengo capturas"},
    ]))
    assert result.ready_to_confirm is True
    assert result.draft.category == "fraude/estafa digital"
    assert result.draft.priority == "Alta"


@pytest.mark.anyio
async def test_local_agent_varies_follow_up_by_incident_and_conversation_step(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", True)

    first = await chat_with_agent(AgentChatRequest(messages=[
        {"role": "user", "content": "Me llegó un mensaje sospechoso que pide datos bancarios"},
    ]))
    second = await chat_with_agent(AgentChatRequest(messages=[
        {"role": "user", "content": "Me llegó un mensaje sospechoso que pide datos bancarios"},
        {"role": "user", "content": "Fue ayer por WhatsApp"},
    ]))
    account = await chat_with_agent(AgentChatRequest(messages=[
        {"role": "user", "content": "No puedo entrar a mi cuenta de Instagram"},
    ]))

    assert first.draft.category == "phishing"
    assert "whatsapp" in first.message.lower()
    assert "borrador" in second.message.lower()
    assert account.draft.category == "robo o acceso no autorizado a cuenta"
    assert "contraseña" in account.message.lower()


def test_agent_message_contract_rejects_unknown_roles():
    with pytest.raises(ValueError):
        AgentChatRequest(messages=[{"role": "system", "content": "no"}])
