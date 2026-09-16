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
        {"role": "user", "content": "La consecuencia fue perder dinero y me preocupa que vuelvan a contactarme"},
        {"role": "user", "content": "Contacté al banco y bloqueé la cuenta"},
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
    assert "consecuencia" in second.message.lower()
    assert account.draft.category == "robo o acceso no autorizado a cuenta"
    assert "contraseña" in account.message.lower()


def test_agent_message_contract_rejects_unknown_roles():
    with pytest.raises(ValueError):
        AgentChatRequest(messages=[{"role": "system", "content": "no"}])


@pytest.mark.anyio
async def test_local_agent_answers_general_questions_without_stalling(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", True)
    result = await chat_with_agent(AgentChatRequest(messages=[
        {"role": "user", "content": "¿Cómo funciona CyberSOS?"},
    ]))
    assert "borrador" in result.message.lower()
    assert result.draft.category is None


@pytest.mark.anyio
@pytest.mark.parametrize(("text", "category"), [
    ("Compre algo por internet y nunca llego", "fraude/estafa digital"),
    ("Hay un perfil falso usando mis fotos", "suplantación"),
    ("Me sacaron de mi cuenta y cambiaron la contraseña", "robo o acceso no autorizado a cuenta"),
    ("Publicaron mis documentos personales", "robo de información"),
    ("Me escriben sin parar y me intimidan", "amenaza/acoso digital"),
    ("Me están chantajeando con publicar mis fotos", "extorsión cibernética"),
    ("Un virus bloqueó mis archivos", "malware"),
])
async def test_local_agent_recognizes_every_main_incident_category(monkeypatch, text, category):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", True)
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": text}]))
    assert result.draft.category == category


@pytest.mark.anyio
async def test_local_agent_prioritizes_physical_emergency(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", True)
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "Estoy en peligro físico"}]))
    assert "emergencias" in result.message.lower()


@pytest.mark.anyio
async def test_local_agent_explains_report_lifecycle(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_enabled", False)
    monkeypatch.setattr(settings, "ai_local_mode", True)
    result = await chat_with_agent(AgentChatRequest(messages=[{"role": "user", "content": "¿Cuándo recibo mi número de caso?"}]))
    assert "confirmar" in result.message.lower()
    assert "borrador" in result.message.lower()
