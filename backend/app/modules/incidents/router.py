import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_permission, require_provider
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.assignments.models import Assignment
from app.modules.audit.service import audit
from app.modules.families.service import next_reference
from app.modules.incidents.models import Incident, IncidentCategory, IncidentNote, IncidentStatus, Severity
from app.modules.notifications.service import link, notify
from app.modules.providers.models import Provider
from app.modules.requests import workflow as wf
from app.modules.requests.models import ServiceRequest
from app.modules.identity.models import User

admin = APIRouter(prefix="/admin/incidents", tags=["admin: incidents"])
provider_api = APIRouter(prefix="/provider", tags=["provider portal"])

FIELDS = ("id", "reference", "request_id", "category", "severity", "status", "description", "event_time", "reported_by_user_id",
          "reporter_role", "owner_user_id", "escalation_contacts", "actions_taken", "customer_communication", "closure_review",
          "resolved_at", "closed_at", "created_at")


def create_incident_record(db: Session, *, actor, req: ServiceRequest | None, category, severity, description: str, event_time=None) -> Incident:
    inc = Incident(
        reference=next_reference(db, "incident", "INC"), request_id=req.id if req else None, parent_id=req.parent_id if req else None,
        category=category, severity=severity, description=description, event_time=event_time or utcnow(),
        reported_by_user_id=actor.id, reporter_role=actor.role_name,
    )
    db.add(inc)
    db.flush()
    if req and severity in (Severity.HIGH, Severity.CRITICAL):
        wf.open_incident_state(db, req, actor)
    audit(db, actor=actor, action="incident.create", entity_type="incident", entity_id=inc.id, after={"severity": severity, "category": category})
    # alert operations
    for u in db.scalars(select(User).where(User.is_active.is_(True))).all():
        if u.role_name == "admin" and severity in (Severity.HIGH, Severity.CRITICAL):
            notify(db, template_key="incident_alert", user=u, context={"reference": inc.reference, "severity": severity.value, "link": link(f"/admin/incidents/{inc.id}")})
    return inc


class ProviderIncident(BaseModel):
    category: IncidentCategory = IncidentCategory.SAFETY
    severity: Severity = Severity.MEDIUM
    description: str = Field(min_length=5, max_length=3000)


@provider_api.post("/jobs/{assignment_id}/incident", status_code=201)
def report(assignment_id: uuid.UUID, body: ProviderIncident, provider: Provider = Depends(require_provider), db: Session = Depends(get_db)):
    a = db.get(Assignment, assignment_id)
    if not a or a.provider_id != provider.id:
        raise HTTPException(404, "Job not found")
    inc = create_incident_record(db, actor=provider.user, req=a.request, category=body.category, severity=body.severity, description=body.description)
    db.commit()
    return {"reference": inc.reference, "notice": settings.emergency_notice}


@provider_api.get("/emergency-notice")
def notice():
    return {"notice": settings.emergency_notice}


@admin.get("")
def list_incidents(status: IncidentStatus | None = None, user=Depends(require_permission("incident.manage")), db: Session = Depends(get_db)):
    q = select(Incident).order_by(Incident.created_at.desc()).limit(300)
    if status:
        q = q.where(Incident.status == status)
    return [pick(i, *FIELDS) for i in db.scalars(q).all()]


@admin.get("/{incident_id}")
def get_incident(incident_id: uuid.UUID, user=Depends(require_permission("incident.manage")), db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "Not found")
    d = pick(inc, *FIELDS)
    d["notes"] = [pick(n, "id", "note", "author_user_id", "created_at") for n in db.scalars(select(IncidentNote).where(IncidentNote.incident_id == inc.id).order_by(IncidentNote.created_at))]
    return d


class IncidentCreate(BaseModel):
    request_id: uuid.UUID | None = None
    category: IncidentCategory = IncidentCategory.OTHER
    severity: Severity = Severity.MEDIUM
    description: str = Field(min_length=5, max_length=3000)


@admin.post("", status_code=201)
def create(body: IncidentCreate, user=Depends(require_permission("incident.manage")), db: Session = Depends(get_db)):
    req = db.get(ServiceRequest, body.request_id) if body.request_id else None
    inc = create_incident_record(db, actor=user, req=req, category=body.category, severity=body.severity, description=body.description)
    db.commit()
    return pick(inc, *FIELDS)


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    severity: Severity | None = None
    owner_user_id: uuid.UUID | None = None
    escalation_contacts: list[str] | None = None
    actions_taken: str | None = None
    customer_communication: str | None = None
    closure_review: str | None = None
    note: str | None = Field(default=None, max_length=2000)


@admin.patch("/{incident_id}")
def update(incident_id: uuid.UUID, body: IncidentUpdate, user=Depends(require_permission("incident.manage")), db: Session = Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "Not found")
    before = pick(inc, "status", "severity", "owner_user_id")
    data = body.model_dump(exclude_unset=True, exclude={"note"})
    if data.get("status") == IncidentStatus.CLOSED and not (data.get("closure_review") or inc.closure_review):
        raise HTTPException(422, "A closure review is required to close an incident")
    for k, v in data.items():
        setattr(inc, k, v)
    now = utcnow()
    if inc.status == IncidentStatus.RESOLVED and not inc.resolved_at:
        inc.resolved_at = now
    if inc.status == IncidentStatus.CLOSED:
        inc.closed_at = inc.closed_at or now
    if body.note:
        db.add(IncidentNote(incident_id=inc.id, author_user_id=user.id, note=body.note))
    if inc.request_id and inc.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
        db.flush()
        req = db.get(ServiceRequest, inc.request_id)
        wf.restore_after_incident(db, req, user)
    audit(db, actor=user, action="incident.update", entity_type="incident", entity_id=inc.id, before=before, after=data)
    db.commit()
    return pick(inc, *FIELDS)
