import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.serialize import pick
from app.db import get_db
from app.modules.audit.service import audit
from app.modules.evidence.models import ChecklistTemplate
from app.modules.providers.models import provider_services
from app.modules.requests.models import ServiceRequest
from app.modules.catalogue.models import Package, PackageInterval, PricingRule, Service, ServiceArea

public = APIRouter(prefix="/public", tags=["public"])
admin = APIRouter(prefix="/admin/catalogue", tags=["admin: catalogue"])

SVC = ("id", "code", "name", "summary", "description", "inclusions", "exclusions", "requirements", "required_consent_scope", "is_active", "sort_order")


@public.get("/services")
def services(db: Session = Depends(get_db)):
    rows = db.scalars(select(Service).where(Service.is_active.is_(True)).order_by(Service.sort_order, Service.name)).all()
    out = []
    for s in rows:
        d = pick(s, "id", "code", "name", "summary", "description", "inclusions", "exclusions", "requirements")
        rule = db.scalar(select(PricingRule).where(PricingRule.service_id == s.id, PricingRule.service_area_id.is_(None), PricingRule.is_active.is_(True)))
        d["indicative_min_minor"] = rule.indicative_min_minor if rule else None
        d["indicative_max_minor"] = rule.indicative_max_minor if rule else None
        d["currency"] = rule.currency if rule else "INR"
        out.append(d)
    return out


@public.get("/packages")
def packages(db: Session = Depends(get_db)):
    return [pick(p, "id", "code", "name", "description", "interval", "indicative_price_minor", "currency", "entitlements")
            for p in db.scalars(select(Package).where(Package.is_active.is_(True)))]


@public.get("/areas")
def areas(db: Session = Depends(get_db)):
    return [pick(a, "id", "name", "district", "state") for a in db.scalars(select(ServiceArea).where(ServiceArea.is_active.is_(True)).order_by(ServiceArea.name))]


# Authenticated read for portals (includes consent scope etc.)
@admin.get("/services")
def admin_services(user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    return [pick(s, *SVC) for s in db.scalars(select(Service).order_by(Service.sort_order))]


class ServiceBody(BaseModel):
    code: str = Field(pattern="^[a-z0-9_]{2,40}$")
    name: str = Field(min_length=2, max_length=120)
    summary: str = Field(default="", max_length=300)
    description: str = ""
    inclusions: list[str] = []
    exclusions: list[str] = []
    requirements: str = ""
    required_consent_scope: str = Field(default="home_visit", pattern="^(home_visit|errands|photographs|updates|information_sharing)$")
    is_active: bool = True
    sort_order: int = 100


@admin.post("/services", status_code=201)
def create_service(body: ServiceBody, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    if db.scalar(select(Service).where(Service.code == body.code)):
        raise HTTPException(409, "Service code already exists")
    s = Service(**body.model_dump())
    db.add(s)
    audit(db, actor=user, action="service.create", entity_type="service", entity_id=None, after=body.model_dump())
    db.commit()
    return pick(s, *SVC)


@admin.put("/services/{service_id}")
def update_service(service_id: uuid.UUID, body: ServiceBody, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    s = db.get(Service, service_id)
    if not s:
        raise HTTPException(404, "Not found")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    audit(db, actor=user, action="service.update", entity_type="service", entity_id=s.id, after=body.model_dump())
    db.commit()
    return pick(s, *SVC)


@admin.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: uuid.UUID, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    """Hard-delete only a service that has never been requested. Otherwise it must be put on hold (is_active=false)."""
    s = db.get(Service, service_id)
    if not s:
        raise HTTPException(404, "Not found")
    if db.scalar(select(ServiceRequest.id).where(ServiceRequest.service_id == s.id).limit(1)):
        raise HTTPException(409, "This service has requests on record and cannot be deleted. Put it on hold instead.")
    before = pick(s, *SVC)
    for r in db.scalars(select(PricingRule).where(PricingRule.service_id == s.id)):
        db.delete(r)
    for t in db.scalars(select(ChecklistTemplate).where(ChecklistTemplate.service_id == s.id)):
        db.delete(t)
    db.execute(provider_services.delete().where(provider_services.c.service_id == s.id))
    db.delete(s)
    audit(db, actor=user, action="service.delete", entity_type="service", entity_id=service_id, before=before)
    db.commit()


class AreaBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    district: str = "Nellore"
    state: str = "Andhra Pradesh"
    pincodes: list[str] = []
    is_active: bool = True


@admin.get("/areas")
def admin_areas(user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    return [pick(a, "id", "name", "district", "state", "pincodes", "is_active") for a in db.scalars(select(ServiceArea))]


@admin.post("/areas", status_code=201)
def create_area(body: AreaBody, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    a = ServiceArea(**body.model_dump())
    db.add(a)
    audit(db, actor=user, action="service_area.create", entity_type="service_area", entity_id=None, after=body.model_dump())
    db.commit()
    return pick(a, "id", "name", "district", "state", "pincodes", "is_active")


class PricingBody(BaseModel):
    service_id: uuid.UUID
    service_area_id: uuid.UUID | None = None
    currency: str = Field(default="INR", pattern="^[A-Z]{3}$")
    coordination_fee_minor: int = Field(ge=0)
    urgent_surcharge_minor: int = Field(default=0, ge=0)
    tax_percent: float = Field(default=18, ge=0, le=100)
    indicative_min_minor: int | None = Field(default=None, ge=0)
    indicative_max_minor: int | None = Field(default=None, ge=0)
    notes: str | None = None


@admin.get("/pricing")
def list_pricing(user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    return [pick(r, "id", "service_id", "service_area_id", "currency", "coordination_fee_minor", "urgent_surcharge_minor", "tax_percent", "indicative_min_minor", "indicative_max_minor", "notes", "is_active") for r in db.scalars(select(PricingRule))]


@admin.post("/pricing", status_code=201)
def upsert_pricing(body: PricingBody, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    r = db.scalar(select(PricingRule).where(PricingRule.service_id == body.service_id, PricingRule.service_area_id == body.service_area_id)) \
        if body.service_area_id else db.scalar(select(PricingRule).where(PricingRule.service_id == body.service_id, PricingRule.service_area_id.is_(None)))
    data = body.model_dump()
    if r:
        for k, v in data.items():
            setattr(r, k, v)
    else:
        r = PricingRule(**data)
        db.add(r)
    audit(db, actor=user, action="pricing.upsert", entity_type="pricing_rule", entity_id=None, after=data)
    db.commit()
    return pick(r, "id", "service_id", "service_area_id", "coordination_fee_minor", "tax_percent")


class PackageBody(BaseModel):
    code: str = Field(pattern="^[a-z0-9_]{2,40}$")
    name: str
    description: str = ""
    interval: PackageInterval = PackageInterval.MONTHLY
    indicative_price_minor: int | None = None
    currency: str = "INR"
    entitlements: list[str] = []
    is_active: bool = True


@admin.post("/packages", status_code=201)
def create_package(body: PackageBody, user=Depends(require_permission("catalogue.manage")), db: Session = Depends(get_db)):
    p = Package(**body.model_dump())
    db.add(p)
    audit(db, actor=user, action="package.create", entity_type="package", entity_id=None, after=body.model_dump())
    db.commit()
    return pick(p, "id", "code", "name")
