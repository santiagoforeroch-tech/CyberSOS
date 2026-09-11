"""Aislamiento de pruebas: nunca usar la base configurada para desarrollo."""

import app.models  # noqa: F401
import pytest

from app.core.config import settings
from app.db.session import get_engine
from app.models.base import Base


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Cada prueba usa SQLite temporal, incluso si .env apunta a Supabase."""
    database_path = (tmp_path / "cybersos-test.db").as_posix()
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{database_path}")
    # Las credenciales de prueba son fijas y no dependen de valores privados
    # configurados por cada persona en su archivo .env local.
    monkeypatch.setattr(settings, "local_admin_email", "admin@cybersos.example")
    monkeypatch.setattr(settings, "local_admin_password", "CyberSOS-Demo-2026")
    monkeypatch.setattr(settings, "local_mfa_code", "123456")
    monkeypatch.setattr(settings, "session_secret", "cybersos-test-session-secret")
    get_engine.cache_clear()
    Base.metadata.create_all(get_engine())
    yield
    get_engine.cache_clear()
