import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from app.core.config import settings
from app.core.rate_limit import limit_public_report
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CaseHistory, Evidence
from app.schemas.reports import ReportCreate
from app.services.evidence import prepare_evidence, remove_evidence, upload_evidence
from app.services.reports import create_report
from app.services.notifications import notify_report_received

router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.post("", status_code=201)
async def submit(request: Request, payload: str = Form(), website: str = Form(default=""), evidence: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)) -> dict:
    # Campo trampa: las personas nunca lo ven; los robots genéricos suelen llenarlo.
    if website.strip():
        raise HTTPException(422, "No fue posible validar el envío")
    try:
        report_payload = ReportCreate.model_validate(json.loads(payload))
    except json.JSONDecodeError as error:
        raise HTTPException(422, "Los datos del reporte no son válidos") from error
    except ValidationError as error:
        error_text = str(error).lower()
        message = "Revisa los campos obligatorios del reporte."
        if "email" in error_text:
            message = "Revisa el correo de contacto e intenta nuevamente."
        elif "categor" in error_text:
            message = "Selecciona una categoría válida para el incidente."
        raise HTTPException(422, message) from error
    client_ip = request.client.host if request.client else "unknown"
    limit_public_report(client_ip, settings.public_report_rate_limit, settings.public_report_rate_window_seconds)
    prepared = await prepare_evidence(evidence)
    report = create_report(db, report_payload, commit=not prepared)
    if prepared:
        records = []
        try:
            records = upload_evidence(report.id, prepared)
            for record in records:
                db.add(Evidence(report_id=report.id, **record))
            db.add(CaseHistory(report_id=report.id, action="Evidencias almacenadas", details={"count": len(records)}, actor_type="citizen"))
            db.commit()
        except Exception:
            db.rollback()
            remove_evidence([record["storage_key"] for record in records])
            raise
    if settings.notifications_enabled:
        try:
            notify_report_received(report.case_number)
        except Exception:
            # El reporte ya está guardado; una falla de correo no debe duplicar ni perder el caso.
            pass
    return {"case_number": report.case_number, "evidence_count": len(prepared), "message": "Tu reporte fue recibido correctamente"}
