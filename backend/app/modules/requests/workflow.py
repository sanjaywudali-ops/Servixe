"""Explicit request workflow. Allowed transitions and consent/approval gates are enforced here
(server-side) so staff cannot skip them by editing a status field."""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.assignments.models import Assignment, AssignmentRole, AssignmentStatus
from app.modules.audit.service import audit
from app.modules.evidence.models import ChecklistResponse, ChecklistTemplate
from app.modules.families.service import active_authorisation, active_consent
from app.modules.incidents.models import Incident, IncidentStatus, Severity
from app.modules.requests.models import QualityOutcome, RequestEvent, RequestStatus as S, ServiceRequest

TERMINAL = {S.CLOSED, S.CANCELLED, S.REJECTED}
PRE_ASSIGNMENT = {S.NEW_REQUEST, S.UNDER_REVIEW, S.QUOTE_PENDING, S.APPROVAL_PENDING}

TRANSITIONS: dict[S, set[S]] = {
    S.NEW_REQUEST: {S.UNDER_REVIEW, S.CANCELLED, S.REJECTED},
    S.UNDER_REVIEW: {S.QUOTE_PENDING, S.ASSIGNED, S.CANCELLED, S.REJECTED, S.RESCHEDULED},
    S.QUOTE_PENDING: {S.APPROVAL_PENDING, S.UNDER_REVIEW, S.CANCELLED, S.REJECTED},
    S.APPROVAL_PENDING: {S.ASSIGNED, S.UNDER_REVIEW, S.CANCELLED, S.RESCHEDULED},
    S.ASSIGNED: {S.IN_PROGRESS, S.APPROVAL_PENDING, S.UNDER_REVIEW, S.CANCELLED, S.RESCHEDULED, S.NO_SHOW},
    S.IN_PROGRESS: {S.QUALITY_CHECK, S.APPROVAL_PENDING, S.FAILED, S.NO_SHOW, S.CANCELLED},
    S.QUALITY_CHECK: {S.COMPLETED, S.IN_PROGRESS, S.FAILED},
    S.COMPLETED: {S.CLOSED, S.REFUND_PENDING},
    S.RESCHEDULED: {S.UNDER_REVIEW, S.CANCELLED},
    S.NO_SHOW: {S.UNDER_REVIEW, S.REFUND_PENDING, S.CANCELLED},
    S.FAILED: {S.UNDER_REVIEW, S.REFUND_PENDING},
    S.REFUND_PENDING: {S.CLOSED},
    S.CLOSED: set(), S.CANCELLED: set(), S.REJECTED: set(), S.INCIDENT_OPEN: set(),
}


def latest_approval(db: Session, request_id) -> Approval | None:
    return db.scalar(select(Approval).where(Approval.request_id == request_id).order_by(Approval.version.desc()).limit(1))


def approval_satisfied(db: Session, req: ServiceRequest) -> bool:
    """Paid third-party work needs the latest quote approved (or a documented, admin-granted exception)."""
    if req.approval_exception_reason:
        return True
    a = latest_approval(db, req.id)
    return bool(a and a.status == ApprovalStatus.APPROVED)


def primary_assignment(db: Session, request_id, statuses=(AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED)) -> Assignment | None:
    return db.scalar(
        select(Assignment).where(
            Assignment.request_id == request_id, Assignment.role == AssignmentRole.PRIMARY, Assignment.status.in_(statuses)
        )
    )


def _fail(msg: str, code: int = 409):
    raise HTTPException(code, msg)


def check_consent_and_authorisation(db: Session, req: ServiceRequest) -> None:
    scope = req.consent_scope or req.service.required_consent_scope
    consent = active_consent(db, req.parent_id, scope)
    if not consent:
        _fail(f"No active parent consent covering '{scope}'. Record the parent's informed agreement first.")
    if not active_authorisation(db, req.requestor_customer_id, req.parent_id):
        _fail("The requestor does not have an active authorisation for this parent.")
    req.consent_id = consent.id


def _gate(db: Session, req: ServiceRequest, frm: S, to: S) -> None:
    if to == S.QUOTE_PENDING:
        check_consent_and_authorisation(db, req)
    elif to == S.APPROVAL_PENDING and frm == S.QUOTE_PENDING:
        a = latest_approval(db, req.id)
        if not a or a.status != ApprovalStatus.PENDING:
            _fail("Create a quote before sending for approval.")
    elif to == S.ASSIGNED:
        if not approval_satisfied(db, req):
            _fail("The customer has not approved the current quote. Paid work cannot be assigned yet.")
        if not primary_assignment(db, req.id):
            _fail("Assign a verified primary provider first.")
    elif to == S.IN_PROGRESS and frm == S.ASSIGNED:
        if not approval_satisfied(db, req):
            _fail("Cost/scope approval is required before work starts. If the quote changed, obtain renewed approval.")
        a = primary_assignment(db, req.id, (AssignmentStatus.ACCEPTED,))
        if not a:
            _fail("The primary provider has not accepted the job.")
        check_consent_and_authorisation(db, req)
    elif to == S.QUALITY_CHECK:
        resp = db.scalar(select(ChecklistResponse).where(ChecklistResponse.request_id == req.id).order_by(ChecklistResponse.created_at.desc()))
        has_template = db.scalar(select(func.count()).select_from(ChecklistTemplate).where(ChecklistTemplate.service_id == req.service_id, ChecklistTemplate.is_active.is_(True)))
        if has_template and (not resp or not resp.completed_at):
            _fail("The required checklist items are not complete.")
    elif to == S.COMPLETED:
        if req.quality_outcome is None or req.quality_outcome == QualityOutcome.FAIL:
            _fail("A passing quality review is required before completion.")
    elif to == S.CLOSED:
        from app.modules.billing.models import Invoice, InvoiceStatus

        open_inc = db.scalar(select(func.count()).select_from(Incident).where(Incident.request_id == req.id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING])))
        if open_inc:
            _fail("Resolve open incidents before closing the request.")
        if frm != S.REFUND_PENDING:
            inv = db.scalars(select(Invoice).where(Invoice.request_id == req.id)).all()
            live = [i for i in inv if i.status.value != "void"]
            if not live or any(i.status.value == "issued" and not i.waived_reason for i in live) or any(i.status.value == "draft" for i in live):
                _fail("Invoice/payment close-out is incomplete (issue and collect or waive the invoice).")
    elif to in (S.CANCELLED, S.REJECTED):
        if not (req.cancel_reason or "").strip():
            _fail("A reason is required.", 422)


def add_event(db, req, actor, event_type, message=None, frm=None, to=None, visible=False) -> RequestEvent:
    ev = RequestEvent(
        request_id=req.id, actor_user_id=getattr(actor, "id", None), event_type=event_type,
        from_status=frm.value if frm else None, to_status=to.value if to else None, message=message,
        visible_to_customer=visible, created_at=utcnow(),
    )
    db.add(ev)
    return ev


def transition(db: Session, req: ServiceRequest, to: S, actor, note: str | None = None, visible: bool = False, ip: str | None = None) -> ServiceRequest:
    frm = req.status
    if to not in TRANSITIONS.get(frm, set()):
        _fail(f"Transition {frm.value} -> {to.value} is not allowed.")
    _gate(db, req, frm, to)
    req.status = to
    now = utcnow()
    if to == S.COMPLETED:
        req.completed_at = now
    if to == S.CLOSED:
        req.closed_at = now
    add_event(db, req, actor, "status_change", note, frm, to, visible)
    audit(db, actor=actor, action="request.transition", entity_type="service_request", entity_id=req.id,
          before={"status": frm}, after={"status": to, "note": note}, ip=ip)
    return req


def open_incident_state(db: Session, req: ServiceRequest, actor) -> None:
    if req.status in TERMINAL or req.status == S.INCIDENT_OPEN:
        return
    req.status_before_incident = req.status.value
    frm, req.status = req.status, S.INCIDENT_OPEN
    add_event(db, req, actor, "status_change", "Incident opened", frm, S.INCIDENT_OPEN, False)


def restore_after_incident(db: Session, req: ServiceRequest, actor) -> None:
    if req.status != S.INCIDENT_OPEN:
        return
    still_open = db.scalar(select(func.count()).select_from(Incident).where(
        Incident.request_id == req.id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
        Incident.severity.in_([Severity.HIGH, Severity.CRITICAL])))
    if still_open:
        return
    prev = S(req.status_before_incident or S.UNDER_REVIEW.value)
    req.status = prev
    add_event(db, req, actor, "status_change", "Incident resolved", S.INCIDENT_OPEN, prev, False)
