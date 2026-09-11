import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(title="CyberSOS")
allowed_origins = [settings.frontend_origin]
if settings.app_env == "development":
    allowed_origins.extend([
        "http://localhost:4174",
        "http://127.0.0.1:4174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Vercel Services ya retira el prefijo /api antes de entregar la petición a
# FastAPI. Localmente se conserva para no cambiar las URLs de desarrollo.
api_prefix = "" if os.getenv("VERCEL") else "/api"
app.include_router(api_router, prefix=api_prefix)
