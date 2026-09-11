from __future__ import annotations

import hashlib
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import UploadFile

from app.core.config import settings


class WhatsAppStorage:
    bucket = "whatsapp-media"

    def _headers(self) -> dict[str, str]:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Supabase Storage todavía no está configurado")
        return {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
        }

    async def upload(self, file: UploadFile, conversation_key: str = "outbound") -> dict[str, Any]:
        limit = settings.whatsapp_max_media_mb * 1024 * 1024
        digest = hashlib.sha256()
        size = 0
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as temporary:
            while chunk := await file.read(64 * 1024):
                size += len(chunk)
                if size > limit:
                    raise ValueError(f"El archivo supera {settings.whatsapp_max_media_mb} MiB")
                digest.update(chunk)
                temporary.write(chunk)
            temporary.seek(0)
            filename = self._safe_filename(file.filename or "archivo")
            safe_conversation = re.sub(r"[^a-zA-Z0-9_.-]", "_", conversation_key)
            path = f"{safe_conversation}/{uuid.uuid4()}-{filename}"
            url = f"{settings.supabase_url}/storage/v1/object/{self.bucket}/{path}"
            headers = {**self._headers(), "Content-Type": file.content_type or "application/octet-stream", "x-upsert": "false"}

            async def chunks():
                while chunk := temporary.read(64 * 1024):
                    yield chunk

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, headers=headers, content=chunks())
            response.raise_for_status()
        return {
            "storage_path": path,
            "mime_type": file.content_type or "application/octet-stream",
            "size_bytes": size,
            "sha256": digest.hexdigest(),
            "original_filename": filename,
        }

    async def signed_url(self, path: str, expires_in: int = 300) -> str:
        if not 30 <= expires_in <= 300:
            raise ValueError("La URL firmada debe durar entre 30 y 300 segundos")
        url = f"{settings.supabase_url}/storage/v1/object/sign/{self.bucket}/{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=self._headers(), json={"expiresIn": expires_in})
        response.raise_for_status()
        signed = response.json()["signedURL"]
        return f"{settings.supabase_url}/storage/v1{signed}"

    @staticmethod
    def _safe_filename(filename: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(filename).name).strip("._")
        return clean[:120] or "archivo"
