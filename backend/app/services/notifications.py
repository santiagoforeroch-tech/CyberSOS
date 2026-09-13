import smtplib
from email.message import EmailMessage

from app.core.config import settings


def notify_report_received(case_number: str) -> bool:
    """Send a minimal operational notice; never include report content or contact data."""
    if not settings.notifications_enabled:
        return False
    required = (settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.notification_from, settings.notification_admin_email)
    if not all(required):
        return False
    message = EmailMessage()
    message["Subject"] = f"Nuevo reporte CyberSOS: {case_number}"
    message["From"] = settings.notification_from
    message["To"] = settings.notification_admin_email
    message.set_content(
        "Se recibió un nuevo reporte en CyberSOS. "
        f"Número de caso: {case_number}. Ingresa al panel administrativo para revisarlo."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return True
