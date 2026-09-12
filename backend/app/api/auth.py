import hmac
import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.config import settings
from app.core.security import expected_admin_setup_key, require_mfa_pending, sign_token
from app.services.supabase_auth import admin_auth_client, auth_client, require_institutional_admin

router = APIRouter(prefix="/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class MfaInput(BaseModel):
    code: str


class ActivationInput(BaseModel):
    access_token: str
    refresh_token: str
    password: str


class AdminRegistrationInput(BaseModel):
    full_name: str = Field(min_length=5, max_length=120)
    email: EmailStr
    password: str = Field(max_length=128)
    password_confirmation: str = Field(max_length=128)
    setup_key: str = Field(min_length=8, max_length=64)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned.split()) < 2:
            raise ValueError("Escribe nombre y apellido")
        return cleaned

    @model_validator(mode="after")
    def validate_password(self):
        if self.password != self.password_confirmation:
            raise ValueError("Las contraseñas no coinciden")
        return self


def set_supabase_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    options = {"httponly": True, "secure": settings.cookie_secure, "samesite": "strict", "path": "/"}
    response.set_cookie("sb_access_token", access_token, max_age=3600, **options)
    response.set_cookie("sb_refresh_token", refresh_token, max_age=60 * 60 * 24 * 30, **options)


def start_mfa(client, response: Response) -> dict:
    verified = next((factor for factor in client.auth.mfa.list_factors().totp if factor.status == "verified"), None)
    enrollment = None
    factor_id = verified.id if verified else ""
    if not verified:
        enrolled = client.auth.mfa.enroll({"factor_type": "totp", "friendly_name": "CyberSOS administrador"})
        factor_id = enrolled.id
        enrollment = {"qr_code": enrolled.totp.qr_code, "secret": enrolled.totp.secret}
    challenge = client.auth.mfa.challenge({"factor_id": factor_id})
    cookie_options = {"httponly": True, "secure": settings.cookie_secure, "samesite": "strict", "max_age": 300, "path": "/"}
    response.set_cookie("mfa_pending", sign_token("mfa-pending", 300), **cookie_options)
    response.set_cookie("mfa_factor_id", factor_id, **cookie_options)
    response.set_cookie("mfa_challenge_id", challenge.id, **cookie_options)
    return {"mfa_required": True, "enrollment_required": enrollment is not None, "enrollment": enrollment}


def login_error(exc: Exception) -> HTTPException:
    """Devuelve un mensaje útil sin revelar detalles internos de Supabase."""
    message = str(exc).casefold()
    if "invalid login credentials" in message:
        return HTTPException(401, "Correo o contraseña incorrectos")
    if "email not confirmed" in message:
        return HTTPException(401, "Confirma el correo de la cuenta administrativa antes de iniciar sesión")
    logger.exception("No fue posible iniciar sesión con Supabase")
    return HTTPException(503, "No fue posible conectar con Supabase. Revisa la configuración de Vercel e inténtalo nuevamente")


@router.post("/login")
def login(payload: LoginInput, response: Response) -> dict:
    if settings.auth_provider == "local":
        if not (hmac.compare_digest(str(payload.email), settings.local_admin_email) and hmac.compare_digest(payload.password, settings.local_admin_password)):
            raise HTTPException(401, "Credenciales incorrectas")
        response.set_cookie("mfa_pending", sign_token("mfa-pending", 300), httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=300)
        return {"mfa_required": True}

    try:
        client = auth_client()
        signed_in = client.auth.sign_in_with_password({"email": str(payload.email), "password": payload.password})
        if not signed_in.user or not signed_in.session:
            raise HTTPException(401, "Credenciales incorrectas")
        require_institutional_admin(signed_in.user.email, signed_in.user.app_metadata)
        set_supabase_cookies(response, signed_in.session.access_token, signed_in.session.refresh_token)
        return start_mfa(client, response)
    except HTTPException:
        raise
    except Exception as exc:
        raise login_error(exc) from exc


@router.post("/register-admin", status_code=201)
def register_admin(payload: AdminRegistrationInput, response: Response) -> dict:
    if settings.auth_provider != "supabase":
        raise HTTPException(404, "La activación solo está disponible con Supabase")
    valid_key = hmac.compare_digest(payload.setup_key.strip().upper(), expected_admin_setup_key())
    if not valid_key:
        raise HTTPException(403, "El correo o la clave de creación no son válidos")

    try:
        admin_client = admin_auth_client()
        listed = admin_client.auth.admin.list_users(page=1, per_page=1000)
        users = getattr(listed, "users", listed)
        requested_email = str(payload.email).casefold()
        existing = next((user for user in users if (user.email or "").casefold() == requested_email), None)
        if existing and bool((existing.app_metadata or {}).get("setup_complete")):
            raise HTTPException(409, "La cuenta administrativa ya fue creada; inicia sesión")

        attributes = {
            "password": payload.password,
            "user_metadata": {**((existing.user_metadata or {}) if existing else {}), "full_name": payload.full_name},
            "app_metadata": {**((existing.app_metadata or {}) if existing else {}), "role": "admin", "setup_complete": True},
        }
        if existing:
            admin_client.auth.admin.update_user_by_id(existing.id, attributes)
        else:
            admin_client.auth.admin.create_user({
                "email": str(payload.email),
                "email_confirm": True,
                **attributes,
            })

        client = auth_client()
        signed_in = client.auth.sign_in_with_password({"email": str(payload.email), "password": payload.password})
        if not signed_in.user or not signed_in.session:
            raise HTTPException(401, "La cuenta fue creada, pero no fue posible iniciar la sesión")
        require_institutional_admin(signed_in.user.email, signed_in.user.app_metadata)
        set_supabase_cookies(response, signed_in.session.access_token, signed_in.session.refresh_token)
        return start_mfa(client, response)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "No fue posible crear la cuenta administrativa") from exc


@router.post("/activate")
def activate(payload: ActivationInput, response: Response) -> dict:
    if settings.auth_provider != "supabase":
        raise HTTPException(404, "La activación solo está disponible con Supabase")
    try:
        client = auth_client()
        session = client.auth.set_session(payload.access_token, payload.refresh_token)
        if not session.user or not session.session:
            raise HTTPException(401, "La invitación no es válida o ya venció")
        require_institutional_admin(session.user.email, session.user.app_metadata)
        updated = client.auth.update_user({"password": payload.password})
        require_institutional_admin(updated.user.email, updated.user.app_metadata)
        current_session = client.auth.get_session()
        if not current_session:
            raise HTTPException(401, "No fue posible crear la sesión")
        set_supabase_cookies(response, current_session.access_token, current_session.refresh_token)
        return start_mfa(client, response)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(401, "La invitación no es válida, ya fue utilizada o venció") from exc


@router.post("/mfa/verify")
def mfa(
    payload: MfaInput,
    response: Response,
    sb_access_token: str | None = Cookie(default=None),
    sb_refresh_token: str | None = Cookie(default=None),
    mfa_factor_id: str | None = Cookie(default=None),
    mfa_challenge_id: str | None = Cookie(default=None),
    _: None = Depends(require_mfa_pending),
) -> dict:
    if settings.auth_provider == "local":
        if not hmac.compare_digest(payload.code, settings.local_mfa_code):
            raise HTTPException(401, "Código MFA incorrecto")
        response.set_cookie("admin_session", sign_token("admin-aal2", 3600), httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=3600)
        response.delete_cookie("mfa_pending", secure=settings.cookie_secure, samesite="strict")
        return {"authenticated": True, "aal": "aal2"}

    if not all((sb_access_token, sb_refresh_token, mfa_factor_id, mfa_challenge_id)):
        raise HTTPException(401, "La verificación MFA expiró; inicia sesión nuevamente")
    try:
        client = auth_client()
        client.auth.set_session(sb_access_token, sb_refresh_token)
        verified = client.auth.mfa.verify({"factor_id": mfa_factor_id, "challenge_id": mfa_challenge_id, "code": payload.code})
        require_institutional_admin(verified.user.email, verified.user.app_metadata)
        set_supabase_cookies(response, verified.access_token, verified.refresh_token)
        response.delete_cookie("mfa_factor_id", path="/")
        response.delete_cookie("mfa_challenge_id", path="/")
        return {"authenticated": True, "aal": "aal2"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(401, "Código MFA incorrecto o vencido") from exc


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    for name in ("admin_session", "mfa_pending", "sb_access_token", "sb_refresh_token", "mfa_factor_id", "mfa_challenge_id"):
        response.delete_cookie(name, secure=settings.cookie_secure, samesite="strict", path="/")
