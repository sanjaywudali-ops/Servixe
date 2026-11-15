import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_permission, revoke_all_sessions
from app.core.permissions import STAFF_ROLES
from app.core.security import hash_password, hash_token, new_token, validate_password_strength
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.assignments.models import Assignment, AssignmentRole, AssignmentStatus
from app.modules.audit.models import AuditLog
from app.modules.audit.service import audit
from app.modules.billing.models import Invoice, InvoiceStatus, ProviderPayout, Refund, RefundStatus
from app.modules.families.models import Customer
from app.modules.identity.models import AuthToken, Role, User
from app.modules.incidents.models import Incident, IncidentStatus
from app.modules.notifications.service import link, notify
from app.modules.providers.models import Provider, ProviderDocument, ProviderStatus
from app.modules.requests.models import RequestStatus as S, ServiceRequest
from app.modules.requests.workflow import TERMINAL

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs")
def audit_logs(entity_type: str | None = None, entity_id: str | None = None, action: str | None = None, limit: int = Query(200, le=1000),
               user=Depends(require_permission("audit.view")), db: Session = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    if action:
        q = q.where(AuditLog.action.ilike(f"{action}%"))
    return [pick(a, "id", "created_at", "actor_user_id", "actor_role", "action", "entity_type", "entity_id", "before", "after", "ip") for a in db.scalars(q)]


# -------- staff management (admin only) --------
class StaffCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2)
    role: str = Field(pattern="^(support|admin)$")


@router.get("/staff")
def list_staff(user=Depends(require_permission("staff.manage")), db: Session = Depends(get_db)):
    rows = db.scalars(select(User)).all()
    return [{**pick(u, "id", "email", "full_name", "is_active", "mfa_enabled", "last_login_at"), "role": u.role_name} for u in rows if u.role_name in STAFF_ROLES]


@router.post("/staff", status_code=201)
def create_staff(body: StaffCreate, user=Depends(require_permission("staff.manage")), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "A user with this email already exists")
    role = db.scalar(select(Role).where(Role.name == body.role))
    u = User(email=body.email.lower(), full_name=body.full_name, role_id=role.id, password_hash=hash_password(new_token()))
    db.add(u)
    db.flush()
    token = new_token()
    db.add(AuthToken(user_id=u.id, purpose="invite", token_hash=hash_token(token), expires_at=utcnow() + dt.timedelta(days=3)))
    audit(db, actor=user, action="staff.create", entity_type="user", entity_id=u.id, after={"role": body.role})
    db.commit()
    notify(db, template_key="provider_invite", user=u, context={"link": link(f"/reset-password?token={token}")})
    return {"id": u.id, "email": u.email, "role": body.role}


class StaffPatch(BaseModel):
    is_active: bool


@router.patch("/staff/{user_id}")
def patch_staff(user_id: uuid.UUID, body: StaffPatch, user=Depends(require_permission("staff.manage")), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u or u.role_name not in STAFF_ROLES:
        raise HTTPException(404, "Not found")
    if u.id == user.id:
        raise HTTPException(409, "You cannot deactivate your own account")
    u.is_active = body.is_active
    if not body.is_active:
        revoke_all_sessions(db, u.id)
    audit(db, actor=user, action="staff.update", entity_type="user", entity_id=u.id, after={"is_active": body.is_active})
    db.commit()
    return {"ok": True}


# -------- dashboards & reports --------
@router.get("/overview")
def overview(user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    now = utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    reqs = db.scalars(select(ServiceRequest).where(ServiceRequest.deleted_at.is_(None))).all()
    open_reqs = [r for r in reqs if r.status not in TERMINAL and r.status != S.COMPLETED]
    overdue = [r for r in open_reqs if r.requested_end and r.requested_end < now and r.status not in (S.QUALITY_CHECK,)]
    today = db.scalars(select(Assignment).where(Assignment.status.in_([AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED]), Assignment.window_start >= day_start, Assignment.window_start < day_start + dt.timedelta(days=1))).all()
    return {
        "open_requests": len(open_reqs),
        "new_requests": sum(r.status == S.NEW_REQUEST for r in reqs),
        "awaiting_quote": sum(r.status == S.QUOTE_PENDING for r in reqs),
        "awaiting_customer_approval": sum(r.status == S.APPROVAL_PENDING for r in reqs),
        "overdue": [{"id": r.id, "reference": r.reference, "status": r.status} for r in overdue][:20],
        "jobs_today": len(today),
        "open_incidents": db.scalar(select(func.count()).select_from(Incident).where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]))),
        "verified_providers": db.scalar(select(func.count()).select_from(Provider).where(Provider.status == ProviderStatus.VERIFIED)),
        "providers_in_verification": db.scalar(select(func.count()).select_from(Provider).where(Provider.status.in_([ProviderStatus.APPLICANT, ProviderStatus.IN_VERIFICATION]))),
        "by_status": {s.value: sum(r.status == s for r in reqs) for s in S},
    }


@router.get("/reports")
def reports(days: int = Query(30, ge=1, le=365), user=Depends(require_permission("reports.view")), db: Session = Depends(get_db)):
    since = utcnow() - dt.timedelta(days=days)
    reqs = db.scalars(select(ServiceRequest).where(ServiceRequest.created_at >= since)).all()
    done = [r for r in reqs if r.completed_at]
    avg_hours = (sum((r.completed_at - r.created_at).total_seconds() for r in done) / len(done) / 3600) if done else None

    invoices = db.scalars(select(Invoice).where(Invoice.created_at >= since, Invoice.status.in_([InvoiceStatus.PAID, InvoiceStatus.ISSUED, InvoiceStatus.REFUNDED]))).all()
    paid = [i for i in invoices if i.status == InvoiceStatus.PAID]
    revenue_minor = sum(i.total_minor for i in paid)
    coordination = sum(i.coordination_fee_minor for i in paid)
    third_party = sum(i.provider_cost_minor for i in paid)
    tax = sum(i.tax_minor for i in paid)
    refunds = db.scalar(select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(Refund.status == RefundStatus.PROCESSED, Refund.created_at >= since))
    payouts = db.scalars(select(ProviderPayout).where(ProviderPayout.created_at >= since)).all()
    payout_total = sum(p.amount_minor for p in payouts)
    # Contribution margin (single-currency view): coordination fee kept, less refunds. Provider charges are pass-through
    # costs, so they are shown separately and not counted as margin. Review with your accountant.
    margin = coordination - refunds

    assigns = db.scalars(select(Assignment).where(Assignment.created_at >= since, Assignment.role == AssignmentRole.PRIMARY)).all()
    total_a = len(assigns) or 1
    rej = sum(a.status == AssignmentStatus.REJECTED for a in assigns)
    acc = sum(a.status in (AssignmentStatus.ACCEPTED, AssignmentStatus.COMPLETED) for a in assigns)
    no_show = sum(r.status == S.NO_SHOW for r in reqs)

    cust_counts: dict = {}
    for r in db.scalars(select(ServiceRequest).where(ServiceRequest.status.in_([S.COMPLETED, S.CLOSED]))):
        cust_counts[r.customer_id] = cust_counts.get(r.customer_id, 0) + 1
    repeat = sum(1 for n in cust_counts.values() if n > 1)

    soon = utcnow() + dt.timedelta(days=30)
    expiring = db.scalars(select(ProviderDocument).where(ProviderDocument.expires_at.is_not(None), ProviderDocument.expires_at <= soon)).all()

    return {
        "period_days": days,
        "requests": {"created": len(reqs), "completed": len(done), "cancelled": sum(r.status == S.CANCELLED for r in reqs),
                     "avg_completion_hours": round(avg_hours, 1) if avg_hours is not None else None},
        "providers": {"acceptance_rate": round(acc / total_a, 3), "rejection_rate": round(rej / total_a, 3), "no_shows": no_show},
        "incidents": {s.value: db.scalar(select(func.count()).select_from(Incident).where(Incident.severity == s, Incident.created_at >= since)) for s in __import__("app.modules.incidents.models", fromlist=["Severity"]).Severity},
        "finance_minor": {"revenue_collected": revenue_minor, "coordination_fees": coordination, "third_party_costs": third_party, "tax": tax,
                          "refunds": refunds, "provider_payouts": payout_total, "contribution_margin": margin},
        "repeat_customers": repeat,
        "provider_document_gaps": [{"provider_id": d.provider_id, "doc_type": d.doc_type, "expires_at": d.expires_at} for d in expiring],
    }
