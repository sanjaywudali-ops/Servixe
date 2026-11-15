"""Private object storage. Files are never public; access is through short-lived signed URLs."""
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from app.core.config import settings


class StorageError(Exception):
    pass


class LocalStorage:
    """Development/test backend. Signed URLs point at the API's /files endpoint."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise StorageError("invalid key")
        return p

    def put(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def signed_url(self, key: str, filename: str, content_type: str, ttl: int | None = None) -> str:
        exp = int(time.time()) + (ttl or settings.signed_url_ttl_seconds)
        payload = base64.urlsafe_b64encode(json.dumps({"k": key, "e": exp, "f": filename, "c": content_type}).encode()).decode()
        sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{settings.api_prefix}/files/{payload}.{sig}"


class S3Storage:
    def __init__(self):
        import boto3

        self.client = boto3.client("s3", region_name=settings.s3_region, endpoint_url=settings.s3_endpoint_url)
        self.bucket = settings.s3_bucket

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256"
        )

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def signed_url(self, key: str, filename: str, content_type: str, ttl: int | None = None) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket, "Key": key, "ResponseContentType": content_type,
                "ResponseContentDisposition": f'inline; filename="{filename}"',
            },
            ExpiresIn=ttl or settings.signed_url_ttl_seconds,
        )


def verify_local_token(token: str) -> dict | None:
    try:
        payload, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    except Exception:
        return None
    if data["e"] < time.time():
        return None
    return data


_storage = None


def get_storage():
    global _storage
    if _storage is None:
        _storage = S3Storage() if settings.storage_backend == "s3" else LocalStorage(settings.local_storage_dir)
    return _storage


def set_storage(s) -> None:
    global _storage
    _storage = s


# --- upload validation -------------------------------------------------------------------------
MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
    "application/pdf": (b"%PDF-",),
}


def validate_upload(data: bytes, declared_type: str) -> str | None:
    """Return an error message, or None if the file is acceptable."""
    if declared_type not in settings.allowed_upload_types:
        return f"File type {declared_type} is not allowed."
    if not data:
        return "Empty file."
    if len(data) > settings.upload_max_bytes:
        return f"File exceeds the {settings.upload_max_bytes // (1024 * 1024)} MB limit."
    sigs = MAGIC.get(declared_type)
    if sigs and not any(data.startswith(s) for s in sigs):
        return "File content does not match its declared type."
    if declared_type == "image/webp" and data[8:12] != b"WEBP":
        return "File content does not match its declared type."
    return None


def scan_for_malware(data: bytes) -> str:
    """Hook for malware scanning (e.g. ClamAV sidecar or S3 GuardDuty Malware Protection).
    Returns a ScanStatus value. Replace with a real scanner before production launch."""
    return "skipped"
