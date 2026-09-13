# Lista de preparación para producción

Esta lista mantiene CyberSOS en desarrollo hasta que cada control tenga una verificación reciente.

## Antes de aceptar datos reales

- [ ] Completar la verificación manual del flujo público y administrativo.
- [ ] Activar un antivirus externo o ClamAV gestionado para analizar evidencias antes de almacenarlas.
- [ ] Configurar SMTP transaccional y enviar únicamente avisos sin descripción, contacto ni archivos adjuntos.
- [ ] Confirmar las variables privadas de producción en Vercel sin exponer sus valores.
- [ ] Confirmar que `CRON_SECRET` está configurado y probar la tarea de retención con datos ficticios.

## Operación

- [ ] Activar monitoreo de errores y disponibilidad para `/api/health`.
- [ ] Configurar copias de seguridad de Supabase y probar una restauración en un proyecto separado.
- [ ] Revisar accesos administrativos y MFA trimestralmente.
- [ ] Separar claramente proyectos de desarrollo y producción.

## Pendientes explícitos

- WhatsApp real y su cuenta dedicada.
- Definición y prueba final del método MFA.
