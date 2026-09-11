import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from supabase import Client, create_client

from app.core.config import settings

BUCKET = "cybersos-evidence"
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_FILES = 5
ALLOWED_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),
}
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


@dataclass(frozen=True)
class PreparedEvidence:
    original_name: str
    mime_type: str
    content: bytes
    sha256: str


def storage_client() -> Client:
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(503, "El almacenamiento seguro todavía no está configurado")
    return create_client(settings.supabase_url, settings.supabase_secret_key)


async def prepare_evidence(files: list[UploadFile]) -> list[PreparedEvidence]:
    if len(files) > MAX_FILES:
        raise HTTPException(422, "Puedes adjuntar máximo cinco imágenes")
    prepared = []
    for file in files:
        mime_type = (file.content_type or "").lower()
        if mime_type not in ALLOWED_SIGNATURES:
            raise HTTPException(422, "Solo se permiten imágenes PNG, JPEG o WebP")
        content = await file.read(MAX_FILE_SIZE + 1)
        if not content or len(content) > MAX_FILE_SIZE:
            raise HTTPException(422, "Cada evidencia debe pesar entre 1 byte y 10 MB")
        valid_signature = any(content.startswith(signature) for signature in ALLOWED_SIGNATURES[mime_type])
        if mime_type == "image/webp":
            valid_signature = valid_signature and len(content) >= 12 and content[8:12] == b"WEBP"
        if not valid_signature:
            raise HTTPException(422, "El contenido del archivo no coincide con su tipo de imagen")
        safe_name = Path(file.filename or "evidencia").name[:255]
        prepared.append(PreparedEvidence(safe_name, mime_type, content, hashlib.sha256(content).hexdigest()))
    return prepared


def upload_evidence(report_id: str, items: list[PreparedEvidence]) -> list[dict]:
    client = storage_client()
    uploaded_keys: list[str] = []
    records = []
    try:
        for item in items:
            storage_key = f"{report_id}/{uuid4().hex}{EXTENSIONS[item.mime_type]}"
            client.storage.from_(BUCKET).upload(
                path=storage_key,
                file=item.content,
                file_options={"content-type": item.mime_type, "cache-control": "3600", "upsert": "false"},
            )
            uploaded_keys.append(storage_key)
            records.append({
                "storage_key": storage_key,
                "original_name": item.original_name,
                "mime_type": item.mime_type,
                "size_bytes": len(item.content),
                "sha256": item.sha256,
            })
        return records
    except Exception as error:
        if uploaded_keys:
            client.storage.from_(BUCKET).remove(uploaded_keys)
        raise HTTPException(502, "No fue posible guardar las evidencias de forma segura") from error


def create_download_url(storage_key: str) -> str:
    response = storage_client().storage.from_(BUCKET).create_signed_url(storage_key, 60)
    if isinstance(response, dict):
        return response.get("signedURL") or response.get("signedUrl") or response.get("signed_url") or ""
    return getattr(response, "signed_url", "") or getattr(response, "signedURL", "")


def remove_evidence(storage_keys: list[str]) -> None:
    if storage_keys:
        storage_client().storage.from_(BUCKET).remove(storage_keys)
