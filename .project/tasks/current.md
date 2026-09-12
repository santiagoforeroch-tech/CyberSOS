# Tarea actual

## Renovación de CyberSOS como plataforma de ciberdenuncias

- [ ] Conectar y aplicar las migraciones existentes al nuevo proyecto Supabase de desarrollo `kmjlwaviqqznjagrgkpd`; no trasladar datos reales.

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
- [x] Garantizar que el acceso local use una base SQLite aislada cuando Supabase no esté disponible, sin cambiar la configuración de despliegue.
- [x] Añadir gráficas administrativas para evolución, estados y prioridades de los reportes.
- [ ] Verificar el flujo actualizado en navegador antes de usar datos reales.

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
- [ ] Incorporar análisis antivirus antes de habilitar archivos de ciudadanos reales.
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
