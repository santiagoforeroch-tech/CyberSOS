"""Retención explícita y auditable; nunca se ejecuta al iniciar la API."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeletionAudit, Report
from app.services.evidence import remove_evidence


def expired_reports(db: Session, now: datetime | None = None) -> list[Report]:
    """Devuelve los casos vencidos sin modificar datos."""
    cutoff = now or datetime.now(timezone.utc)
    return list(db.scalars(select(Report).where(Report.expires_at <= cutoff).order_by(Report.expires_at)))


def delete_expired_reports(db: Session, now: datetime | None = None, *, confirm: bool = False) -> int:
    """Elimina solo casos vencidos tras confirmación explícita y deja auditoría."""
    if not confirm:
        raise ValueError("La retención exige confirmación explícita")
    reports = expired_reports(db, now)
    try:
        for report in reports:
            evidences = list(report.evidences)
            remove_evidence([item.storage_key for item in evidences])
            db.add(DeletionAudit(
                case_number=report.case_number,
                report_id=report.id,
                evidence_count=len(evidences),
            ))
            db.delete(report)
        db.commit()
        return len(reports)
    except Exception:
        db.rollback()
        raise
