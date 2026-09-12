# Contexto del proyecto

- **Título:** CyberSOS
- **Slug:** `cybersos`
- **Creado:** 2026-08-26
- **Fase actual:** Desarrollo
- **Stack:** FastAPI, SQLAlchemy, PostgreSQL de Supabase, Vite React
- **Autenticación:** Un administrador mediante Supabase Auth y MFA TOTP; ciudadanos sin cuenta
- **Supabase project ref:** `kmjlwaviqqznjagrgkpd`
- **Región:** Por confirmar desde el proyecto conectado
- **MCP:** Pendiente de reconectar al nuevo proyecto de desarrollo; no aplicar migraciones hasta validar la conexión PostgreSQL.
- **UI/UX Pro Max:** Instalado y verificado; versión `2.15.0`
- **Propiedad y administración:** La organización Supabase APOLO y el panel CyberSOS están autorizados para `santiagoforeroch@gmail.com`. Son identidades separadas: cuenta del Dashboard y usuario de Supabase Auth, ambas con MFA obligatorio.

## Resumen

CyberSOS es una plataforma institucional de ciberdenuncias: recibe reportes web y WhatsApp, protege las evidencias y permite al administrador hacer seguimiento centralizado. Durante el desarrollo se usan únicamente datos ficticios.

## Reglas de continuidad

Leer este archivo, `mvp.md`, `architecture.md`, `tasks/current.md` y `handoffs/latest.md` al comenzar cada sesión. No guardar secretos aquí.
