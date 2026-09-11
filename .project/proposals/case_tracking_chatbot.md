# Propuesta: seguimiento conversacional y QR por caso

## Estado

Propuesta solicitada el 2026-08-28. Requiere aprobación de SENATIC antes de ampliar el MVP porque introduce consulta ciudadana de casos y conversación asistida.

## Resultado esperado

- Antes de reportar, cualquier ciudadano puede conversar con un asistente de orientación general que no diagnostica ni consulta datos privados.
- Después de reportar, la persona recibe un QR y un código de seguimiento exclusivos del caso.
- El QR abre WhatsApp con una referencia opaca; nunca contiene nombre, contacto, descripción, estado ni identificadores internos.
- Para consultar un caso, WhatsApp exige una segunda prueba de posesión enviada al contacto registrado.
- El administrador conversa con Gemini dentro del panel utilizando únicamente el caso abierto y siempre revisa las sugerencias antes de aplicarlas.

## Controles obligatorios

- No permitir búsqueda pública por número de caso solamente.
- Guardar únicamente el hash del token de seguimiento; el valor original se muestra una sola vez.
- Rotar o revocar el token si el QR se comparte o se pierde.
- Limitar intentos, registrar auditoría y ocultar datos sensibles en mensajes y registros.
- Mostrar estados resumidos al ciudadano; observaciones internas, análisis IA y evidencias permanecen solo para el administrador.
- Obtener consentimiento explícito antes de enviar contenido del caso a Gemini.
- Escalar a una persona cuando exista riesgo urgente, amenaza, extorsión o posible afectación a menores.

## Flujo propuesto

1. CyberSOS crea el reporte y genera un token aleatorio de alta entropía.
2. La base guarda el hash y la fecha de vencimiento; el QR contiene un enlace de WhatsApp con una referencia opaca.
3. WhatsApp solicita una verificación adicional enviada al correo o teléfono registrado.
4. Tras verificar, el ciudadano ve estado, última actualización pública y próximos pasos.
5. El administrador puede publicar una actualización ciudadana separada de las notas internas.

## Decisiones pendientes

- Número oficial de WhatsApp Business y aprobación de Meta.
- Política institucional sobre qué estados y mensajes se pueden mostrar al ciudadano.
- Duración, renovación y revocación del token de seguimiento.
- Proveedor y presupuesto para mensajería, Gemini, antivirus y monitoreo.
- Protocolo de emergencia y responsable humano de escalamiento.
