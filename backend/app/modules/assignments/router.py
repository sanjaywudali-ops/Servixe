import datetime as dt
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, require_permission, require_provider
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.assignments.models import Assignment, AssignmentRole, AssignmentStatus
from app.modules.audit.service import audit
from app.modules.evidence.models import AccessScope, ChecklistResponse, ChecklistTemplate, Evidence, EvidencePurpose
from app.modules.evidence.service import evidence_summary, read_and_validate, store_evidence
from app.modules.notifications.service import link, notify
from app.modules.providers.models import Provider, ProviderStatus
from app.modules.requests import workflow as wf
from app.modules.requests.models import RequestStatus as S, ServiceRequest
from app.modules.requests.router import load

admin = APIRouter(tags=["admin: assignments"])
provider_api = APIRouter(prefix="/provider", tags=["provider portal"])


class AssignBody(BaseModel):
    provider_id: uuid.UUID
    role: AssignmentRole = AssignmentRole.PRIMARY
    instructions: str | None = Field(default=None, max_length=2000)
    window_start: dt.datetime | None = None
    window_end: dt.datetime | None = None
    provider_payout_minor: int = Field(default=0, ge=0)


@admin.post("/admin/requests/{request_id}/assignments", status_code=201)
def assign(request_id: uuid.UUID, body: AssignBody, request: Request, user=Depends(require_permission("assignment.manage")), db: Session = Depends(get_db)):
    req = load(db, request_id)
    ip = client_ip(request)
    if req.status not in (S.UNDER_REVIEW, S.APPROVAL_PENDING, S.ASSIGNED):
        raise HTTPException(409, f"Cannot assign a provider while request is {req.status.value}")
    if not wf.approval_satisfied(db, req):
        raise HTTPException(409, "The customer has not approved the current quote. Paid work cannot be assigned yet.")
    wf.check_consent_and_authorisation(db, req)
    prov = db.get(Provider, body.provider_id)
    if not prov or prov.deleted_at:
        raise HTTPException(404, "Provider not found")
    if prov.status != ProviderStatus.VERIFIED:
        raise HTTPException(409, "Only verified providers can be assigned")
    if prov.services and req.service_id not in {s.id for s in prov.services}:
        raise HTTPException(409, "Provider does not cover this service")
    if req.service_area_id and prov.areas and req.service_area_id not in {a.id for a in prov.areas}:
        raise HTTPException(409, "Provider does not cover this service area")
    if body.role == AssignmentRole.BACKUP and not prov.can_be_backup:
        raise HTTPException(409, "Provider is not available as a backup")
    live = (AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED)
    others = db.scalars(select(Assignment).where(Assignment.request_id == req.id, Assignment.status.in_(live))).all()
    if any(a.provider_id == prov.id for a in others):
        raise HTTPException(409, "Provider is already assigned to this request")
    for a in others:
        if a.role == body.role:
            a.status = AssignmentStatus.WITHDRAWN
    a = Assignment(request_id=req.id, provider_id=prov.id, role=body.role, status=AssignmentStatus.OFFERED, instructions=body.instructions,
                   window_start=body.window_start or req.requested_start, window_end=body.window_end or req.requested_end,
                   provider_payout_minor=body.provider_payout_minor, offered_at=utcnow(), assigned_by_user_id=user.id)
    db.add(a)
    db.flush()
    wf.add_event(db, req, user, "assignment", f"{body.role.value.title()} provider offered the job", visible=False)
    if body.role == AssignmentRole.PRIMARY and req.status != S.ASSIGNED:
        wf.transition(db, req, S.ASSIGNED, user, "Provider assigned", True, ip)
    audit(db, actor=user, action="assignment.create", entity_type="assignment", entity_id=a.id, after={"provider_id": prov.id, "role": body.role}, ip=ip)
    db.commit()
    if prov.email:
        notify(db, template_key="job_offered", email=prov.email, request_id=req.id, context={"reference": req.reference, "link": link(f"/provider/jobs/{a.id}")})
    return pick(a, "id", "provider_id", "role", "status")


@admin.delete("/admin/assignments/{assignment_id}")
def withdraw(assignment_id: uuid.UUID, user=Depends(require_permission("assignment.manage")), db: Session = Depends(get_db)):
    a = db.get(Assignment, assignment_id)
    if not a or a.status not in (AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED) or a.checked_in_at:
        raise HTTPException(409, "Assignment cannot be withdrawn")
    a.status = AssignmentStatus.WITHDRAWN
    audit(db, actor=user, action="assignment.withdraw", entity_type="assignment", entity_id=a.id)
    db.commit()
    return {"ok": True}


# --------------- provider portal: minimum necessary data only ----------------
def job_view(a: Assignment, db: Session) -> dict:
    req = a.request
    accepted = a.status in (AssignmentStatus.ACCEPTED, AssignmentStatus.COMPLETED)
    d = {
        "id": a.id, "reference": req.reference, "role": a.role, "status": a.status, "service": req.service.name,
        "window_start": a.window_start, "window_end": a.window_end, "request_status": req.status,
        "area": req.parent.area or req.parent.city, "instructions": a.instructions if accepted else None,
        "task_details": req.task_details if accepted else None, "payout_minor": a.provider_payout_minor, "currency": req.currency,
        "checked_in_at": a.checked_in_at, "checked_out_at": a.checked_out_at,
        # Address / contact only after the provider accepts, and only for the parent's first name.
        "parent_first_name": req.parent.full_name.split(" ")[0] if accepted else None,
        "location": req.location_text if accepted else None,
        "contact_phone": req.parent.phone if accepted and req.status not in wf.TERMINAL else None,
    }
    return d


def own_assignment(db: Session, provider: Provider, assignment_id) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if not a or a.provider_id != provider.id:
        raise HTTPException(404, "Job not found")
    return a


@provider_api.get("/me")
def me(provider: Provider = Depends(require_provider)):
    return pick(provider, "id", "full_name", "phone", "email", "status")


@provider_api.get("/jobs")
def jobs(provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    rows = db.scalars(select(Assignment).where(Assignment.provider_id == provider.id, Assignment.status != AssignmentStatus.WITHDRAWN)
                      .order_by(Assignment.window_start.asc().nulls_last())).all()
    return [job_view(a, db) for a in rows]


@provider_api.get("/jobs/{assignment_id}")
def job(assignment_id: uuid.UUID, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    d = job_view(a, db)
    tpl = db.scalar(select(ChecklistTemplate).where(ChecklistTemplate.service_id == a.request.service_id, ChecklistTemplate.is_active.is_(True)))
    resp = db.scalar(select(ChecklistResponse).where(ChecklistResponse.assignment_id == a.id))
    d["checklist"] = {"items": (resp.template_snapshot if resp else (tpl.items if tpl else [])), "responses": resp.responses if resp else {}, "completed_at": resp.completed_at if resp else None}
    d["evidence"] = [evidence_summary(e) for e in db.scalars(select(Evidence).where(Evidence.assignment_id == a.id, Evidence.deleted_at.is_(None))).all()]
    return d


class RejectBody(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@provider_api.post("/jobs/{assignment_id}/accept")
def accept(assignment_id: uuid.UUID, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    if a.status != AssignmentStatus.OFFERED:
        raise HTTPException(409, "This job is not awaiting a response")
    a.status, a.accepted_at = AssignmentStatus.ACCEPTED, utcnow()
    wf.add_event(db, a.request, provider.user, "assignment", "Provider accepted the job")
    audit(db, actor=provider.user, action="assignment.accept", entity_type="assignment", entity_id=a.id)
    db.commit()
    return job_view(a, db)


@provider_api.post("/jobs/{assignment_id}/reject")
def reject(assignment_id: uuid.UUID, body: RejectBody, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    if a.status != AssignmentStatus.OFFERED:
        raise HTTPException(409, "This job is not awaiting a response")
    a.status, a.rejected_at, a.reject_reason = AssignmentStatus.REJECTED, utcnow(), body.reason
    req = a.request
    wf.add_event(db, req, provider.user, "assignment", f"Provider declined: {body.reason}")
    if a.role == AssignmentRole.PRIMARY:
        backup = db.scalar(select(Assignment).where(Assignment.request_id == req.id, Assignment.role == AssignmentRole.BACKUP,
                                                    Assignment.status.in_([AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED])))
        if backup:
            backup.role = AssignmentRole.PRIMARY
            wf.add_event(db, req, provider.user, "assignment", "Backup provider promoted to primary")
        elif req.status == S.ASSIGNED:
            wf.transition(db, req, S.UNDER_REVIEW, provider.user, "Primary provider declined; reassignment needed", False)
    audit(db, actor=provider.user, action="assignment.reject", entity_type="assignment", entity_id=a.id, after={"reason": body.reason})
    db.commit()
    return {"ok": True}


class CheckBody(BaseModel):
    note: str | None = Field(default=None, max_length=500)


@provider_api.post("/jobs/{assignment_id}/check-in")
def check_in(assignment_id: uuid.UUID, body: CheckBody, request: Request, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    if a.role != AssignmentRole.PRIMARY or a.status != AssignmentStatus.ACCEPTED or a.checked_in_at:
        raise HTTPException(409, "Cannot check in to this job")
    req = a.request
    wf.transition(db, req, S.IN_PROGRESS, provider.user, "Provider checked in", True, client_ip(request))
    a.checked_in_at, a.check_in_note = utcnow(), body.note
    tpl = db.scalar(select(ChecklistTemplate).where(ChecklistTemplate.service_id == req.service_id, ChecklistTemplate.is_active.is_(True)))
    if tpl and not db.scalar(select(ChecklistResponse).where(ChecklistResponse.assignment_id == a.id)):
        db.add(ChecklistResponse(request_id=req.id, assignment_id=a.id, template_id=tpl.id, template_snapshot=tpl.items, responses={}))
    db.commit()
    return job_view(a, db)


class ChecklistBody(BaseModel):
    responses: dict[str, dict]  # {key: {done: bool, note?: str}}


@provider_api.put("/jobs/{assignment_id}/checklist")
def save_checklist(assignment_id: uuid.UUID, body: ChecklistBody, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    resp = db.scalar(select(ChecklistResponse).where(ChecklistResponse.assignment_id == a.id))
    if not resp or a.request.status != S.IN_PROGRESS:
        raise HTTPException(409, "Checklist is available while the job is in progress")
    keys = {i["key"] for i in resp.template_snapshot}
    clean = {k: {"done": bool(v.get("done")), "note": str(v.get("note", ""))[:300]} for k, v in body.responses.items() if k in keys}
    resp.responses = clean
    required = [i["key"] for i in resp.template_snapshot if i.get("required", True)]
    done = all(clean.get(k, {}).get("done") for k in required)
    resp.completed_at = utcnow() if done else None
    resp.completed_by_user_id = provider.user_id if done else None
    db.commit()
    return {"complete": done, "responses": clean}


@provider_api.post("/jobs/{assignment_id}/check-out")
def check_out(assignment_id: uuid.UUID, body: CheckBody, request: Request, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    if not a.checked_in_at or a.checked_out_at:
        raise HTTPException(409, "Cannot check out of this job")
    req = a.request
    wf.transition(db, req, S.QUALITY_CHECK, provider.user, "Provider checked out; awaiting quality review", False, client_ip(request))
    a.checked_out_at, a.check_out_note = utcnow(), body.note
    db.commit()
    return job_view(a, db)


@provider_api.post("/jobs/{assignment_id}/evidence", status_code=201)
async def upload_evidence(assignment_id: uuid.UUID, file: UploadFile = File(...), purpose: EvidencePurpose = Form(EvidencePurpose.COMPLETION_PHOTO),
                          caption: str | None = Form(None), provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = own_assignment(db, provider, assignment_id)
    if a.status != AssignmentStatus.ACCEPTED or a.request.status not in (S.IN_PROGRESS, S.QUALITY_CHECK):
        raise HTTPException(409, "Evidence can be uploaded only for an active job")
    data, ctype = await read_and_validate(file)
    ev = store_evidence(db, req=a.request, assignment=a, uploader=provider.user, data=data, ctype=ctype, filename=file.filename,
                        purpose=purpose, scope=AccessScope.OPS_ONLY, caption=(caption or None) and caption[:300])
    audit(db, actor=provider.user, action="evidence.upload", entity_type="evidence", entity_id=ev.id)
    db.commit()
    return evidence_summary(ev)


@provider_api.get("/history")
def history(provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    from app.modules.billing.models import ProviderPayout

    rows = db.scalars(select(Assignment).where(Assignment.provider_id == provider.id, Assignment.status.in_([AssignmentStatus.COMPLETED, AssignmentStatus.ACCEPTED, AssignmentStatus.REJECTED])).order_by(Assignment.created_at.desc())).all()
    payouts = {p.assignment_id: p for p in db.scalars(select(ProviderPayout).where(ProviderPayout.provider_id == provider.id)).all()}
    out = []
    for a in rows:
        p = payouts.get(a.id)
        out.append({"id": a.id, "reference": a.request.reference, "service": a.request.service.name, "status": a.status,
                    "request_status": a.request.status, "completed_at": a.request.completed_at,
                    "payout_status": p.status if p else None, "payout_minor": p.amount_minor if p else a.provider_payout_minor})
    return out
