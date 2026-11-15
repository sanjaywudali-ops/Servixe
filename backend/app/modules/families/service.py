import datetime as dt
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.modules.families.models import AuthStatus, Consent, Customer, FamilyAuthorisation, Parent
from app.modules.requests.models import Counter


def next_reference(db: Session, name: str, prefix: str) -> str:
    c = db.get(Counter, name, with_for_update=True)
    if c is None:
        c = Counter(name=name, value=0)
        db.add(c)
        db.flush()
    c.value += 1
    db.flush()
    return f"{prefix}-{utcnow().year}-{c.value:06d}"


def customer_authorisation(db: Session, customer_id: uuid.UUID, parent_id: uuid.UUID) -> FamilyAuthorisation | None:
    return db.scalar(
        select(FamilyAuthorisation).where(
            FamilyAuthorisation.customer_id == customer_id,
            FamilyAuthorisation.parent_id == parent_id,
            FamilyAuthorisation.status != AuthStatus.REVOKED,
        )
    )


def active_authorisation(db: Session, customer_id, parent_id, at: dt.datetime | None = None) -> FamilyAuthorisation | None:
    a = customer_authorisation(db, customer_id, parent_id)
    return a if a and a.is_active(at or utcnow()) else None


def active_consent(db: Session, parent_id, scope: str, at: dt.datetime | None = None) -> Consent | None:
    at = at or utcnow()
    rows = db.scalars(
        select(Consent).where(Consent.parent_id == parent_id, Consent.revoked_at.is_(None)).order_by(Consent.captured_at.desc())
    ).all()
    for c in rows:
        if c.covers(scope, at):
            return c
    return None


def get_parent_for_customer(db: Session, customer: Customer, parent_id) -> Parent:
    p = db.get(Parent, parent_id)
    if not p or p.deleted_at or not customer_authorisation(db, customer.id, p.id):
        raise HTTPException(404, "Parent not found")
    return p
