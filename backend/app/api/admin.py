from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.core.config import settings
from app.db.session import get_db
from app.models import CaseHistory, Evidence, Observation, Report
from app.schemas.reports import ObservationCreate, ReportSummary, ReportUpdate
from app.services.evidence import create_download_url

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])
logger = logging.getLogger(__name__)


def _private_query(query):
    """Aplica el esquema de producción sin afectar las pruebas SQLite."""
    if not settings.database_url.startswith("sqlite"):
        return query.execution_options(schema_translate_map={None: "private"})
    return query


@router.get("/reports")
def reports(search: str = "", status: str = "", priority: str = "", db: Session = Depends(get_db)) -> dict:
    query = select(Report)
    if search:
        query = query.where(or_(Report.case_number.ilike(f"%{search}%"), Report.reporter_name.ilike(f"%{search}%")))
    if status:
        query = query.where(Report.status == status)
    if priority:
        query = query.where(Report.priority == priority)
    try:
        items = db.execute(_private_query(query.order_by(Report.created_at.desc()).limit(100))).scalars().all()
    except Exception:
        logger.exception("admin reports query failed")
        raise HTTPException(503, "Base de datos administrativa no disponible")
    return {"items": [ReportSummary.model_validate(item).model_dump(mode="json") for item in items]}


@router.get("/reports/{report_id}")
def detail(report_id: str, db: Session = Depends(get_db)) -> dict:
    report = db.execute(_private_query(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Reporte no encontrado")
    return {**ReportSummary.model_validate(report).model_dump(mode="json"), "description": report.description, "channel": report.channel, "contact_value": report.contact_value, "evidences": [{"id": e.id, "original_name": e.original_name, "mime_type": e.mime_type, "size_bytes": e.size_bytes, "created_at": e.created_at.isoformat()} for e in sorted(report.evidences, key=lambda x: x.created_at)], "history": [{"action": h.action, "details": h.details, "created_at": h.created_at.isoformat()} for h in sorted(report.history, key=lambda x: x.created_at, reverse=True)], "observations": [{"id": o.id, "text": o.text, "created_at": o.created_at.isoformat()} for o in sorted(report.observations, key=lambda x: x.created_at, reverse=True)]}


@router.post("/evidences/{evidence_id}/download-url")
def evidence_download(evidence_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(Evidence, evidence_id)
    if not item:
        raise HTTPException(404, "Evidencia no encontrada")
    url = create_download_url(item.storage_key)
    if not url:
        raise HTTPException(502, "No fue posible preparar la descarga")
    return {"url": url, "expires_in": 60}


@router.patch("/reports/{report_id}")
def update(report_id: str, payload: ReportUpdate, db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, "Reporte no encontrado")
    changes = {}
    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "status" and value not in {"Nuevo", "En revisión", "Atendido", "Cerrado"} or field == "priority" and value not in {"Baja", "Media", "Alta", "Crítica"}:
            raise HTTPException(422, "Valor inválido")
        changes[field] = {"before": getattr(report, field), "after": value}; setattr(report, field, value)
    db.add(CaseHistory(report_id=report.id, action="Caso actualizado", details=changes, actor_type="admin", actor_id="local-admin")); db.commit()
    return {"message": "Caso actualizado"}


@router.post("/reports/{report_id}/observations", status_code=201)
def observation(report_id: str, payload: ObservationCreate, db: Session = Depends(get_db)) -> dict:
    if not db.get(Report, report_id):
        raise HTTPException(404, "Reporte no encontrado")
    item = Observation(report_id=report_id, text=payload.text); db.add(item); db.flush(); db.add(CaseHistory(report_id=report_id, action="Observación agregada", details={"observation_id": item.id}, actor_type="admin", actor_id="local-admin")); db.commit()
    return {"id": item.id, "message": "Observación agregada"}


@router.get("/statistics")
def statistics(db: Session = Depends(get_db)) -> dict:
    try:
        reports = db.execute(_private_query(select(Report))).scalars().all()
        by_status = dict(db.execute(_private_query(select(Report.status, func.count()).group_by(Report.status))).all())
        by_category = dict(db.execute(_private_query(select(Report.category, func.count()).group_by(Report.category).order_by(func.count().desc()))).all())
        by_priority = dict(db.execute(_private_query(select(Report.priority, func.count()).group_by(Report.priority))).all())
    except Exception:
        logger.exception("admin statistics query failed")
        raise HTTPException(503, "Base de datos administrativa no disponible")
    completed = [report for report in reports if report.status in {"Atendido", "Cerrado"}]
    average_hours = round(sum((report.updated_at - report.created_at).total_seconds() / 3600 for report in completed) / len(completed), 1) if completed else None
    today = datetime.now(timezone.utc).date()
    trend = []
    for offset in range(6, -1, -1):
        day = today.fromordinal(today.toordinal() - offset)
        trend.append({"date": day.isoformat(), "count": sum(1 for report in reports if report.created_at.date() == day)})
    return {"total": len(reports), "by_status": by_status, "by_category": by_category, "by_priority": by_priority, "average_resolution_hours": average_hours, "trend": trend}
