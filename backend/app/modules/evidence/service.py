import datetime as dt
import hashlib
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import get_storage, scan_for_malware, validate_upload
from app.db import utcnow
from app.modules.evidence.models import AccessScope, Evidence, EvidencePurpose, ScanStatus
from app.modules.families.service import active_consent


async def read_and_validate(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read(settings.upload_max_bytes + 1)
    ctype = (file.content_type or "").lower()
    err = validate_upload(data, ctype)
    if err:
        raise HTTPException(422, err)
    return data, ctype


def safe_filename(name: str | None) -> str:
    name = (name or "upload").replace("\\", "/").split("/")[-1]
    return "".join(c for c in name if c.isalnum() or c in "._- ")[:120] or "upload"


def store_evidence(db: Session, *, req, assignment, uploader, data: bytes, ctype: str, filename: str,
                   purpose: EvidencePurpose, scope: AccessScope, caption: str | None) -> Evidence:
    if purpose == EvidencePurpose.COMPLETION_PHOTO and not active_consent(db, req.parent_id, "photographs"):
        raise HTTPException(403, "The parent has not consented to photographs for this service. Photo upload is not permitted.")
    key = f"evidence/{req.id}/{uuid.uuid4()}"
    get_storage().put(key, data, ctype)
    ev = Evidence(
        request_id=req.id, assignment_id=getattr(assignment, "id", None), uploader_user_id=uploader.id, storage_key=key,
        filename=safe_filename(filename), content_type=ctype, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        purpose=purpose, access_scope=scope, caption=caption, scan_status=ScanStatus(scan_for_malware(data)),
        retain_until=utcnow() + dt.timedelta(days=settings.evidence_retention_days),
    )
    db.add(ev)
    db.flush()
    return ev


def evidence_summary(ev: Evidence) -> dict:
    return {"id": ev.id, "filename": ev.filename, "content_type": ev.content_type, "size_bytes": ev.size_bytes,
            "purpose": ev.purpose, "access_scope": ev.access_scope, "caption": ev.caption, "created_at": ev.created_at}


def signed_link(ev: Evidence) -> str:
    return get_storage().signed_url(ev.storage_key, ev.filename, ev.content_type)
