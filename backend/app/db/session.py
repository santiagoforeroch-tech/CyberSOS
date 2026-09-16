from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_engine() -> Engine:
    database_url = settings.database_url
    # Supabase entrega URLs postgresql://; el proyecto usa psycopg v3.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    elif ".pooler.supabase.com:6543" in database_url:
        # El pooler transaccional de Supabase no admite prepared statements.
        connect_args = {"prepare_threshold": None, "options": "-c search_path=private,public"}
    else:
        # Las tablas de CyberSOS viven en el esquema privado de Supabase.
        connect_args = {"options": "-c search_path=private,public"}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def get_db() -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with session_factory() as session:
        yield session
