import json

import httpx

from app.core.config import settings
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentDraft
from app.schemas.reports import CATEGORIES


SYSTEM_PROMPT = """Eres el agente ciudadano de CyberSOS en Colombia. Ayudas a describir incidentes digitales y preparar un reporte para revisión humana. Responde en español sencillo, con empatía y sin culpar. Puedes contestar preguntas generales de seguridad digital, pero no des asesoría legal definitiva. Nunca pidas contraseñas, códigos MFA, números completos de tarjetas ni dinero. Si hay peligro físico o una emergencia, indica contactar inmediatamente a emergencias y continúa solo si la persona lo desea.

Analiza la conversación y devuelve JSON válido con estas claves: message (respuesta natural y empática), draft (category usando exactamente una categoría válida o null, priority entre Baja/Media/Alta/Crítica, summary, facts, missing_information, evidence_requested, needs_human_review), ready_to_confirm (true solo después de comprender qué ocurrió, cuándo y por qué canal, el impacto, las acciones realizadas y las evidencias; nunca cierres la entrevista tras una o dos respuestas). Haz una sola pregunta clara por turno, reconoce primero lo que la persona acaba de contar y no repitas preguntas ya respondidas. No inventes hechos. Categorías válidas: phishing, fraude/estafa digital, suplantación, robo o acceso no autorizado a cuenta, robo de información, amenaza/acoso digital, extorsión cibernética, malware, otro."""


KEYWORDS = {
    "phishing": ("phishing", "enlace falso", "link falso", "enlace extraño", "mensaje falso", "mensaje sospechoso", "correo sospechoso", "correo raro", "sms sospechoso", "whatsapp sospechoso", "pide datos", "pide mis datos", "datos bancarios", "clave bancaria", "premio falso", "banco falso", "robaron mi clave", "sitio clon"),
    "fraude/estafa digital": ("estafa", "estafaron", "fraude", "me engañaron", "me tumbaron", "perdí dinero", "perdi dinero", "transferencia", "pago", "consignación", "consignacion", "venta falsa", "inversión falsa", "inversion falsa", "cobro falso", "tienda falsa", "oferta falsa", "compré y no llegó", "compre y no llego", "nunca llego", "nunca llegó"),
    "suplantación": ("suplant", "perfil falso", "se hacen pasar", "identidad falsa", "cuenta falsa", "clonaron mi perfil", "usaron mi foto", "fingiendo ser", "se hacen pasar por mí", "se hacen pasar por mi"),
    "robo o acceso no autorizado a cuenta": ("hackearon", "hackeada", "hackeado", "entraron a mi cuenta", "perdí el acceso", "perdi el acceso", "me robaron whatsapp", "sesión desconocida", "sesion desconocida", "cambiaron mi contraseña", "cambiaron mi contrasena", "no puedo entrar", "me sacaron de"),
    "robo de información": ("robaron mis datos", "publicaron mis datos", "documentos", "filtraron", "filtración", "filtracion", "datos personales", "fotos privadas", "información confidencial", "informacion confidencial"),
    "amenaza/acoso digital": ("amenaza", "acoso", "insultan", "intimidan", "persiguen", "hostigamiento", "mensajes repetidos", "me molestan", "me están acosando", "me estan acosando", "me escriben sin parar", "me difaman"),
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

GENERAL_ANSWERS = {
    "hola": "Hola. Soy el orientador de CyberSOS. Cuéntame con tus palabras qué ocurrió y te ayudaré a organizarlo. No compartas contraseñas ni códigos.",
    "buenas": "Hola. Soy el orientador de CyberSOS. Cuéntame con tus palabras qué ocurrió y te ayudaré a organizarlo. No compartas contraseñas ni códigos.",
    "gracias": "Con gusto. Si recuerdas otro detalle, puedes añadirlo. Cuando el borrador esté listo, podrás revisarlo antes de enviarlo.",
    "adiós": "Está bien. Conserva las evidencias y evita responder bajo presión. Puedes volver cuando te sientas preparado.",
    "adios": "Está bien. Conserva las evidencias y evita responder bajo presión. Puedes volver cuando te sientas preparado.",
    "qué es cybersos": "CyberSOS es un canal institucional para orientar y recibir ciberdenuncias. Te ayuda a ordenar lo ocurrido; una persona revisa el reporte antes de tomar decisiones.",
    "como funciona": "Puedes contarme qué pasó sin compartir contraseñas ni códigos. Te haré preguntas sencillas, organizaré un borrador y tú decides si quieres enviarlo para revisión humana.",
    "cómo funciona": "Puedes contarme qué pasó sin compartir contraseñas ni códigos. Te haré preguntas sencillas, organizaré un borrador y tú decides si quieres enviarlo para revisión humana.",
    "qué hago": "Primero protege tus cuentas desde un dispositivo confiable, no respondas bajo presión y conserva capturas, enlaces y fechas. Cuéntame qué ocurrió para orientarte mejor.",
    "es seguro": "No compartas aquí contraseñas, códigos MFA, números completos de tarjetas ni dinero. El chatbot solo organiza la información y el reporte queda sujeto a revisión humana.",
    "contraseña": "No me envíes tu contraseña. Si sospechas que fue comprometida, cámbiala desde el sitio oficial, activa la verificación disponible y cierra sesiones desconocidas.",
    "código": "No compartas códigos de verificación conmigo ni con nadie. Si recibiste un código que no solicitaste, cambia la contraseña desde la aplicación oficial y revisa las sesiones abiertas.",
    "policía": "Si existe peligro físico, amenazas inmediatas o riesgo para una persona, contacta a emergencias o a la autoridad local. También puedes conservar las pruebas y continuar aquí si te sientes seguro.",
    "datos personales": "No compartas aquí tu número de documento, dirección, contraseña ni códigos. Para el reporte solo necesitaremos la información mínima de contacto cuando decidas confirmarlo.",
    "anónimo": "Puedes pedir orientación sin compartir secretos. Para enviar un reporte, el sistema solicita un medio de contacto para que la institución pueda hacer seguimiento; revisa esos datos antes de confirmar.",
    "anonimo": "Puedes pedir orientación sin compartir secretos. Para enviar un reporte, el sistema solicita un medio de contacto para que la institución pueda hacer seguimiento; revisa esos datos antes de confirmar.",
    "qué información": "Cuéntame qué pasó, cuándo, por qué aplicación o canal, quién estuvo involucrado y qué consecuencia tuvo. Las capturas, enlaces, archivos y nombres de usuario ayudan, pero no envíes contraseñas ni códigos.",
    "que información": "Cuéntame qué pasó, cuándo, por qué aplicación o canal, quién estuvo involucrado y qué consecuencia tuvo. Las capturas, enlaces, archivos y nombres de usuario ayudan, pero no envíes contraseñas ni códigos.",
    "qué pasa después": "Después de confirmar, recibirás un número de caso. El reporte queda para revisión humana; conserva tus evidencias y no respondas bajo presión a la persona involucrada.",
    "que pasa despues": "Después de confirmar, recibirás un número de caso. El reporte queda para revisión humana; conserva tus evidencias y no respondas bajo presión a la persona involucrada.",
    "cuánto tarda": "El tiempo de respuesta depende de la institución y del tipo de incidente. El chatbot no puede prometer un plazo, pero el número de caso permite identificar el reporte enviado.",
    "cuanto tarda": "El tiempo de respuesta depende de la institución y del tipo de incidente. El chatbot no puede prometer un plazo, pero el número de caso permite identificar el reporte enviado.",
    "puedo enviar": "Puedes describir el incidente y mencionar qué evidencias conservas. No envíes contraseñas, códigos MFA, números completos de tarjeta, dinero ni datos de otras personas que no sean necesarios.",
    "quiero reportar": "Claro. Comencemos por lo principal: cuéntame qué ocurrió, sin incluir contraseñas ni códigos. Luego organizaremos fecha, canal, impacto y evidencias.",
    "necesito reportar": "Claro. Comencemos por lo principal: cuéntame qué ocurrió, sin incluir contraseñas ni códigos. Luego organizaremos fecha, canal, impacto y evidencias.",
    "número de caso": "El número de caso se genera únicamente después de confirmar y enviar el borrador. Antes de enviarlo podrás revisar la categoría, el resumen y los datos de contacto.",
    "numero de caso": "El número de caso se genera únicamente después de confirmar y enviar el borrador. Antes de enviarlo podrás revisar la categoría, el resumen y los datos de contacto.",
    "estado de mi caso": "Para consultar el estado se necesita el número de caso y el mecanismo institucional habilitado. Si aún no has confirmado el reporte, primero revisa y envía el borrador desde este chat.",
    "agregar evidencia": "Puedes indicar qué evidencia conservas, como capturas, enlaces, archivos, recibos o nombres de usuario. No adjuntes contraseñas, códigos ni información innecesaria de terceros.",
    "corregir": "Puedes corregir el relato antes de confirmar. Dime qué dato está mal y cuál es la versión correcta; conservaré solo la información necesaria para el borrador.",
    "cancelar": "De acuerdo, no enviaré ningún reporte. Si ya guardaste evidencias, consérvalas en un lugar seguro y evita responder bajo presión.",
    "borrar": "Si quieres abandonar este borrador, puedes cerrar la conversación. No compartas más datos; para solicitar eliminación de un reporte ya enviado, usa el canal institucional correspondiente.",
    "confirmar reporte": "Antes de confirmar revisa que el resumen sea correcto, que el medio de contacto esté bien escrito y que no incluya secretos. La confirmación envía el caso a revisión humana.",
    "qué datos": "Para el reporte necesitamos el relato de los hechos, fecha aproximada, canal o aplicación, impacto, evidencias disponibles y un medio de contacto. No necesitamos contraseñas ni códigos.",
    "que datos": "Para el reporte necesitamos el relato de los hechos, fecha aproximada, canal o aplicación, impacto, evidencias disponibles y un medio de contacto. No necesitamos contraseñas ni códigos.",
}

URGENT_WORDS = ("me van a matar", "peligro físico", "peligro inmediato", "están en mi casa", "secuestro", "emergencia", "me persiguen")
OTHER_INCIDENT_WORDS = ("problema en internet", "incidente digital", "algo raro", "me pasó algo", "me paso algo", "no sé qué hacer", "no se que hacer", "me contactaron", "recibí algo", "recibi algo", "mi información", "mi informacion")


def _local_chat(payload: AgentChatRequest) -> AgentChatResponse:
    """Flujo determinista para desarrollo: no usa red ni claves de proveedor."""
    text = " ".join(item.content for item in payload.messages if item.role == "user").lower()
    # La extorsión es más específica que una amenaza general: priorizarla
    # evita clasificar como acoso los casos que exigen dinero o chantaje.
    extortion_markers = ("extorsión", "extorsion", "chantaje", "no divulgar", "amenazan con publicar", "publicar mis fotos", "difundir mis fotos", "me exigen dinero")
    if any(word in text for word in extortion_markers):
        category = "extorsión cibernética"
    else:
        category = next((name for name, words in KEYWORDS.items() if any(word in text for word in words)), None)
    assistant_turns = sum(1 for item in payload.messages if item.role == "assistant")
    facts = [item.content.strip() for item in payload.messages if item.role == "user" and item.content.strip()][-5:]
    general_answer = next((answer for phrase, answer in GENERAL_ANSWERS.items() if phrase in text), None)
    urgent = any(phrase in text for phrase in URGENT_WORDS)
    if not category and any(phrase in text for phrase in OTHER_INCIDENT_WORDS) and len(facts) >= 2:
        category = "otro"
    priority = "Crítica" if any(word in text for word in ("peligro", "amenaza física", "extorsión", "chantaje")) else "Alta" if any(word in text for word in ("perdí dinero", "hackearon", "bloqueó")) else "Media"
    missing = []
    if not category:
        missing.append("Tipo de incidente o qué ocurrió")
    has_channel_or_date = any(word in text for word in ("ayer", "hoy", "fecha", "semana", "mes", "correo", "sms", "whatsapp", "instagram", "facebook", "telegram", "red social"))
    has_evidence = any(word in text for word in ("captura", "capturas", "evidencia", "evidencias", "pantallazo", "pantallazos", "enlace", "link", "archivo", "archivos", "nombre de usuario", "usuario"))
    has_impact = any(word in text for word in ("perdí", "perdi", "daño", "dano", "afectó", "afecto", "entraron", "publicaron", "cobraron", "bloqueó", "bloqueo", "me preocupa", "consecuencia", "resultado"))
    if len(facts) < 2 or not has_channel_or_date:
        missing.append("Cuándo ocurrió y por qué canal o aplicación")
    if category and not has_impact:
        missing.append("Qué consecuencia tuvo o qué es lo que más te preocupa")
    if not has_evidence:
        missing.append("Si conservas capturas, enlaces, archivos o nombres de usuario")
    has_actions = any(word in text for word in ("hice", "cambié", "cambie", "bloqueé", "bloquee", "contacté", "contacte", "denuncié", "denuncie", "no hice", "todavía no", "todavia no"))
    ready = bool(category and len(facts) >= 4 and has_channel_or_date and has_impact and has_actions and has_evidence)
    if urgent:
        message = "Si hay peligro físico o una emergencia, aléjate de la situación y contacta inmediatamente a emergencias o a la autoridad local. No compartas tu ubicación aquí. Si estás a salvo, puedo ayudarte a ordenar los hechos digitales después."
    elif general_answer and not category:
        message = general_answer
    elif ready:
        if has_evidence:
            message = "Ya organicé el borrador con el incidente, cuándo ocurrió y las evidencias disponibles. Revisa el resumen, agrega un medio de contacto y confirma solo si representa correctamente tu caso."
        else:
            message = "Ya organicé el borrador. Si puedes, conserva capturas, enlaces o archivos relacionados. Revisa el resumen, agrega un medio de contacto y confirma solo si representa correctamente tu caso."
    elif category:
        first_question, evidence_question = FOLLOW_UPS[category]
        previous_assistant_messages = [item.content.lower() for item in payload.messages[:-1] if item.role == "assistant"]
        already_requested_evidence = any(any(word in message for word in ("evidencia", "captura", "enlace", "archivo", "nombre de usuario")) for message in previous_assistant_messages)
        if already_requested_evidence and not has_evidence:
            message = "Para avanzar sin repetir preguntas, dime si conservas alguna prueba relacionada, aunque sea una captura, enlace, archivo o nombre de usuario."
        elif len(facts) == 1:
            message = first_question
        elif not has_channel_or_date:
            message = "Gracias por explicarlo; entiendo que puede ser preocupante. Para ubicar los hechos, ¿cuándo ocurrió y en qué canal o aplicación pasó?"
        elif not has_impact:
            message = "Gracias, ya entiendo mejor la situación. ¿Qué consecuencia tuvo o qué es lo que más te preocupa en este momento?"
        elif not has_actions:
            message = "Entiendo. Para saber cómo orientarte, ¿qué hiciste después de notarlo: cambiaste alguna clave, contactaste al banco o todavía no has tomado medidas?"
        elif not has_evidence:
            message = evidence_question
        else:
            message = "Gracias. Ya tengo los datos principales. ¿Hay algún otro detalle importante que deba incluir antes de preparar el borrador?"
    else:
        message = "Gracias por contarme. Para orientarte mejor, dime qué pasó: ¿recibiste un mensaje, perdiste una cuenta, hubo un cobro, publicaron información o te amenazaron? No compartas contraseñas ni códigos."
    return AgentChatResponse(message=message, draft=AgentDraft(category=category, priority=priority, summary=" ".join(facts), facts=facts, missing_information=missing, evidence_requested=["Capturas, enlaces o archivos relacionados"], needs_human_review=True), ready_to_confirm=ready)


async def chat_with_agent(payload: AgentChatRequest) -> AgentChatResponse:
    # El flujo local permite que el chatbot siga funcionando en desarrollo,
    # en despliegues sin clave y durante una caída temporal del proveedor.
    if not settings.ai_agent_enabled or not settings.gemini_api_key:
        return _local_chat(payload)
    # Enviar solo el contexto reciente reduce el tiempo de procesamiento sin
    # perder los datos relevantes del reporte.
    contents = [{"role": "user" if item.role == "user" else "model", "parts": [{"text": item.content}]} for item in payload.messages[-min(settings.ai_agent_max_history_messages, 8):]]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    body = {"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]}, "contents": contents, "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2, "maxOutputTokens": 900}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
            response = await client.post(url, headers={"x-goog-api-key": settings.gemini_api_key}, json=body)
            response.raise_for_status()
        response_data = response.json()
        candidates = response_data.get("candidates") or []
        if not candidates:
            raise ValueError("Gemini no devolvió candidatos de respuesta")
        response_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        if response_text.startswith("```"):
            response_text = response_text.removeprefix("```").removeprefix("json").removesuffix("```").strip()
        if not response_text:
            raise ValueError("Gemini devolvió una respuesta vacía")
        parsed = AgentChatResponse.model_validate(json.loads(response_text))
    except Exception:
        return _local_chat(payload)
    if parsed.draft.category not in (*CATEGORIES, None):
        parsed.draft.category = "otro"
    parsed.ready_to_confirm = bool(parsed.ready_to_confirm and parsed.draft.category and parsed.draft.summary.strip())
    parsed.conversation_id = payload.conversation_id
    return parsed
