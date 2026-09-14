from fastapi import APIRouter

from app.api.whatsapp import admin_router as whatsapp_admin_router, internal_router as whatsapp_internal_router
from app.core.config import settings

from app.schemas.health import HealthResponse
from app.api import admin, agent, auth, reports, system

api_router = APIRouter()
api_router.include_router(reports.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(system.router)
api_router.include_router(agent.router)


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    database = "sqlite" if settings.database_url.startswith("sqlite") else "postgresql"
    return HealthResponse(status="ok", database=database)

api_router.include_router(whatsapp_internal_router)
if settings.app_env == "development" and settings.whatsapp_admin_local:
    api_router.include_router(whatsapp_admin_router)
