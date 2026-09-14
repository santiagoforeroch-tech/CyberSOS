import pytest

from app.core.config import settings
from app.schemas.agent import AgentChatRequest
from app.services.ai_agent import chat_with_agent


@pytest.mark.anyio
async def test_agent_has_safe_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Me pasó algo en internet"}]))
    assert "formulario" in result.message.lower()
    assert result.draft.needs_human_review is True


def test_agent_message_contract_rejects_unknown_roles():
    with pytest.raises(ValueError):
        AgentChatRequest(messages=[{"role": "system", "content": "no"}])
