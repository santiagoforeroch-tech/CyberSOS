import jwt
from fastapi import HTTPException
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import settings


def auth_client() -> Client:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(503, "Supabase Auth no está configurado")
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


def admin_auth_client() -> Client:
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(503, "La activación administrativa no está configurada")
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
        options=SyncClientOptions(auto_refresh_token=False, persist_session=False),
    )


def require_institutional_admin(user_email: str | None) -> None:
    if not user_email or user_email.casefold() != settings.supabase_admin_email.casefold():
        raise HTTPException(403, "Esta cuenta no tiene autorización administrativa")


def verified_aal(access_token: str) -> str:
    claims = jwt.decode(access_token, options={"verify_signature": False})
    return str(claims.get("aal", "aal1"))
