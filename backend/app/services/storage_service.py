"""
NDIP Phase D.3 — Cloud Storage Service (D3.5)
File: app/services/storage_service.py

Google Cloud Storage abstraction. All file operations go through this
service — no code outside this module references GCS directly.

Design:
  - Signed URLs for all private asset access (15-minute default TTL)
  - MIME type validation before upload acceptance
  - File size enforcement per asset type
  - Metadata stored in media_assets table
  - Secure deletion (GCS object removal + metadata soft-delete)
  - Local filesystem fallback for development (no GCS credentials needed)

GCS credentials: standard Application Default Credentials (ADC).
Set GCS_BUCKET env var to enable GCS. Without it, files are written
to LOCAL_STORAGE_PATH (defaults to /app/uploads/).

Upload flow:
  1. Caller provides file bytes + metadata
  2. Service validates MIME type and size
  3. Service writes to GCS (or local fallback)
  4. Service persists metadata to media_assets table
  5. Service returns signed URL (or local path)
"""
import hashlib
import mimetypes
import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import utcnow

# ─── Configuration ─────────────────────────────────────────────────────────

GCS_BUCKET = os.getenv("GCS_BUCKET", "")
GCS_PREFIX = os.getenv("GCS_PREFIX", "ndip")
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", "/app/uploads")
SIGNED_URL_TTL_MINUTES = int(os.getenv("SIGNED_URL_TTL_MINUTES", "15"))

# Per-asset-type size limits (bytes)
SIZE_LIMITS = {
    "image":    10 * 1024 * 1024,   # 10 MB
    "video":   500 * 1024 * 1024,   # 500 MB
    "pdf":      25 * 1024 * 1024,   # 25 MB
    "document": 25 * 1024 * 1024,   # 25 MB
    "evidence": 50 * 1024 * 1024,   # 50 MB
    "other":    10 * 1024 * 1024,   # 10 MB
}

# Allowed MIME types per asset type
ALLOWED_MIMES = {
    "image":    {"image/jpeg", "image/png", "image/webp", "image/gif"},
    "video":    {"video/mp4", "video/webm", "video/quicktime", "video/avi"},
    "pdf":      {"application/pdf"},
    "document": {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
    },
    "evidence": {
        "image/jpeg", "image/png", "image/webp",
        "application/pdf",
        "video/mp4", "video/webm",
    },
    "other":    None,  # None = no restriction (use with caution)
}


# ─── Exceptions ────────────────────────────────────────────────────────────

class StorageError(Exception):
    pass

class FileTooLargeError(StorageError):
    pass

class InvalidMimeTypeError(StorageError):
    pass

class AssetNotFoundError(StorageError):
    pass


# ─── GCS Backend ───────────────────────────────────────────────────────────

class GCSBackend:
    """Google Cloud Storage backend. Requires google-cloud-storage package
    and ADC credentials. Installed in requirements.txt as
    google-cloud-storage>=2.0.0 (add to requirements.txt for GCP deploy)."""

    def __init__(self, bucket_name: str):
        try:
            from google.cloud import storage as gcs
            self._client = gcs.Client()
            self._bucket = self._client.bucket(bucket_name)
            self._bucket_name = bucket_name
        except ImportError:
            raise RuntimeError(
                "google-cloud-storage is not installed. "
                "Run: pip install google-cloud-storage"
            )

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes to GCS. Returns the gs:// URI."""
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self._bucket_name}/{key}"

    def signed_url(self, key: str, ttl_minutes: int = SIGNED_URL_TTL_MINUTES) -> str:
        """Generate a v4 signed URL for temporary access."""
        blob = self._bucket.blob(key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=ttl_minutes),
            method="GET",
        )

    def delete(self, key: str) -> None:
        """Delete an object from GCS."""
        blob = self._bucket.blob(key)
        if blob.exists():
            blob.delete()

    def exists(self, key: str) -> bool:
        return self._bucket.blob(key).exists()


class LocalBackend:
    """Development fallback — stores files on the local filesystem.
    Signed URLs are just local file paths (suitable for development only)."""

    def __init__(self, base_path: str = LOCAL_STORAGE_PATH):
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def signed_url(self, key: str, ttl_minutes: int = SIGNED_URL_TTL_MINUTES) -> str:
        # In dev, just return the local path as a "URL"
        return f"file://{self._base}/{key}"

    def delete(self, key: str) -> None:
        path = self._base / key
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return (self._base / key).exists()


def _get_backend():
    if GCS_BUCKET:
        return GCSBackend(GCS_BUCKET)
    return LocalBackend()


# ─── Storage Service ───────────────────────────────────────────────────────

class StorageService:
    def __init__(self, db: Session):
        self.db = db
        self._backend = _get_backend()

    def upload(
        self,
        *,
        file_bytes: bytes,
        original_name: str,
        asset_type: str,
        entity_type: str,
        entity_id: Optional[UUID] = None,
        uploaded_by: Optional[UUID] = None,
        is_public: bool = False,
        override_mime: Optional[str] = None,
    ) -> dict:
        """
        Validate, store, and record a file upload.
        Returns a dict with the media_asset record fields + signed_url.
        """
        # Detect MIME type
        detected_mime = override_mime or mimetypes.guess_type(original_name)[0] or "application/octet-stream"

        # Validate MIME
        allowed = ALLOWED_MIMES.get(asset_type)
        if allowed is not None and detected_mime not in allowed:
            raise InvalidMimeTypeError(
                f"File type '{detected_mime}' is not allowed for asset type '{asset_type}'. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )

        # Validate size
        size_limit = SIZE_LIMITS.get(asset_type, SIZE_LIMITS["other"])
        if len(file_bytes) > size_limit:
            raise FileTooLargeError(
                f"File size {len(file_bytes):,} bytes exceeds the "
                f"{size_limit // (1024*1024)} MB limit for {asset_type} assets."
            )

        # Build GCS key
        asset_id = uuid.uuid4()
        ext = Path(original_name).suffix.lower()
        gcs_key = f"{GCS_PREFIX}/{entity_type}/{asset_id}{ext}"
        bucket = GCS_BUCKET or "local"

        # Upload
        self._backend.upload(gcs_key, file_bytes, detected_mime)

        # Persist metadata
        self.db.execute(text("""
            INSERT INTO media_assets
                (id, uploaded_by, entity_type, entity_id, asset_type,
                 original_name, gcs_bucket, gcs_key, mime_type, size_bytes, is_public)
            VALUES
                (CAST(:id AS UUID), CAST(:uploaded_by AS UUID), :entity_type,
                 CAST(:entity_id AS UUID), :asset_type, :original_name,
                 :gcs_bucket, :gcs_key, :mime_type, :size_bytes, :is_public)
        """), {
            "id": str(asset_id),
            "uploaded_by": str(uploaded_by) if uploaded_by else None,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "asset_type": asset_type,
            "original_name": original_name[:500],
            "gcs_bucket": bucket,
            "gcs_key": gcs_key,
            "mime_type": detected_mime,
            "size_bytes": len(file_bytes),
            "is_public": is_public,
        })
        self.db.commit()

        signed_url = self._backend.signed_url(gcs_key)

        return {
            "id": str(asset_id),
            "original_name": original_name,
            "asset_type": asset_type,
            "mime_type": detected_mime,
            "size_bytes": len(file_bytes),
            "gcs_key": gcs_key,
            "signed_url": signed_url,
            "is_public": is_public,
        }

    def get_signed_url(self, asset_id: UUID, ttl_minutes: int = SIGNED_URL_TTL_MINUTES) -> str:
        """Generate a fresh signed URL for an existing asset."""
        row = self.db.execute(text("""
            SELECT gcs_key, is_public, deleted_at
            FROM media_assets
            WHERE id = CAST(:id AS UUID)
        """), {"id": str(asset_id)}).fetchone()

        if row is None:
            raise AssetNotFoundError(f"Asset {asset_id} not found.")
        if row.deleted_at is not None:
            raise AssetNotFoundError(f"Asset {asset_id} has been deleted.")

        if row.is_public:
            if GCS_BUCKET:
                return f"https://storage.googleapis.com/{GCS_BUCKET}/{row.gcs_key}"
            return self._backend.signed_url(row.gcs_key, ttl_minutes)

        return self._backend.signed_url(row.gcs_key, ttl_minutes)

    def delete_asset(self, asset_id: UUID, deleted_by: Optional[UUID] = None) -> None:
        """Soft-delete in DB + hard-delete from storage."""
        row = self.db.execute(text("""
            SELECT gcs_key, deleted_at FROM media_assets
            WHERE id = CAST(:id AS UUID)
        """), {"id": str(asset_id)}).fetchone()

        if row is None:
            raise AssetNotFoundError(f"Asset {asset_id} not found.")
        if row.deleted_at is not None:
            return  # Already deleted — idempotent

        # Hard delete from storage
        try:
            self._backend.delete(row.gcs_key)
        except Exception:
            pass  # Storage delete failure should not block DB soft-delete

        # Soft delete in DB
        self.db.execute(text("""
            UPDATE media_assets
            SET deleted_at = now()
            WHERE id = CAST(:id AS UUID)
        """), {"id": str(asset_id)})
        self.db.commit()

    def list_assets(
        self,
        entity_type: str,
        entity_id: UUID,
        include_deleted: bool = False,
    ) -> list:
        """List all assets for a given entity."""
        where = "WHERE entity_type = :entity_type AND entity_id = CAST(:entity_id AS UUID)"
        if not include_deleted:
            where += " AND deleted_at IS NULL"

        rows = self.db.execute(text(f"""
            SELECT id, original_name, asset_type, mime_type, size_bytes,
                   gcs_key, is_public, created_at, deleted_at
            FROM media_assets
            {where}
            ORDER BY created_at DESC
        """), {"entity_type": entity_type, "entity_id": str(entity_id)}).fetchall()

        result = []
        for row in rows:
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            if d["deleted_at"] is None:
                try:
                    d["signed_url"] = self._backend.signed_url(d["gcs_key"])
                except Exception:
                    d["signed_url"] = None
            else:
                d["signed_url"] = None
            result.append(d)
        return result
