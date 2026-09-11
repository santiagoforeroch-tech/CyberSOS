from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CaseCounter, CaseHistory, Report
from app.schemas.reports import ReportCreate


def create_report(db: Session, payload: ReportCreate, source: str = "web", commit: bool = True) -> Report:
    now = datetime.now(timezone.utc)
    counter = db.execute(select(CaseCounter).where(CaseCounter.year == now.year).with_for_update()).scalar_one_or_none()
    if counter is None:
        counter = CaseCounter(year=now.year, value=0)
        db.add(counter)
        db.flush()
    counter.value += 1
    report = Report(case_number=f"CS-{now.year}-{counter.value:06d}", source=source, **payload.model_dump(), expires_at=now + timedelta(days=settings.retention_days))
    db.add(report)
    db.flush()
    db.add(CaseHistory(report_id=report.id, action="Reporte creado", details={"source": source}, actor_type="whatsapp" if source == "whatsapp" else "citizen"))
    if commit:
        db.commit()
        db.refresh(report)
    return report
