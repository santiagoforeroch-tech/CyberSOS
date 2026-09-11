# Arquitectura

## Flujo

```text
Navegador → Vite React → /api de FastAPI → servicios → SQLAlchemy → PostgreSQL de Supabase
```

## Backend

- API bajo `/api` y verificación en `/api/health`.
- Configuración mediante variables de entorno.
- Modelos SQLAlchemy alineados con migraciones SQL.
- Sin creación automática de tablas al iniciar.
- Integra Supabase Auth/Storage solo desde servicios del backend.
- Recibe webhooks de WhatsApp y reutiliza el mismo servicio de creación de reportes.

## Frontend

- React consume exclusivamente la API de FastAPI.
- `VITE_API_URL` contiene una URL pública, nunca un secreto.
- Cada pantalla contempla carga, vacío, error y éxito.

## Datos

Entidades: contadores anuales, reportes, evidencias, análisis IA, observaciones, historial y auditoría de eliminación. Aplicar DDL mediante archivos en `supabase/migrations/` y Supabase MCP.

## Integraciones

- Web: React → FastAPI.
- WhatsApp (desarrollo local): puente Baileys aislado → webhook firmado de FastAPI → servicio de reportes. El puente usa una única cuenta dedicada, conserva solo mensajes nuevos y nunca se ejecuta en el frontend ni en una función serverless.
- No se usa un asistente de IA para procesar denuncias.
- Secretos únicamente en `.env`; nunca variables `VITE_*` salvo la URL pública de la API.

## Separación de accesos

- **Propietario técnico de Supabase:** cuenta personal de Santiago, protegida con MFA. Administra infraestructura, configuración y recuperación del proyecto; no se usa para entrar al panel de reportes.
- **Administrador de CyberSOS:** cuenta personal autorizada `santiagoforeroch@gmail.com`, protegida con MFA TOTP y validación `aal2`. Es la única cuenta que consulta y gestiona reportes.
- No compartir contraseñas, códigos TOTP ni tokens entre ambas cuentas. Revisar accesos trimestralmente.
