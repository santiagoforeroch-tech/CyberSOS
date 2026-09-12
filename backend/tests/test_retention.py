import asyncio
from datetime import datetime, timedelta, timezone

from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import get_engine
from app.main import app
from app.models import DeletionAudit, Report
from app.services.retention import delete_expired_reports


def test_retention_requires_confirmation_and_leaves_audit() -> None:
    from sqlalchemy.orm import Session

    with Session(get_engine()) as db:
        report = Report(
            case_number="CS-2026-999999",
            category="phishing",
            description="Descripción ficticia suficientemente extensa para la prueba.",
            reporter_name="Persona de prueba",
            contact_type="email",
            contact_value="prueba@example.com",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        db.add(report)
        db.commit()
        try:
            delete_expired_reports(db)
        except ValueError:
            pass
        else:
            raise AssertionError("La retención debe exigir confirmación")
        assert delete_expired_reports(db, confirm=True) == 1
        assert db.query(DeletionAudit).filter_by(case_number="CS-2026-999999").one().evidence_count == 0


def test_retention_endpoint_requires_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "test-cron-secret")

    async def request() -> tuple[int, int]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.get("/api/internal/retention/run")
            allowed = await client.get("/api/internal/retention/run", headers={"Authorization": "Bearer test-cron-secret"})
            return forbidden.status_code, allowed.status_code

    forbidden, allowed = asyncio.run(request())
    assert forbidden == 401
    assert allowed == 200
