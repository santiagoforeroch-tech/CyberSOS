import asyncio

from httpx import ASGITransport, AsyncClient

import app.db.session as db_session
from app.core.config import settings
from app.db.session import get_engine
from app.main import app


def test_health() -> None:
    async def request_health():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "sqlite"}


def test_supabase_transaction_pooler_uses_psycopg_without_prepared_statements(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql://postgres.example:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres",
    )
    captured = {}

    def capture_engine(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(db_session, "create_engine", capture_engine)
    get_engine.cache_clear()
    get_engine()

    assert captured["url"].startswith("postgresql+psycopg://")
    assert captured["connect_args"]["prepare_threshold"] is None
