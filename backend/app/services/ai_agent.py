import json

import httpx

from app.core.config import settings
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentDraft


SYSTEM_PROMPT = """Eres el agente ciudadano de CyberSOS en Colombia. Ayudas a describir incidentes digitales y preparar un reporte para revisión humana. Responde en español sencillo, con empatía y sin culpar. Puedes contestar preguntas generales de seguridad digital, pero no des asesoría legal definitiva. Nunca pidas contraseñas, códigos MFA, números completos de tarjetas ni dinero. Si hay peligro físico o una emergencia, indica contactar inmediatamente a emergencias y continúa solo si la persona lo desea.

Analiza la conversación y devuelve JSON válido con estas claves: message (respuesta natural), draft (category usando exactamente una categoría válida o null, priority entre Baja/Media/Alta/Crítica, summary, facts, missing_information, evidence_requested, needs_human_review), ready_to_confirm (true solo cuando haya descripción suficiente y datos de contacto confirmados). No inventes hechos. Categorías válidas: phishing, fraude/estafa digital, suplantación, robo o acceso no autorizado a cuenta, robo de información, amenaza/acoso digital, extorsión cibernética, malware, otro."""


KEYWORDS = {
    "phishing": ("phishing", "enlace falso", "link falso", "mensaje falso", "mensaje sospechoso", "correo sospechoso", "correo raro", "sms sospechoso", "whatsapp sospechoso", "pide datos", "pide mis datos", "datos bancarios", "clave bancaria", "premio falso", "banco falso", "robaron mi clave"),
    "fraude/estafa digital": ("estafa", "fraude", "me engañaron", "perdí dinero", "perdi dinero", "transferencia", "pago", "consignación", "consignacion", "venta falsa", "inversión falsa", "inversion falsa", "cobro falso", "tienda falsa", "oferta falsa"),
    "suplantación": ("suplant", "perfil falso", "se hacen pasar", "identidad falsa", "cuenta falsa", "clonaron mi perfil", "usaron mi foto", "fingiendo ser"),
    "robo o acceso no autorizado a cuenta": ("hackearon", "hackeada", "hackeado", "entraron a mi cuenta", "perdí el acceso", "perdi el acceso", "me robaron whatsapp", "sesión desconocida", "sesion desconocida", "cambiaron mi contraseña", "cambiaron mi contrasena", "no puedo entrar", "me sacaron de"),
    "robo de información": ("robaron mis datos", "publicaron mis datos", "documentos", "filtraron", "filtración", "filtracion", "datos personales", "fotos privadas", "información confidencial", "informacion confidencial"),
    "amenaza/acoso digital": ("amenaza", "acoso", "insultan", "intimidan", "persiguen", "hostigamiento", "mensajes repetidos", "me molestan", "me están acosando", "me estan acosando"),
    "extorsión cibernética": ("extorsión", "extorsion", "chantaje", "me exigen dinero", "piden dinero", "no divulgar", "amenazan con publicar", "publicar mis fotos", "difundir mis fotos"),
    "malware": ("virus", "malware", "ransomware", "bloqueó mis archivos", "bloqueo mis archivos", "archivo malicioso", "aplicación extraña", "aplicacion extraña", "computador infectado", "celular infectado", "pantalla bloqueada"),
}

FOLLOW_UPS = {
    "phishing": ("Esto parece un intento de phishing. No abras enlaces ni compartas datos; entra al sitio oficial escribiendo la dirección manualmente. ¿Te llegó por correo, SMS, WhatsApp o una red social?", "Para conservar la evidencia, ¿guardaste el mensaje, el enlace y el nombre o número del remitente?"),
    "fraude/estafa digital": ("Lamento que te haya ocurrido. Contacta al banco o plataforma por su canal oficial si hubo un pago. ¿Qué ofrecían, por qué medio hablaste y en qué fecha ocurrió?", "¿Conservas comprobantes de pago, conversación, perfil, enlace o número de cuenta usado?"),
    "suplantación": ("Parece una posible suplantación. Guarda el enlace o nombre del perfil falso y avisa a tus contactos por otro medio. ¿En qué red o aplicación apareció?", "¿La persona está usando tu nombre, fotos, número o pidiendo dinero a tus contactos?"),
    "robo o acceso no autorizado a cuenta": ("Entiendo. Cambia la contraseña desde un dispositivo confiable y cierra sesiones abiertas si todavía puedes acceder. ¿Qué cuenta fue afectada y cuándo notaste el acceso?", "¿Recibiste avisos de inicio de sesión, cambios de contraseña o mensajes enviados sin tu permiso?"),
    "robo de información": ("Tomemos esto con calma. Conserva capturas y evita borrar mensajes o archivos relacionados. ¿Qué tipo de información fue expuesta y dónde la viste publicada o compartida?", "¿Tienes el enlace, capturas o el nombre del perfil, sitio o persona que compartió la información?"),
    "amenaza/acoso digital": ("Siento que estés pasando por esto. No respondas bajo presión y conserva todas las pruebas. ¿La amenaza menciona un daño físico, información privada o contacto fuera de internet?", "¿Puedes indicar la plataforma, fecha aproximada y el usuario o número desde el que llegó?"),
    "extorsión cibernética": ("No pagues ni envíes más información. Guarda las conversaciones y contacta a las autoridades si hay peligro inmediato. ¿Qué te están exigiendo y por cuál canal te contactaron?", "¿Conservas capturas, el número o perfil, solicitudes de pago y la fecha de los mensajes?"),
    "malware": ("Desconecta el dispositivo de internet si notas actividad extraña y no ingreses más contraseñas. ¿Qué ocurrió: archivo bloqueado, ventana extraña, cobro o aplicación desconocida?", "¿Recuerdas qué archivo, enlace o aplicación abriste antes del problema y tienes alguna captura del aviso?"),
}


def _local_chat(payload: AgentChatRequest) -> AgentChatResponse:
    """Flujo determinista para desarrollo: no usa red ni claves de proveedor."""
    text = " ".join(item.content for item in payload.messages if item.role == "user").lower()
    category = next((name for name, words in KEYWORDS.items() if any(word in text for word in words)), None)
    priority = "Crítica" if any(word in text for word in ("peligro", "amenaza física", "extorsión", "chantaje")) else "Alta" if any(word in text for word in ("perdí dinero", "hackearon", "bloqueó")) else "Media"
    facts = [item.content.strip() for item in payload.messages if item.role == "user" and item.content.strip()][-5:]
    missing = []
    if not category:
        missing.append("Tipo de incidente o qué ocurrió")
    if len(facts) < 2:
        missing.append("Cuándo ocurrió y por qué canal o aplicación")
    if not any(word in text for word in ("captura", "evidencia", "pantallazo", "enlace", "archivo")):
        missing.append("Si conservas capturas, enlaces, archivos o nombres de usuario")
    ready = bool(category and len(facts) >= 2)
    if ready:
        message = "Ya organicé lo que me contaste en un borrador. Revisa el resumen, agrega un medio de contacto y confirma solo si representa correctamente tu caso."
    elif category:
        first_question, evidence_question = FOLLOW_UPS[category]
        message = first_question if len(facts) == 1 else evidence_question
    else:
        message = "Gracias por contarme. Para orientarte mejor, dime qué pasó: ¿recibiste un mensaje, perdiste una cuenta, hubo un cobro, publicaron información o te amenazaron? No compartas contraseñas ni códigos."
    return AgentChatResponse(message=message, draft=AgentDraft(category=category, priority=priority, summary=" ".join(facts), facts=facts, missing_information=missing, evidence_requested=["Capturas, enlaces o archivos relacionados"], needs_human_review=True), ready_to_confirm=ready)


async def chat_with_agent(payload: AgentChatRequest) -> AgentChatResponse:
    # El MVP funciona sin claves externas. Los proveedores solo se usan cuando
    # el modo local se desactiva expresamente en una configuración privada.
    if settings.ai_local_mode or not settings.ai_agent_enabled or (not settings.gemini_api_key and not settings.openai_api_key):
        return _local_chat(payload)
    if settings.ai_provider == "openai":
        return await _chat_openai(payload)
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
