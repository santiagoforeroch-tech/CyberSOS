import pytest

from app.core.config import settings
from app.schemas.agent import AgentChatRequest
from app.services.ai_agent import chat_with_agent


@pytest.mark.anyio
async def test_agent_has_local_predetermined_flow_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Recibí un enlace falso del banco"}]))
    assert "qué ocurrió" in result.message.lower()
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


def test_agent_message_contract_rejects_unknown_roles():
    with pytest.raises(ValueError):
        AgentChatRequest(messages=[{"role": "system", "content": "no"}])
