import hashlib
import hmac
import time

from fastapi import Cookie, HTTPException

from app.core.config import settings


def sign_token(purpose: str, lifetime: int) -> str:
    expires = str(int(time.time()) + lifetime)
    payload = f"{purpose}.{expires}"
    signature = hmac.new(settings.session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def expected_admin_setup_key() -> str:
    if not settings.session_secret:
        raise HTTPException(503, "La activación administrativa no está configurada")
    digest = hmac.new(settings.session_secret.encode(), b"cybersos-admin-setup", hashlib.sha256).hexdigest().upper()
    return f"CS-{digest[:6]}-{digest[6:12]}"


def valid_token(token: str | None, purpose: str) -> bool:
    try:
        actual, expires, signature = (token or "").split(".", 2)
        payload = f"{actual}.{expires}"
        expected = hmac.new(settings.session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return actual == purpose and int(expires) >= int(time.time()) and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


def require_admin(
    admin_session: str | None = Cookie(default=None),
    sb_access_token: str | None = Cookie(default=None),
) -> str:
    if settings.auth_provider == "local":
        if not valid_token(admin_session, "admin-aal2"):
            raise HTTPException(401, "Se requiere una sesión administrativa con MFA")
        return "local-admin"

    if not sb_access_token:
        raise HTTPException(401, "Inicia sesión con la cuenta institucional")

    from app.services.supabase_auth import auth_client, require_institutional_admin, verified_aal

    try:
        user_response = auth_client().auth.get_user(sb_access_token)
        user = user_response.user
        require_institutional_admin(user.email)
        if verified_aal(sb_access_token) != "aal2":
            raise HTTPException(403, "Completa la verificación MFA")
        return user.id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(401, "La sesión administrativa no es válida") from exc


def require_mfa_pending(mfa_pending: str | None = Cookie(default=None)) -> None:
    if not valid_token(mfa_pending, "mfa-pending"):
        raise HTTPException(401, "Primero debes validar el correo y la contraseña")
