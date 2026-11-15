import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, require_customer, require_permission
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.approvals.service import compute_quote, find_rule
from app.modules.assignments.models import AssignmentStatus
from app.modules.audit.service import audit
from app.modules.families.models import Customer
from app.modules.families.service import customer_authorisation
from app.modules.notifications.service import link, notify
from app.modules.requests import workflow as wf
from app.modules.requests.models import RequestStatus as S
from app.modules.requests.router import customer_can_access, load, load_for_customer

admin = APIRouter(tags=["admin: quotes"])
portal = APIRouter(prefix="/portal", tags=["customer: quotes"])

QUOTE_FIELDS = ("id", "version", "scope_summary", "line_items", "provider_cost_minor", "coordination_fee_minor", "tax_minor",
                "total_minor", "currency", "exceeds_budget_cap", "scheduled_window_start", "scheduled_window_end",
                "valid_until", "cancellation_terms", "status", "decided_at", "decision_note", "created_at")


class QuoteCreate(BaseModel):
    scope_summary: str = Field(min_length=5, max_length=2000)
    provider_cost_minor: int = Field(ge=0)
    line_items: list[dict] = []
    valid_days: int = Field(default=3, ge=1, le=30)
    cancellation_terms: str = "Cancellation terms apply as published on the Servixe website."
    scheduled_window_start: dt.datetime | None = None
    scheduled_window_end: dt.datetime | None = None


@admin.post("/admin/requests/{request_id}/quotes", status_code=201)
def create_quote(request_id: uuid.UUID, body: QuoteCreate, request: Request, user=Depends(require_permission("request.manage")), db: Session = Depends(get_db)):
    """Create a new quote version and send it for approval. Material changes supersede the old
    version and pause work until the customer approves again."""
    req = load(db, request_id)
    if req.status not in (S.UNDER_REVIEW, S.QUOTE_PENDING, S.APPROVAL_PENDING, S.ASSIGNED, S.IN_PROGRESS):
        raise HTTPException(409, f"Cannot quote a request in status {req.status.value}")
    rule = find_rule(db, req.service_id, req.service_area_id)
    if not rule:
        raise HTTPException(422, "No pricing rule configured for this service. Add one in the catalogue.")
    totals = compute_quote(rule, body.provider_cost_minor, req.priority.value == "urgent")
    ip = client_ip(request)
    if req.status == S.UNDER_REVIEW:
        wf.transition(db, req, S.QUOTE_PENDING, user, "Gathering quote", False, ip)
    prev = wf.latest_approval(db, req.id)
    for a in db.scalars(select(Approval).where(Approval.request_id == req.id, Approval.status == ApprovalStatus.PENDING)):
        a.status = ApprovalStatus.SUPERSEDED
    if prev and prev.status == ApprovalStatus.APPROVED:
        prev.status = ApprovalStatus.SUPERSEDED
    q = Approval(
        request_id=req.id, version=(prev.version + 1) if prev else 1, scope_summary=body.scope_summary,
        line_items=body.line_items, created_by_user_id=user.id, valid_until=utcnow() + dt.timedelta(days=body.valid_days),
        cancellation_terms=body.cancellation_terms, scheduled_window_start=body.scheduled_window_start or req.requested_start,
        scheduled_window_end=body.scheduled_window_end or req.requested_end,
        exceeds_budget_cap=bool(req.budget_cap_minor is not None and totals["total_minor"] > req.budget_cap_minor), **totals,
    )
    db.add(q)
    db.flush()
    if req.status != S.APPROVAL_PENDING:
        wf.transition(db, req, S.APPROVAL_PENDING, user, f"Quote v{q.version} sent for approval", True, ip)
    else:
        wf.add_event(db, req, user, "quote", f"Revised quote v{q.version} sent for approval", visible=True)
    audit(db, actor=user, action="quote.create", entity_type="approval", entity_id=q.id, after=pick(q, "version", "total_minor", "currency"), ip=ip)
    db.commit()
    c = db.get(Customer, req.customer_id)
    notify(db, template_key="quote_ready", user=c.user, request_id=req.id, prefer_whatsapp=c.whatsapp_opt_in, phone=c.phone,
           context={"reference": req.reference, "link": link(f"/portal/requests/{req.id}")})
    return pick(q, *QUOTE_FIELDS)


@portal.get("/requests/{request_id}/quotes")
def list_quotes(request_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    req = load_for_customer(db, customer, request_id)
    rows = db.scalars(select(Approval).where(Approval.request_id == req.id).order_by(Approval.version.desc())).all()
    return [pick(a, *QUOTE_FIELDS) for a in rows]


class Decision(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: str | None = Field(default=None, max_length=500)


@portal.post("/quotes/{quote_id}/decision")
def decide(quote_id: uuid.UUID, body: Decision, request: Request, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    q = db.get(Approval, quote_id)
    req = db.get(wf.ServiceRequest, q.request_id) if q else None
    if not q or not req or not customer_can_access(db, customer, req):
        raise HTTPException(404, "Quote not found")
    auth = customer_authorisation(db, customer.id, req.parent_id)
    if customer.id != req.customer_id and not (auth and auth.can_approve_costs and auth.status.value == "active"):
        raise HTTPException(403, "You are not authorised to approve costs for this parent")
    if q.status != ApprovalStatus.PENDING:
        raise HTTPException(409, f"This quote is {q.status.value} and can no longer be decided.")
    if q.valid_until and q.valid_until < utcnow():
        q.status = ApprovalStatus.EXPIRED
        db.commit()
        raise HTTPException(409, "This quote has expired. Please request a new quote.")
    ip = client_ip(request)
    q.approver_customer_id = customer.id
    q.decided_at = utcnow()
    q.decision_note = body.note
    if body.decision == "approve":
        q.status = ApprovalStatus.APPROVED
        wf.add_event(db, req, customer.user, "approval", f"Quote v{q.version} approved", visible=True)
        # If work was paused for renewed approval and a provider is already assigned, resume.
        if req.status == S.APPROVAL_PENDING and wf.primary_assignment(db, req.id):
            wf.transition(db, req, S.ASSIGNED, customer.user, "Renewed approval received; assignment resumed", True, ip)
    else:
        q.status = ApprovalStatus.REJECTED
        wf.add_event(db, req, customer.user, "approval", f"Quote v{q.version} declined", visible=True)
        if req.status == S.APPROVAL_PENDING:
            wf.transition(db, req, S.UNDER_REVIEW, customer.user, body.note or "Quote declined", True, ip)
    audit(db, actor=customer.user, action=f"quote.{body.decision}", entity_type="approval", entity_id=q.id,
          after={"total_minor": q.total_minor, "version": q.version, "approver": customer.id}, ip=ip)
    db.commit()
    return pick(q, *QUOTE_FIELDS)
