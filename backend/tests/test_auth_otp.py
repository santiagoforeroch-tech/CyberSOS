import asyncio
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

import app.api.auth as auth_api
from app.core.config import settings
from app.core.security import sign_token
from app.main import app


def test_email_otp_creates_admin_session_with_response_session_tokens(monkeypatch) -> None:
    class FakeAuth:
        def verify_otp(self, payload):
            assert payload == {
                "email": "admin@cybersos.example",
                "token": "12345678",
                "type": "email",
            }
            return SimpleNamespace(
                user=SimpleNamespace(
                    email="admin@cybersos.example",
                    app_metadata={"role": "admin", "setup_complete": True},
                ),
                session=SimpleNamespace(access_token="test-access", refresh_token="test-refresh"),
            )

    monkeypatch.setattr(settings, "auth_provider", "supabase")
    monkeypatch.setattr(auth_api, "auth_client", lambda: SimpleNamespace(auth=FakeAuth()))

    async def verify():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://test") as client:
            client.cookies.set("mfa_pending", sign_token("mfa-pending", 300))
            client.cookies.set("mfa_email", "admin@cybersos.example")
            return await client.post("/api/v1/auth/mfa/verify", json={"code": "12345678"})

    response = asyncio.run(verify())
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "aal": "aal2"}
    assert "sb_access_token=test-access" in response.headers["set-cookie"]
