import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import client_ip, require_permission
from app.core.ratelimit import limiter
from app.core.serialize import pick
from app.db import get_db
from app.modules.audit.service import audit
from app.modules.enquiries.models import ContactMethod, Enquiry, EnquiryStatus

public = APIRouter(prefix="/public", tags=["public"])
admin = APIRouter(prefix="/admin/enquiries", tags=["admin: enquiries"])


class EnquiryBody(BaseModel):
    """Lead-stage fields only. Deliberately no free-text health/medical field."""
    name: str = Field(min_length=2, max_length=160)
    country: str = Field(min_length=2, max_length=80)
    contact_method: ContactMethod
    contact_value: str = Field(min_length=3, max_length=255)
    parent_city_area: str = Field(min_length=2, max_length=160)
    service_interest: str = Field(min_length=2, max_length=120)
    callback_requested: bool = False
    consent_to_contact: bool
    captcha_token: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if not self.consent_to_contact:
            raise ValueError("Consent to be contacted is required")
        if self.contact_method == ContactMethod.EMAIL and "@" not in self.contact_value:
            raise ValueError("Enter a valid email address")
        return self


def verify_captcha(token: str | None, ip: str | None) -> bool:
    if not settings.turnstile_secret:
        return True  # dev only; set TURNSTILE_SECRET in staging/production
    if not token:
        return False
    try:
        r = httpx.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                       data={"secret": settings.turnstile_secret, "response": token, "remoteip": ip}, timeout=5)
        return bool(r.json().get("success"))
    except Exception:
        return False


@public.post("/enquiries", status_code=201, dependencies=[Depends(limiter("enquiry", 5, 600))])
def submit(body: EnquiryBody, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    if not verify_captcha(body.captcha_token, ip):
        raise HTTPException(400, "Bot check failed. Please retry.")
    e = Enquiry(**body.model_dump(exclude={"captcha_token"}))
    db.add(e)
    db.commit()
    return {"ok": True, "message": "Thank you. Our team will contact you shortly. Servixe is not an emergency service."}


@admin.get("")
def list_enquiries(status: EnquiryStatus | None = None, user=Depends(require_permission("enquiry.manage")), db: Session = Depends(get_db)):
    q = select(Enquiry).order_by(Enquiry.created_at.desc()).limit(300)
    if status:
        q = q.where(Enquiry.status == status)
    return [pick(e, "id", "name", "country", "contact_method", "contact_value", "parent_city_area", "service_interest", "callback_requested", "status", "handled_by", "created_at") for e in db.scalars(q)]


class EnquiryPatch(BaseModel):
    status: EnquiryStatus


@admin.patch("/{enquiry_id}")
def update_enquiry(enquiry_id: uuid.UUID, body: EnquiryPatch, user=Depends(require_permission("enquiry.manage")), db: Session = Depends(get_db)):
    e = db.get(Enquiry, enquiry_id)
    if not e:
        raise HTTPException(404, "Not found")
    e.status, e.handled_by = body.status, user.full_name or user.email
    audit(db, actor=user, action="enquiry.update", entity_type="enquiry", entity_id=e.id, after={"status": body.status})
    db.commit()
    return pick(e, "id", "status", "handled_by")
