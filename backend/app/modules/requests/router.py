import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, current_user, require_customer, require_permission
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.audit.service import audit
from app.modules.catalogue.models import Service
from app.modules.families.models import AuthStatus, Customer, FamilyAuthorisation, Parent
from app.modules.families.service import customer_authorisation, next_reference
from app.modules.notifications.service import link, notify
from app.modules.requests import workflow as wf
from app.modules.requests.models import Priority, RequestEvent, RequestStatus, ServiceRequest, Source

portal = APIRouter(prefix="/portal/requests", tags=["customer: requests"])
admin = APIRouter(prefix="/admin/requests", tags=["admin: requests"])

CUSTOMER_FIELDS = (
    "id", "reference", "parent_id", "service_id", "status", "priority", "task_details", "location_text",
    "requested_start", "requested_end", "budget_cap_minor", "currency", "created_at", "completed_at", "cancel_reason",
)


def customer_view(req: ServiceRequest) -> dict:
    d = pick(req, *CUSTOMER_FIELDS)
    d["service_name"] = req.service.name
    d["parent_name"] = req.parent.full_name
    return d


def ops_view(req: ServiceRequest) -> dict:
    d = customer_view(req)
    d.update(pick(req, "customer_id", "requestor_customer_id", "service_area_id", "source", "consent_id", "consent_scope",
                  "approval_exception_reason", "quality_outcome", "quality_notes", "internal_notes", "closed_at"))
    return d


def customer_can_access(db: Session, customer: Customer, req: ServiceRequest) -> bool:
    if customer.id in (req.customer_id, req.requestor_customer_id):
        return True
    a = customer_authorisation(db, customer.id, req.parent_id)
    return bool(a and a.can_receive_updates and a.status.value == "active")


def load_for_customer(db: Session, customer: Customer, request_id) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req or req.deleted_at or not customer_can_access(db, customer, req):
        raise HTTPException(404, "Request not found")
    return req


def load(db: Session, request_id) -> ServiceRequest:
    req = db.get(ServiceRequest, request_id)
    if not req or req.deleted_at:
        raise HTTPException(404, "Request not found")
    return req


class RequestCreate(BaseModel):
    parent_id: uuid.UUID
    service_id: uuid.UUID
    task_details: str = Field(min_length=5, max_length=2000)
    requested_start: dt.datetime | None = None
    requested_end: dt.datetime | None = None
    location_text: str | None = Field(default=None, max_length=500)
    priority: Priority = Priority.NORMAL
    budget_cap_minor: int | None = Field(default=None, ge=0)


def _create(db: Session, customer: Customer, body: RequestCreate, source: Source, actor, ip) -> ServiceRequest:
    parent = db.get(Parent, body.parent_id)
    auth = customer_authorisation(db, customer.id, body.parent_id) if parent else None
    if not parent or not auth:
        raise HTTPException(404, "Parent not found")
    if not auth.can_request_services:
        raise HTTPException(403, "You are not authorised to request services for this parent")
    svc = db.get(Service, body.service_id)
    if not svc or not svc.is_active:
        raise HTTPException(404, "Service not available")
    if body.requested_start and body.requested_end and body.requested_end <= body.requested_start:
        raise HTTPException(422, "End time must be after start time")
    req = ServiceRequest(
        reference=next_reference(db, "request", "SX"), customer_id=customer.id, requestor_customer_id=customer.id,
        parent_id=parent.id, service_id=svc.id, service_area_id=parent.service_area_id, source=source,
        task_details=body.task_details, requested_start=body.requested_start, requested_end=body.requested_end,
        location_text=body.location_text or ", ".join(x for x in [parent.address_line, parent.area, parent.city] if x),
        priority=body.priority, budget_cap_minor=body.budget_cap_minor, currency=customer.preferred_currency,
        consent_scope=svc.required_consent_scope,
    )
    db.add(req)
    db.flush()
    wf.add_event(db, req, actor, "created", f"Request received via {source.value}", None, RequestStatus.NEW_REQUEST, True)
    audit(db, actor=actor, action="request.create", entity_type="service_request", entity_id=req.id, after={"reference": req.reference}, ip=ip)
    return req


@portal.post("", status_code=201)
def create_request(body: RequestCreate, request: Request, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    req = _create(db, customer, body, Source.PORTAL, customer.user, client_ip(request))
    db.commit()
    notify(db, template_key="request_received", user=customer.user, request_id=req.id,
           context={"reference": req.reference, "link": link(f"/portal/requests/{req.id}")})
    return customer_view(req)


@portal.get("")
def list_requests(customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    auth_parent_ids = select(FamilyAuthorisation.parent_id).where(
        FamilyAuthorisation.customer_id == customer.id, FamilyAuthorisation.can_receive_updates.is_(True), FamilyAuthorisation.status == AuthStatus.ACTIVE)
    rows = db.scalars(select(ServiceRequest).where(
        ServiceRequest.deleted_at.is_(None),
        or_(ServiceRequest.customer_id == customer.id, ServiceRequest.requestor_customer_id == customer.id, ServiceRequest.parent_id.in_(auth_parent_ids)),
    ).order_by(ServiceRequest.created_at.desc())).all()
    return [customer_view(r) for r in rows]


@portal.get("/{request_id}")
def get_request(request_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    req = load_for_customer(db, customer, request_id)
    d = customer_view(req)
    d["timeline"] = [pick(e, "id", "event_type", "to_status", "message", "created_at") for e in req.events if e.visible_to_customer]
    return d


class CancelBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@portal.post("/{request_id}/cancel")
def cancel_request(request_id: uuid.UUID, body: CancelBody, request: Request, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    req = load_for_customer(db, customer, request_id)
    if req.status not in wf.PRE_ASSIGNMENT | {RequestStatus.ASSIGNED}:
        raise HTTPException(409, "This request can no longer be cancelled online. Please contact support.")
    req.cancel_reason = body.reason
    wf.transition(db, req, RequestStatus.CANCELLED, customer.user, body.reason, True, client_ip(request))
    db.commit()
    return customer_view(req)


class ConcernBody(BaseModel):
    message: str = Field(min_length=3, max_length=1500)


@portal.post("/{request_id}/concern", status_code=201)
def raise_concern(request_id: uuid.UUID, body: ConcernBody, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    from app.modules.incidents.router import create_incident_record
    from app.modules.incidents.models import IncidentCategory, Severity

    req = load_for_customer(db, customer, request_id)
    inc = create_incident_record(db, actor=customer.user, req=req, category=IncidentCategory.COMPLAINT, severity=Severity.MEDIUM, description=body.message)
    db.commit()
    return {"reference": inc.reference, "status": inc.status}


# ---------------- admin / operations ----------------
@admin.get("")
def admin_list(status: RequestStatus | None = None, q: str | None = None, limit: int = Query(100, le=500),
               user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    stmt = select(ServiceRequest).where(ServiceRequest.deleted_at.is_(None))
    if status:
        stmt = stmt.where(ServiceRequest.status == status)
    if q:
        stmt = stmt.where(ServiceRequest.reference.ilike(f"%{q}%"))
    rows = db.scalars(stmt.order_by(ServiceRequest.created_at.desc()).limit(limit)).all()
    return [ops_view(r) for r in rows]


@admin.post("/assisted", status_code=201)
def admin_create(customer_id: uuid.UUID, body: RequestCreate, request: Request, user=Depends(require_permission("request.manage")), db: Session = Depends(get_db)):
    """Create a request on behalf of a customer who called or messaged (assisted channel)."""
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    req = _create(db, customer, body, Source.ASSISTED, user, client_ip(request))
    db.commit()
    return ops_view(req)


@admin.get("/{request_id}")
def admin_get(request_id: uuid.UUID, user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    from app.modules.approvals.models import Approval
    from app.modules.assignments.models import Assignment

    req = load(db, request_id)
    d = ops_view(req)
    d["timeline"] = [pick(e, "id", "event_type", "from_status", "to_status", "message", "visible_to_customer", "actor_user_id", "created_at") for e in req.events]
    d["quotes"] = [pick(a, "id", "version", "status", "total_minor", "provider_cost_minor", "coordination_fee_minor", "tax_minor", "currency", "exceeds_budget_cap", "valid_until", "decided_at", "decision_note")
                   for a in db.scalars(select(Approval).where(Approval.request_id == req.id).order_by(Approval.version)).all()]
    d["assignments"] = [{**pick(a, "id", "provider_id", "role", "status", "offered_at", "accepted_at", "rejected_at", "reject_reason", "checked_in_at", "checked_out_at", "provider_payout_minor"), "provider_name": a.provider.full_name}
                        for a in db.scalars(select(Assignment).where(Assignment.request_id == req.id)).all()]
    d["allowed_transitions"] = sorted(t.value for t in wf.TRANSITIONS[req.status])
    audit(db, actor=user, action="request.view", entity_type="service_request", entity_id=req.id)
    db.commit()
    return d


DEDICATED = {RequestStatus.COMPLETED, RequestStatus.ASSIGNED, RequestStatus.IN_PROGRESS, RequestStatus.QUALITY_CHECK, RequestStatus.APPROVAL_PENDING}


class TransitionBody(BaseModel):
    to_status: RequestStatus
    note: str | None = Field(default=None, max_length=1000)
    notify_customer: bool = False


@admin.post("/{request_id}/transition")
def admin_transition(request_id: uuid.UUID, body: TransitionBody, request: Request, user=Depends(require_permission("request.manage")), db: Session = Depends(get_db)):
    req = load(db, request_id)
    if body.to_status in (RequestStatus.CANCELLED, RequestStatus.REJECTED):
        req.cancel_reason = body.note
    if body.to_status in DEDICATED:
        raise HTTPException(409, "Use the dedicated action for this step (quote, assign, provider check-in/out, quality review).")
    wf.transition(db, req, body.to_status, user, body.note, body.notify_customer, client_ip(request))
    db.commit()
    if body.notify_customer:
        from app.modules.families.models import Customer as C
        c = db.get(C, req.customer_id)
        notify(db, template_key="request_update", user=c.user, request_id=req.id, context={"reference": req.reference, "link": link(f"/portal/requests/{req.id}")})
    return ops_view(req)


class NoteBody(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    visible_to_customer: bool = False


@admin.post("/{request_id}/updates", status_code=201)
def post_update(request_id: uuid.UUID, body: NoteBody, user=Depends(require_permission("request.manage")), db: Session = Depends(get_db)):
    req = load(db, request_id)
    wf.add_event(db, req, user, "update" if body.visible_to_customer else "note", body.message, visible=body.visible_to_customer)
    db.commit()
    if body.visible_to_customer:
        c = db.get(Customer, req.customer_id)
        notify(db, template_key="request_update", user=c.user, request_id=req.id, prefer_whatsapp=c.whatsapp_opt_in, phone=c.phone,
               context={"reference": req.reference, "link": link(f"/portal/requests/{req.id}")})
    return {"ok": True}


class ExceptionBody(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


@admin.post("/{request_id}/approval-exception")
def grant_exception(request_id: uuid.UUID, body: ExceptionBody, request: Request, user=Depends(require_permission("approval_exception.grant")), db: Session = Depends(get_db)):
    """Admin-only, documented exception to the 'no paid work before customer approval' rule."""
    req = load(db, request_id)
    req.approval_exception_reason = body.reason
    req.approval_exception_by = user.id
    wf.add_event(db, req, user, "approval_exception", body.reason)
    audit(db, actor=user, action="request.approval_exception", entity_type="service_request", entity_id=req.id, after={"reason": body.reason}, ip=client_ip(request))
    db.commit()
    return ops_view(req)


class QualityBody(BaseModel):
    outcome: str = Field(pattern="^(pass|pass_with_notes|fail)$")
    notes: str | None = Field(default=None, max_length=2000)
    customer_message: str | None = Field(default=None, max_length=1500)


@admin.post("/{request_id}/quality-review")
def quality_review(request_id: uuid.UUID, body: QualityBody, request: Request, user=Depends(require_permission("request.manage")), db: Session = Depends(get_db)):
    from app.modules.billing.service import create_payout_for_request
    from app.modules.requests.models import QualityOutcome

    req = load(db, request_id)
    if req.status != RequestStatus.QUALITY_CHECK:
        raise HTTPException(409, "Request is not awaiting quality check")
    req.quality_outcome = QualityOutcome(body.outcome)
    req.quality_notes = body.notes
    req.quality_reviewed_by = user.id
    ip = client_ip(request)
    if body.outcome == "fail":
        wf.transition(db, req, RequestStatus.IN_PROGRESS, user, body.notes or "Quality check failed; rework required", False, ip)
        db.commit()
        return ops_view(req)
    wf.transition(db, req, RequestStatus.COMPLETED, user, "Quality check passed", False, ip)
    wf.add_event(db, req, user, "update", body.customer_message or "Your request has been completed.", visible=True)
    create_payout_for_request(db, req)
    db.commit()
    c = db.get(Customer, req.customer_id)
    notify(db, template_key="request_completed", user=c.user, request_id=req.id, prefer_whatsapp=c.whatsapp_opt_in, phone=c.phone,
           context={"reference": req.reference, "link": link(f"/portal/requests/{req.id}")})
    return ops_view(req)


class InternalNote(BaseModel):
    internal_notes: str | None = Field(default=None, max_length=4000)
    priority: Priority | None = None


@admin.patch("/{request_id}")
def admin_patch(request_id: uuid.UUID, body: InternalNote, user=Depends(require_permission("request.manage")), db: Session = Depends(get_db)):
    req = load(db, request_id)
    if body.internal_notes is not None:
        req.internal_notes = body.internal_notes
    if body.priority:
        req.priority = body.priority
    db.commit()
    return ops_view(req)
