import datetime as dt
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, require_permission, require_provider
from app.core.security import hash_password, hash_token, new_token
from app.core.serialize import pick
from app.core.storage import get_storage
from app.db import get_db, utcnow
from app.modules.audit.service import audit
from app.modules.catalogue.models import Service, ServiceArea
from app.modules.evidence.service import read_and_validate, safe_filename
from app.modules.identity.models import AuthToken, Role, User
from app.modules.notifications.service import link, notify
from app.modules.providers.models import (REQUIRED_DOC_TYPES, DocType, Provider, ProviderDocument, ProviderStatus, ReviewStatus)

admin = APIRouter(prefix="/admin/providers", tags=["admin: providers"])
self_api = APIRouter(prefix="/provider", tags=["provider portal"])

FIELDS = ("id", "full_name", "phone", "email", "provider_type", "status", "capacity_per_week", "can_be_backup", "interview_at",
          "induction_completed_at", "trial_job_completed_at", "verified_at", "notes", "created_at")
DOC_FIELDS = ("id", "doc_type", "filename", "content_type", "size_bytes", "reference_last4", "issued_at", "expires_at", "review_status", "review_notes", "reviewed_at", "created_at")


def provider_out(p: Provider) -> dict:
    d = pick(p, *FIELDS)
    d["service_ids"] = [s.id for s in p.services]
    d["service_area_ids"] = [a.id for a in p.areas]
    d["has_login"] = p.user_id is not None
    return d


def verification_summary(p: Provider) -> dict:
    approved = {d.doc_type for d in p.documents if d.review_status == ReviewStatus.APPROVED and (d.expires_at is None or d.expires_at > utcnow())}
    checks = {f"document:{t.value}": t in approved for t in REQUIRED_DOC_TYPES}
    checks["interview"] = p.interview_at is not None
    checks["induction"] = p.induction_completed_at is not None
    return {"checks": checks, "ready": all(checks.values())}


class ProviderCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=32)
    email: EmailStr | None = None
    provider_type: str = "individual"
    capacity_per_week: int = Field(default=10, ge=0, le=200)
    can_be_backup: bool = True
    service_ids: list[uuid.UUID] = []
    service_area_ids: list[uuid.UUID] = []
    send_invite: bool = False
    notes: str | None = None


def _apply_links(db, p, service_ids, area_ids):
    if service_ids is not None:
        p.services = list(db.scalars(select(Service).where(Service.id.in_(service_ids)))) if service_ids else []
    if area_ids is not None:
        p.areas = list(db.scalars(select(ServiceArea).where(ServiceArea.id.in_(area_ids)))) if area_ids else []


@admin.get("")
def list_providers(status: ProviderStatus | None = None, user=Depends(require_permission("provider.read")), db: Session = Depends(get_db)):
    q = select(Provider).where(Provider.deleted_at.is_(None)).order_by(Provider.created_at.desc())
    if status:
        q = q.where(Provider.status == status)
    return [provider_out(p) for p in db.scalars(q).all()]


@admin.post("", status_code=201)
def create_provider(body: ProviderCreate, request: Request, user=Depends(require_permission("provider.manage")), db: Session = Depends(get_db)):
    p = Provider(full_name=body.full_name, phone=body.phone, email=body.email, provider_type=body.provider_type,
                 capacity_per_week=body.capacity_per_week, can_be_backup=body.can_be_backup, notes=body.notes)
    db.add(p)
    db.flush()
    _apply_links(db, p, body.service_ids, body.service_area_ids)
    token = None
    if body.send_invite:
        if not body.email:
            raise HTTPException(422, "Email is required to send an invite")
        if db.scalar(select(User).where(User.email == body.email.lower())):
            raise HTTPException(409, "A user with this email already exists")
        role = db.scalar(select(Role).where(Role.name == "provider"))
        u = User(email=body.email.lower(), full_name=body.full_name, phone=body.phone, role_id=role.id, password_hash=hash_password(new_token()))
        db.add(u)
        db.flush()
        p.user_id = u.id
        token = new_token()
        db.add(AuthToken(user_id=u.id, purpose="invite", token_hash=hash_token(token), expires_at=utcnow() + dt.timedelta(days=3)))
    audit(db, actor=user, action="provider.create", entity_type="provider", entity_id=p.id, after={"name": p.full_name}, ip=client_ip(request))
    db.commit()
    if token:
        notify(db, template_key="provider_invite", email=body.email, context={"link": link(f"/reset-password?token={token}")})
    return provider_out(p)


@admin.get("/{provider_id}")
def get_provider(provider_id: uuid.UUID, user=Depends(require_permission("provider.read")), db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p or p.deleted_at:
        raise HTTPException(404, "Not found")
    d = provider_out(p)
    d["documents"] = [pick(x, *DOC_FIELDS) for x in p.documents]
    d["verification"] = verification_summary(p)
    return d


class ProviderPatch(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    capacity_per_week: int | None = Field(default=None, ge=0, le=200)
    can_be_backup: bool | None = None
    interview_at: dt.datetime | None = None
    induction_completed_at: dt.datetime | None = None
    trial_job_completed_at: dt.datetime | None = None
    notes: str | None = None
    service_ids: list[uuid.UUID] | None = None
    service_area_ids: list[uuid.UUID] | None = None


@admin.patch("/{provider_id}")
def patch_provider(provider_id: uuid.UUID, body: ProviderPatch, user=Depends(require_permission("provider.manage")), db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "Not found")
    data = body.model_dump(exclude_unset=True)
    sids, aids = data.pop("service_ids", None), data.pop("service_area_ids", None)
    for k, v in data.items():
        setattr(p, k, v)
    _apply_links(db, p, sids, aids)
    if p.status == ProviderStatus.APPLICANT and p.documents:
        p.status = ProviderStatus.IN_VERIFICATION
    audit(db, actor=user, action="provider.update", entity_type="provider", entity_id=p.id, after=body.model_dump(exclude_unset=True))
    db.commit()
    return provider_out(p)


async def _save_doc(db, provider: Provider, uploader, file, doc_type, last4, expires_at):
    data, ctype = await read_and_validate(file)
    key = f"provider-docs/{provider.id}/{uuid.uuid4()}"
    get_storage().put(key, data, ctype)
    d = ProviderDocument(provider_id=provider.id, doc_type=doc_type, storage_key=key, filename=safe_filename(file.filename), content_type=ctype,
                         size_bytes=len(data), reference_last4=(last4 or None) and last4[-4:], expires_at=expires_at, uploaded_by_user_id=uploader.id)
    db.add(d)
    if provider.status == ProviderStatus.APPLICANT:
        provider.status = ProviderStatus.IN_VERIFICATION
    db.flush()
    return d


@admin.post("/{provider_id}/documents", status_code=201)
async def upload_document(provider_id: uuid.UUID, file: UploadFile = File(...), doc_type: DocType = Form(...), reference_last4: str | None = Form(None),
                          expires_at: dt.datetime | None = Form(None), user=Depends(require_permission("provider.manage")), db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "Not found")
    d = await _save_doc(db, p, user, file, doc_type, reference_last4, expires_at)
    audit(db, actor=user, action="provider_document.upload", entity_type="provider_document", entity_id=d.id)
    db.commit()
    return pick(d, *DOC_FIELDS)


class ReviewBody(BaseModel):
    decision: ReviewStatus
    notes: str | None = Field(default=None, max_length=500)


@admin.post("/documents/{doc_id}/review")
def review_document(doc_id: uuid.UUID, body: ReviewBody, user=Depends(require_permission("provider.verify")), db: Session = Depends(get_db)):
    d = db.get(ProviderDocument, doc_id)
    if not d:
        raise HTTPException(404, "Not found")
    d.review_status, d.review_notes, d.reviewed_by_user_id, d.reviewed_at = body.decision, body.notes, user.id, utcnow()
    audit(db, actor=user, action="provider_document.review", entity_type="provider_document", entity_id=d.id, after={"decision": body.decision})
    db.commit()
    return pick(d, *DOC_FIELDS)


@admin.get("/documents/{doc_id}/url")
def document_url(doc_id: uuid.UUID, user=Depends(require_permission("provider.verify")), db: Session = Depends(get_db)):
    d = db.get(ProviderDocument, doc_id)
    if not d:
        raise HTTPException(404, "Not found")
    audit(db, actor=user, action="provider_document.access", entity_type="provider_document", entity_id=d.id)
    db.commit()
    return {"url": get_storage().signed_url(d.storage_key, d.filename, d.content_type)}


class StatusBody(BaseModel):
    status: ProviderStatus
    reason: str | None = Field(default=None, max_length=500)


@admin.post("/{provider_id}/status")
def set_status(provider_id: uuid.UUID, body: StatusBody, user=Depends(require_permission("provider.verify")), db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "Not found")
    if body.status == ProviderStatus.VERIFIED:
        v = verification_summary(p)
        if not v["ready"]:
            raise HTTPException(409, f"Verification incomplete: {[k for k, ok in v['checks'].items() if not ok]}")
        p.verified_at = utcnow()
    elif body.status in (ProviderStatus.SUSPENDED, ProviderStatus.REJECTED) and not body.reason:
        raise HTTPException(422, "A reason is required")
    before = p.status
    p.status = body.status
    audit(db, actor=user, action="provider.status", entity_type="provider", entity_id=p.id, before={"status": before}, after={"status": body.status, "reason": body.reason})
    db.commit()
    return provider_out(p)


@admin.get("/suggest/{request_id}")
def suggest_for_request(request_id: uuid.UUID, user=Depends(require_permission("provider.read")), db: Session = Depends(get_db)):
    """Verified providers covering the request's service and area."""
    from app.modules.requests.models import ServiceRequest

    req = db.get(ServiceRequest, request_id)
    if not req:
        raise HTTPException(404, "Not found")
    out = []
    for p in db.scalars(select(Provider).where(Provider.status == ProviderStatus.VERIFIED, Provider.deleted_at.is_(None))):
        if p.services and req.service_id not in {s.id for s in p.services}:
            continue
        if req.service_area_id and p.areas and req.service_area_id not in {a.id for a in p.areas}:
            continue
        out.append(provider_out(p))
    return out


@self_api.post("/documents", status_code=201)
async def my_upload(file: UploadFile = File(...), doc_type: DocType = Form(...), reference_last4: str | None = Form(None),
                    expires_at: dt.datetime | None = Form(None), provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    d = await _save_doc(db, provider, provider.user, file, doc_type, reference_last4, expires_at)
    audit(db, actor=provider.user, action="provider_document.upload", entity_type="provider_document", entity_id=d.id)
    db.commit()
    return pick(d, *DOC_FIELDS)


@self_api.get("/documents")
def my_docs(provider: Provider = Depends(require_provider)):
    return [pick(d, *DOC_FIELDS) for d in provider.documents]
