import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import client_ip, require_customer, require_permission
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.audit.service import audit
from app.modules.families.models import (AuthStatus, CaptureMethod, Consent, ConsentScope, Customer, FamilyAuthorisation, Parent)
from app.modules.families.service import customer_authorisation, get_parent_for_customer

portal = APIRouter(prefix="/portal", tags=["customer: family"])
admin = APIRouter(prefix="/admin", tags=["admin: families"])

PARENT_FIELDS = ("id", "full_name", "phone", "preferred_language", "contact_preferences", "address_line", "city", "area",
                 "service_area_id", "location_notes", "emergency_contact_name", "emergency_contact_phone")
AUTH_FIELDS = ("id", "parent_id", "customer_id", "relationship_to_parent", "can_request_services", "can_receive_updates",
               "can_approve_costs", "can_view_evidence", "status", "valid_from", "valid_until", "consent_id")
CONSENT_FIELDS = ("id", "parent_id", "scopes", "given_by", "captured_via", "captured_at", "valid_from", "valid_until", "evidence_ref", "revoked_at")


class ProfileBody(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    country: str | None = Field(default=None, max_length=80)
    whatsapp_opt_in: bool | None = None
    preferred_currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")


@portal.get("/profile")
def profile(customer: Customer = Depends(require_customer)):
    return pick(customer, "id", "full_name", "country", "phone", "whatsapp_opt_in", "preferred_currency")


@portal.patch("/profile")
def update_profile(body: ProfileBody, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_unset=True)
    if data.get("whatsapp_opt_in") and not customer.whatsapp_opt_in:
        customer.whatsapp_opt_in_at = utcnow()
    for k, v in data.items():
        setattr(customer, k, v)
    db.commit()
    return profile(customer)


class ParentBody(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    preferred_language: str | None = Field(default=None, max_length=40)
    contact_preferences: str | None = Field(default=None, max_length=255)
    address_line: str | None = Field(default=None, max_length=255)
    city: str = Field(default="Nellore", max_length=80)
    area: str | None = Field(default=None, max_length=120)
    service_area_id: uuid.UUID | None = None
    location_notes: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=160)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    relationship_to_parent: str = Field(default="son/daughter", max_length=60)


def parent_view(db: Session, customer: Customer, p: Parent) -> dict:
    d = pick(p, *PARENT_FIELDS)
    a = customer_authorisation(db, customer.id, p.id)
    d["authorisation"] = pick(a, *AUTH_FIELDS) if a else None
    cons = db.scalars(select(Consent).where(Consent.parent_id == p.id).order_by(Consent.captured_at.desc())).all()
    now = utcnow()
    d["consent_status"] = "active" if any(c.covers(s.value, now) for c in cons for s in ConsentScope) else "none"
    d["consents"] = [pick(c, *CONSENT_FIELDS) for c in cons]
    return d


@portal.get("/parents")
def list_parents(customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    ids = [a.parent_id for a in db.scalars(select(FamilyAuthorisation).where(FamilyAuthorisation.customer_id == customer.id, FamilyAuthorisation.status != AuthStatus.REVOKED))]
    ps = db.scalars(select(Parent).where(Parent.id.in_(ids), Parent.deleted_at.is_(None))).all() if ids else []
    return [parent_view(db, customer, p) for p in ps]


@portal.post("/parents", status_code=201)
def add_parent(body: ParentBody, request: Request, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    """Adds the parent record and a PENDING authorisation. The overseas payer does NOT automatically gain
    authority: operations records the parent's informed agreement and then activates the authorisation."""
    data = body.model_dump(exclude={"relationship_to_parent"})
    p = Parent(created_by_customer_id=customer.id, **data)
    db.add(p)
    db.flush()
    db.add(FamilyAuthorisation(parent_id=p.id, customer_id=customer.id, relationship_to_parent=body.relationship_to_parent, status=AuthStatus.PENDING))
    audit(db, actor=customer.user, action="parent.create", entity_type="parent", entity_id=p.id, ip=client_ip(request))
    db.commit()
    db.refresh(p)
    return parent_view(db, customer, p)


@portal.get("/parents/{parent_id}")
def get_parent(parent_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    return parent_view(db, customer, get_parent_for_customer(db, customer, parent_id))


@portal.patch("/parents/{parent_id}")
def update_parent(parent_id: uuid.UUID, body: ParentBody, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    p = get_parent_for_customer(db, customer, parent_id)
    for k, v in body.model_dump(exclude={"relationship_to_parent"}, exclude_unset=True).items():
        setattr(p, k, v)
    audit(db, actor=customer.user, action="parent.update", entity_type="parent", entity_id=p.id)
    db.commit()
    return parent_view(db, customer, p)


@portal.delete("/parents/{parent_id}/authorisation")
def revoke_my_authorisation(parent_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    a = customer_authorisation(db, customer.id, parent_id)
    if not a:
        raise HTTPException(404, "Not found")
    a.status, a.revoked_at = AuthStatus.REVOKED, utcnow()
    audit(db, actor=customer.user, action="authorisation.revoke", entity_type="family_authorisation", entity_id=a.id)
    db.commit()
    return {"ok": True}


# ---------------- admin ----------------
@admin.get("/customers")
def list_customers(user=Depends(require_permission("customer.read_all")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Customer).where(Customer.deleted_at.is_(None)).order_by(Customer.created_at.desc()).limit(500)).all()
    return [{**pick(c, "id", "full_name", "country", "phone", "created_at"), "email": c.user.email} for c in rows]


@admin.get("/customers/{customer_id}")
def get_customer(customer_id: uuid.UUID, user=Depends(require_permission("customer.read_all")), db: Session = Depends(get_db)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Not found")
    auths = db.scalars(select(FamilyAuthorisation).where(FamilyAuthorisation.customer_id == c.id)).all()
    parents = []
    for a in auths:
        p = db.get(Parent, a.parent_id)
        parents.append({**pick(p, *PARENT_FIELDS), "authorisation": pick(a, *AUTH_FIELDS, "relationship_to_parent")})
    audit(db, actor=user, action="customer.view", entity_type="customer", entity_id=c.id)
    db.commit()
    return {**pick(c, "id", "full_name", "country", "phone", "whatsapp_opt_in", "created_at"), "email": c.user.email, "parents": parents}


@admin.get("/parents/{parent_id}/consents")
def parent_consents(parent_id: uuid.UUID, user=Depends(require_permission("customer.read_all")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Consent).where(Consent.parent_id == parent_id).order_by(Consent.captured_at.desc())).all()
    return [pick(c, *CONSENT_FIELDS, "notes", "captured_by_user_id", "revoked_reason") for c in rows]


class ConsentBody(BaseModel):
    scopes: list[ConsentScope] = Field(min_length=1)
    given_by: str = Field(min_length=2, max_length=160)
    captured_via: CaptureMethod
    captured_at: dt.datetime | None = None
    valid_until: dt.datetime | None = None
    evidence_ref: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


@admin.post("/parents/{parent_id}/consents", status_code=201)
def record_consent(parent_id: uuid.UUID, body: ConsentBody, request: Request, user=Depends(require_permission("consent.record")), db: Session = Depends(get_db)):
    p = db.get(Parent, parent_id)
    if not p:
        raise HTTPException(404, "Parent not found")
    now = utcnow()
    c = Consent(parent_id=p.id, scopes=[s.value for s in body.scopes], given_by=body.given_by, captured_via=body.captured_via,
                captured_by_user_id=user.id, captured_at=body.captured_at or now, valid_from=body.captured_at or now,
                valid_until=body.valid_until, evidence_ref=body.evidence_ref, notes=body.notes)
    db.add(c)
    db.flush()
    audit(db, actor=user, action="consent.record", entity_type="consent", entity_id=c.id, after={"parent_id": p.id, "scopes": c.scopes, "via": body.captured_via}, ip=client_ip(request))
    db.commit()
    return pick(c, *CONSENT_FIELDS)


class RevokeBody(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


@admin.post("/consents/{consent_id}/revoke")
def revoke_consent(consent_id: uuid.UUID, body: RevokeBody, user=Depends(require_permission("consent.record")), db: Session = Depends(get_db)):
    c = db.get(Consent, consent_id)
    if not c or c.revoked_at:
        raise HTTPException(404, "Not found")
    c.revoked_at, c.revoked_reason = utcnow(), body.reason
    audit(db, actor=user, action="consent.revoke", entity_type="consent", entity_id=c.id, after={"reason": body.reason})
    db.commit()
    return pick(c, *CONSENT_FIELDS)


class ActivateBody(BaseModel):
    consent_id: uuid.UUID
    can_request_services: bool = True
    can_receive_updates: bool = True
    can_approve_costs: bool = True
    can_view_evidence: bool = False
    valid_until: dt.datetime | None = None


@admin.post("/authorisations/{auth_id}/activate")
def activate_authorisation(auth_id: uuid.UUID, body: ActivateBody, user=Depends(require_permission("consent.record")), db: Session = Depends(get_db)):
    a = db.get(FamilyAuthorisation, auth_id)
    c = db.get(Consent, body.consent_id)
    if not a or not c or c.parent_id != a.parent_id or c.revoked_at:
        raise HTTPException(409, "A valid consent for this parent is required to activate the authorisation")
    before = pick(a, "status", "can_request_services", "can_approve_costs", "can_view_evidence")
    a.status, a.valid_from, a.valid_until, a.consent_id = AuthStatus.ACTIVE, utcnow(), body.valid_until, c.id
    a.can_request_services, a.can_receive_updates = body.can_request_services, body.can_receive_updates
    a.can_approve_costs, a.can_view_evidence, a.activated_by_user_id = body.can_approve_costs, body.can_view_evidence, user.id
    audit(db, actor=user, action="authorisation.activate", entity_type="family_authorisation", entity_id=a.id, before=before, after=body.model_dump())
    db.commit()
    return pick(a, *AUTH_FIELDS)


@admin.post("/authorisations/{auth_id}/revoke")
def revoke_authorisation(auth_id: uuid.UUID, user=Depends(require_permission("consent.record")), db: Session = Depends(get_db)):
    a = db.get(FamilyAuthorisation, auth_id)
    if not a:
        raise HTTPException(404, "Not found")
    a.status, a.revoked_at = AuthStatus.REVOKED, utcnow()
    audit(db, actor=user, action="authorisation.revoke", entity_type="family_authorisation", entity_id=a.id)
    db.commit()
    return pick(a, *AUTH_FIELDS)
