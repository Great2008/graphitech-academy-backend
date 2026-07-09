"""
app/services/storage_service.py

Thin wrapper around Supabase Storage for uploading generated files
(certificate PDFs, QR codes, lesson media, project cover images).
Centralized here so the bucket/client setup only happens once.
"""

from supabase import create_client, Client

from app.core.config import settings

_client: Client | None = None


def get_storage_client() -> Client:
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("Supabase storage is not configured (missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _client


def upload_file(path: str, content: bytes, content_type: str) -> str:
    """
    Uploads a file to the configured storage bucket and returns its public URL.
    `path` should be a storage-relative path, e.g. "certificates/GTA-2026-WD-000123.pdf".
    """
    client = get_storage_client()
    bucket = client.storage.from_(settings.SUPABASE_STORAGE_BUCKET)

    bucket.upload(
        path=path,
        file=content,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    return bucket.get_public_url(path)
