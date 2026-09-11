"""Inicializa únicamente la base SQLite local con datos ficticios."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.core.config import settings
from app.db.session import get_engine
from app.models.base import Base

if not settings.database_url.startswith("sqlite"):
    print("Base remota configurada: no se crean tablas automáticamente.")
    raise SystemExit(0)

Base.metadata.create_all(get_engine())
print("Base de desarrollo inicializada")
