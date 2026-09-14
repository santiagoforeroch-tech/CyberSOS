# MVP de CyberSOS

## Resumen aprobado

Plataforma institucional de ciberdenuncias para reportar y gestionar incidentes desde la web y WhatsApp. Durante el desarrollo se usan datos ficticios.

## Problema

Las personas afectadas necesitan registrar incidentes digitales de forma sencilla y el responsable autorizado necesita centralizarlos, analizarlos y hacer seguimiento.

## Usuarios

- Ciudadano: reporta por web o WhatsApp sin crear cuenta.
- Administrador único: gestiona los reportes con contraseña y MFA.

## Objetivo

Ofrecer el recorrido reporte → número de caso → gestión administrativa → historial.

## Incluido

- Formulario guiado, evidencias privadas e identificador `CS-AAAA-XXXXXX`.
- Panel administrativo protegido con MFA, actualización automática, filtros, detalle, observaciones, historial y estadísticas básicas.
- Preparación de webhook de WhatsApp.
- Asistente conversacional con IA para orientar al ciudadano, organizar el relato y preparar un reporte sujeto a confirmación.
- Retención de 90 días.

## Fuera del MVP

- Cuentas, perfiles o consulta pública para ciudadanos.
- Registro público, múltiples administradores y recuperación de contraseña.
- Publicación o uso con datos reales sin aprobación institucional.
- Decisiones autónomas sobre culpabilidad, cierre o atención de casos; el agente siempre requiere confirmación y revisión humana cuando corresponda.

## Historias y criterios de aceptación

- Como ciudadano autorizado, puedo registrar un incidente y recibir un número único sin crear cuenta.
- Como administrador con MFA, puedo buscar, revisar y actualizar un caso.
- Como responsable, puedo verificar evidencias, observaciones, historial y vencimiento de datos.
