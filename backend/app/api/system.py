"""Endpoints internos para operaciones programadas."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.retention import delete_expired_reports

router = APIRouter(prefix="/internal", tags=["system"])


def require_cron_secret(authorization: str | None = Header(default=None)) -> None:
    """Autoriza únicamente al programador que conoce el secreto privado."""
    if not settings.cron_secret:
        raise HTTPException(503, "La tarea programada no está configurada")
    expected = f"Bearer {settings.cron_secret}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, "No autorizado")


@router.get("/retention/run", dependencies=[Depends(require_cron_secret)])
def run_retention(db: Session = Depends(get_db)) -> dict:
    """Elimina casos vencidos y sus evidencias privadas, dejando auditoría."""
    deleted = delete_expired_reports(db, confirm=True)
    return {"deleted_reports": deleted}
