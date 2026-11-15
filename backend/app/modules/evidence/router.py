import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, require_customer, require_permission
from app.core.serialize import pick
from app.core.storage import get_storage, verify_local_token
from app.db import get_db
from app.modules.audit.service import audit
from app.modules.evidence.models import AccessScope, ChecklistTemplate, Evidence
from app.modules.evidence.service import evidence_summary, signed_link
from app.modules.families.models import Customer
from app.modules.families.service import customer_authorisation
from app.modules.requests.models import ServiceRequest
from app.modules.requests.router import load, load_for_customer

router = APIRouter(tags=["evidence"])


@router.get("/admin/requests/{request_id}/evidence")
def admin_list(request_id: uuid.UUID, request: Request, user=Depends(require_permission("evidence.review")), db: Session = Depends(get_db)):
    req = load(db, request_id)
    rows = db.scalars(select(Evidence).where(Evidence.request_id == req.id, Evidence.deleted_at.is_(None))).all()
    return [evidence_summary(e) for e in rows]


@router.get("/admin/evidence/{evidence_id}/url")
def admin_url(evidence_id: uuid.UUID, request: Request, user=Depends(require_permission("evidence.review")), db: Session = Depends(get_db)):
    ev = db.get(Evidence, evidence_id)
    if not ev or ev.deleted_at:
        raise HTTPException(404, "Not found")
    audit(db, actor=user, action="evidence.access", entity_type="evidence", entity_id=ev.id, ip=client_ip(request))
    db.commit()
    return {"url": signed_link(ev)}


class ScopeBody(BaseModel):
    access_scope: AccessScope


@router.patch("/admin/evidence/{evidence_id}")
def set_scope(evidence_id: uuid.UUID, body: ScopeBody, user=Depends(require_permission("evidence.review")), db: Session = Depends(get_db)):
    ev = db.get(Evidence, evidence_id)
    if not ev:
        raise HTTPException(404, "Not found")
    audit(db, actor=user, action="evidence.scope_change", entity_type="evidence", entity_id=ev.id,
          before={"access_scope": ev.access_scope}, after={"access_scope": body.access_scope})
    ev.access_scope = body.access_scope
    db.commit()
    return evidence_summary(ev)


def _customer_evidence(db, customer, ev):
    req = db.get(ServiceRequest, ev.request_id)
    auth = customer_authorisation(db, customer.id, req.parent_id)
    own = customer.id in (req.customer_id, req.requestor_customer_id)
    return ev.access_scope == AccessScope.CUSTOMER_VISIBLE and (own or (auth and auth.can_view_evidence and auth.status.value == "active"))


@router.get("/portal/requests/{request_id}/evidence")
def customer_list(request_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    req = load_for_customer(db, customer, request_id)
    rows = db.scalars(select(Evidence).where(Evidence.request_id == req.id, Evidence.deleted_at.is_(None))).all()
    return [evidence_summary(e) for e in rows if _customer_evidence(db, customer, e)]


@router.get("/portal/evidence/{evidence_id}/url")
def customer_url(evidence_id: uuid.UUID, request: Request, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    ev = db.get(Evidence, evidence_id)
    if not ev or ev.deleted_at or not _customer_evidence(db, customer, ev):
        raise HTTPException(404, "Not found")
    audit(db, actor=customer.user, action="evidence.access", entity_type="evidence", entity_id=ev.id, ip=client_ip(request))
    db.commit()
    return {"url": signed_link(ev)}


@router.get("/files/{token}", include_in_schema=False)
def local_file(token: str):
    """Serves files for the local dev storage backend via short-lived signed tokens (S3 uses presigned URLs)."""
    data = verify_local_token(token)
    if not data:
        raise HTTPException(403, "Link expired or invalid")
    try:
        body = get_storage().get(data["k"])
    except Exception:
        raise HTTPException(404, "Not found")
    return Response(body, media_type=data["c"], headers={"Content-Disposition": f'inline; filename="{data["f"]}"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


# ---- checklist templates (admin) ----
class TemplateBody(BaseModel):
    service_id: uuid.UUID
    name: str
    items: list[dict]  # [{key,label,required}]


@router.get("/admin/checklist-templates")
def list_templates(user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    return [pick(t, "id", "service_id", "name", "items", "is_active") for t in db.scalars(select(ChecklistTemplate)).all()]


@router.post("/admin/checklist-templates", status_code=201)
def create_template(body: TemplateBody, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    for t in db.scalars(select(ChecklistTemplate).where(ChecklistTemplate.service_id == body.service_id, ChecklistTemplate.is_active.is_(True))):
        t.is_active = False
    t = ChecklistTemplate(service_id=body.service_id, name=body.name, items=body.items)
    db.add(t)
    audit(db, actor=user, action="checklist_template.create", entity_type="checklist_template", entity_id=None, after=body.model_dump())
    db.commit()
    return pick(t, "id", "service_id", "name", "items", "is_active")
