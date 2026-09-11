import asyncio
import json

from httpx import ASGITransport, AsyncClient

import app.models  # noqa: F401
import app.api.admin as admin_api
import app.api.reports as reports_api
from app.core.config import settings
from app.db.session import get_engine
from app.main import app
from app.models.base import Base


def test_citizen_report_and_admin_history(monkeypatch) -> None:
    previous_auth_provider = settings.auth_provider
    settings.auth_provider = "local"
    monkeypatch.setattr(
        reports_api,
        "upload_evidence",
        lambda report_id, items: [{
            "storage_key": f"{report_id}/prueba.png",
            "original_name": items[0].original_name,
            "mime_type": items[0].mime_type,
            "size_bytes": len(items[0].content),
            "sha256": items[0].sha256,
        }],
    )
    monkeypatch.setattr(admin_api, "create_download_url", lambda storage_key: f"https://storage.example/{storage_key}")
    Base.metadata.create_all(get_engine())

    async def run_flow():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            direct_mfa = await client.post("/api/v1/auth/mfa/verify", json={"code": "123456"})
            assert direct_mfa.status_code == 401

            payload = {
                "category": "phishing",
                "description": "Recibí un enlace ficticio que solicitaba ingresar mis credenciales.",
                "reporter_name": "Persona de prueba",
                "contact_type": "email",
                "contact_value": "prueba@example.com",
            }
            rejected = await client.post(
                "/api/v1/reports",
                data={"payload": json.dumps(payload)},
                files={"evidence": ("falsa.png", b"esto-no-es-una-imagen", "image/png")},
            )
            assert rejected.status_code == 422
            created = await client.post(
                "/api/v1/reports",
                data={"payload": json.dumps(payload)},
                files={"evidence": ("prueba.png", b"\x89PNG\r\n\x1a\ncontenido-ficticio", "image/png")},
            )
            assert created.status_code == 201
            assert created.json()["case_number"].startswith("CS-")
            assert created.json()["evidence_count"] == 1

            login = await client.post("/api/v1/auth/login", json={"email": "admin@cybersos.example", "password": "CyberSOS-Demo-2026"})
            assert login.status_code == 200
            assert (await client.post("/api/v1/auth/mfa/verify", json={"code": "123456"})).status_code == 200
            reports = await client.get("/api/v1/admin/reports")
            assert reports.status_code == 200
            assert reports.json()["items"][0]["case_number"] == created.json()["case_number"]
            statistics = await client.get("/api/v1/admin/statistics")
            assert statistics.status_code == 200
            assert statistics.json()["by_category"]["phishing"] >= 1
            assert statistics.json()["by_priority"]["Media"] >= 1
            detail = await client.get(f"/api/v1/admin/reports/{reports.json()['items'][0]['id']}")
            assert detail.status_code == 200
            assert detail.json()["evidences"][0]["original_name"] == "prueba.png"
            evidence_id = detail.json()["evidences"][0]["id"]
            download = await client.post(f"/api/v1/admin/evidences/{evidence_id}/download-url")
            assert download.status_code == 200
            assert download.json()["expires_in"] == 60
            assert (await client.post("/api/v1/auth/logout")).status_code == 204
            assert (await client.get("/api/v1/admin/reports")).status_code == 401

    try:
        asyncio.run(run_flow())
    finally:
        settings.auth_provider = previous_auth_provider
