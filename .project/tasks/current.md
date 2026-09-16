# Tarea actual

- [x] Corregir el acceso al panel: el código de correo se usa durante la activación inicial y el inicio de sesión posterior entra directamente con la sesión administrativa de Supabase; verificar pruebas de autenticación y build frontend.

- [x] Reforzar el cierre de producción: encabezados de seguridad en Vercel, verificación CI para backend/frontend y contraste accesible del login.
- [x] Validar localmente el cierre: backend 10/10, frontend 6/6, ESLint, build Vite, JSON de Vercel y escaneo de patrones de credenciales.

## Renovación de CyberSOS como plataforma de ciberdenuncias

## Nueva funcionalidad aprobada: agente conversacional con IA

- [x] Implementar agente ciudadano temporal con mensajes predeterminados detrás de FastAPI, sin API keys.
- [x] Restaurar el respaldo local del agente cuando Gemini está desactivado o no tiene clave, evitando respuestas 503 en el chatbot.
- [x] Desacoplar el chat temporal de la persistencia de conversaciones para que pueda responder aun si la tabla de conversaciones no está disponible.
- [ ] Mantener el formulario actual como respaldo durante la validación.
- [ ] Hacer que la IA produzca un borrador estructurado y nunca escriba directamente en Supabase.
- [ ] Exigir confirmación ciudadana antes de crear el reporte.
- [ ] Registrar conversación, resumen y trazabilidad sin guardar secretos.
- [ ] Añadir límites de uso, detección de solicitudes sensibles y derivación humana.
- [ ] Integrar primero en web y después reutilizar el servicio para WhatsApp.

- [x] Conectar y aplicar las migraciones existentes al nuevo proyecto Supabase de desarrollo `kmjlwaviqqznjagrgkpd`; no trasladar datos reales.

- [x] Reparar el arranque local y verificar el envío de reportes con la base de desarrollo.
- [ ] Configurar el puente WhatsApp local con PostgreSQL/Supabase, secretos privados y una cuenta dedicada para habilitar el QR.
- [x] Retirar el acceso por código de piloto y permitir el envío público de ciberdenuncias sin cuenta.
- [x] Retirar Gemini y el consentimiento asociado de las pantallas y endpoints activos.
- [x] Mantener el alta única de administrador, inicio de sesión y MFA.
- [x] Hacer que la bandeja administrativa se actualice automáticamente cada 15 segundos.
- [x] Renovar la paleta visual a violeta y magenta.
- [x] Crear e integrar el símbolo vectorial CyberSOS y su guía de marca.
- [x] Sustituir el símbolo por una marca vectorial sobria de escudo, alerta y señal, sin degradados ni efectos generativos.
- [x] Añadir métricas operativas: categorías, prioridades y tiempo medio de gestión.
- [x] Añadir límite básico por IP para el formulario público.
- [x] Renovar el inicio de sesión administrativo con ilustración original de respuesta cibernética y diseño adaptable.
- [x] Explicar en lenguaje sencillo las categorías de ciberincidentes del formulario público.
- [x] Fortalecer la bandeja administrativa: filtros por prioridad, actualización manual y mensajes claros ante errores o casos no encontrados.
- [x] Hacer funcional la acción rápida “Generar informe” del centro de control mediante descarga CSV de los casos visibles.
- [x] Mostrar todas las acciones rápidas del centro de control; se eliminaron reglas CSS antiguas que las ocultaban.
- [x] Mantener en el panel solo acciones administrativas: ver casos y generar informe; retirar accesos ajenos a la operación.
- [x] Alinear las consultas de actualización, observaciones y evidencias con el esquema privado usado en producción.
- [x] Garantizar que el acceso local use una base SQLite aislada cuando Supabase no esté disponible, sin cambiar la configuración de despliegue.
- [x] Añadir gráficas administrativas para evolución, estados y prioridades de los reportes.
- [ ] Verificar el flujo actualizado en navegador antes de usar datos reales.

## Ajuste de activación MFA (2026-09-15)

- [x] Mantener el código MFA por correo únicamente durante la creación/activación inicial de la cuenta administrativa.
- [x] Mantener el inicio de sesión posterior con correo y contraseña, sin solicitar un código MFA.
- [x] Alinear los textos del login y de la pantalla de verificación con este flujo.
- [ ] Completar verificación real en navegador y ejecutar las baterías bloqueadas por el entorno OneDrive.

## Flujo vertical inicial: reporte ciudadano

- [x] Terminar configuración y dependencias.
- [x] Registrar y aplicar la migración del dominio en Supabase.
- [x] Crear API para acceso piloto y envío de reportes.
- [x] Crear formulario web guiado, confirmación y panel inicial.
- [x] Añadir pruebas de backend y frontend.
- [x] Verificar el flujo local con datos ficticios en escritorio y móvil.
- [x] Añadir accesos locales de doble clic para iniciar y detener CyberSOS desde Apolo.
- [x] Renovar la portada con una presentación más dinámica y accesible.
- [x] Completar la bandeja administrativa con indicadores, búsqueda, filtros y estados vacíos.
- [x] Mejorar el detalle administrativo con prioridad, estado, observaciones e historial.

## Próximo corte vertical

### Central WhatsApp local con Baileys

- [x] Instalar el scaffold de la central local con una sola cuenta dedicada y datos ficticios; no importar historial.
- [x] Preparar persistencia de mensajes nuevos, outbox y medios privados mediante FastAPI, SQLAlchemy y Supabase.
- [x] Exponer QR, estado y bandeja solamente en desarrollo local; no conectar un número durante la implementación.
- [x] Aplicar la migración en el proyecto Supabase de desarrollo y verificar con datos ficticios el flujo de eventos firmados, deduplicación y creación de reporte.
- [x] Enlazar mensajes directos de WhatsApp a un reporte y registrar el seguimiento en su historial.
- [x] Añadir análisis Gemini manual, estructurado y auditable, condicionado al consentimiento.

- [x] Implementar la activación única del administrador desde el inicio de sesión; falta su ejecución real por el administrador autorizado.
  - [x] Pedir nombre completo, correo autorizado, contraseña y confirmación.
  - [x] Exigir una clave de creación validada solo por el backend.
  - [x] Bloquear nuevos registros después de completar la activación.
  - [x] Continuar inmediatamente al enrolamiento MFA.
- [x] Implementar validación, carga privada, metadatos SHA-256 y enlaces administrativos temporales para evidencias.
- [x] Verificar y optimizar el bucket privado y sus índices en Supabase.
- [x] Configurar localmente la clave secreta del backend y probar una carga real de punta a punta.
- [x] Integrar Supabase Auth y el enrolamiento TOTP real en backend y frontend.
- [x] Confirmar que el administrador aceptó la invitación y verificó su correo.
- [ ] Enrolar el factor TOTP y completar la prueba de acceso real con MFA.
- [ ] Activar MFA en la cuenta propietaria de Supabase desde Account Settings → Security.
- [x] Incorporar el webhook firmado de WhatsApp detrás de configuración segura; Gemini queda preparado y pendiente de su clave local.
- [ ] Conectar el botón de análisis asistido cuando exista una clave de Gemini configurada en el backend.

## Potenciadores priorizados

- [x] Añadir almacenamiento privado con tipos permitidos, tamaño máximo y enlaces temporales.
- [x] Incorporar integración configurable con ClamAV antes de habilitar archivos de ciudadanos reales; queda pendiente desplegar el escáner privado.
- [ ] Incorporar clasificación Gemini con salida estructurada, trazabilidad, revisión humana y límites de uso.
- [ ] Crear tablero de métricas: categorías, severidad, tiempos de respuesta y evolución temporal.
- [ ] Añadir notificaciones institucionales sin incluir información sensible en el correo.
- [x] Automatizar retención de 90 días, auditoría y eliminación verificable.
- [ ] Preparar despliegues separados de desarrollo y producción, monitoreo y copias de seguridad.
  - [x] Preparar frontend Vite y FastAPI como servicios de Vercel con el mismo dominio (`/` y `/api`).
  - [x] Migrar la configuración a la sintaxis `services` actual de Vercel y enrutar explícitamente `/api` al backend.
  - [x] Aclarar los errores de acceso administrativo para distinguir credenciales inválidas de fallos de conexión con Supabase.
  - [x] Mostrar los errores de validación del formulario administrativo como texto legible en lugar de `[object Object]`.
  - [ ] Configurar las variables privadas de producción en Vercel y verificar el flujo completo antes de producción.

## Ampliación propuesta (pendiente de aprobación SENATIC)

- [ ] Aprobar el diseño de seguimiento ciudadano con token revocable, segunda verificación y QR para WhatsApp.
- [ ] Aprobar el alcance del asistente ciudadano general y del asistente administrativo contextual.
- [ ] Definir qué actualizaciones del caso son públicas y cuáles permanecen internas.

## Identidad visual y cierre de organización

- [x] Integrar el logo proporcionado por el estudiante en la marca reutilizada de portada, pie, acceso administrativo y panel.
- [x] Mostrar el nombre CyberSOS debajo del símbolo con adaptación responsive.
- [ ] Verificar el flujo actualizado en navegador y corregir el bloqueo local de Vitest/build causado por permisos de esbuild en OneDrive.
- [x] Redirigir al login cuando la sesión administrativa vence, evitando mostrar un falso aviso de conexión.
- [x] Crear Centro de protección público con guía rápida, checklist, recursos oficiales y acceso directo al reporte.
- [x] Añadir botón de riesgo inmediato, test de seguridad, guías por incidente, checklist descargable, compartir, preguntas frecuentes e indicador de progreso.

## Verificación frontend 2026-09-13

- [x] Corregir navegación de “Cómo funciona” para llevar al ancla correcta sin rutas hash duplicadas.
- [x] Retirar controles visuales sin función real del login y del menú administrativo.
- [x] Hacer copiable el número de caso y mostrar confirmación accesible.
- [x] Evitar desbordes de textos largos en tablas, detalles, cronologías y confirmaciones.
- [x] Ajustar navegación del panel administrativo en móvil y recortar el overflow horizontal decorativo.
- [x] Verificar ESLint, Vitest, build Vite y Pytest antes de publicar.
