"""Seed reference data: roles/permissions, Nellore starter areas, example services, pricing, checklists, packages and
an initial admin. Idempotent. All catalogue content is a STARTING POINT to be confirmed in the pre-development workshop
(spec section 14): final services, exclusions, micro-areas and prices are business decisions.

Usage:  python -m scripts.seed            (uses SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD)
"""
import os
import sys

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db import SessionLocal
from app.modules.catalogue.models import Package, PackageInterval, PricingRule, Service, ServiceArea
from app.modules.evidence.models import ChecklistTemplate
from app.modules.identity.models import Role, User
from app.rbac import seed_rbac

AREAS = ["Stonehousepet", "Dargamitta", "Magunta Layout", "Trunk Road", "Vedayapalem", "Podalakur Road"]  # placeholders

COMMON_EXCL = ["Medical advice, diagnosis or interpretation of medical reports", "Emergency response", "Holding cash or banking credentials"]

SERVICES = [
    dict(code="wellbeing_visit", name="Parent wellbeing visit", summary="A verified local visitor checks in on your parent and sends you an update.",
         description="A verified provider visits your parent at home at an agreed time, completes a friendly check-in checklist and shares a short update with you.",
         inclusions=["Friendly in-person check-in", "Checklist-based visit", "Update to the family", "Photos only if your parent agrees"],
         exclusions=COMMON_EXCL, required_consent_scope="home_visit", sort_order=10, fee=40000, lo=60000, hi=120000,
         checklist=[("arrived", "Arrived and introduced myself", True), ("greeted", "Greeted parent and confirmed they are comfortable", True),
                    ("home_ok", "Noted general home condition (no medical judgement)", True), ("concerns", "Recorded any concerns raised by parent", False)]),
    dict(code="errands", name="Errands & groceries", summary="Groceries and household errands done at your approved budget.",
         description="A verified provider completes approved errands (groceries, household items) within the quoted budget and shares receipts.",
         inclusions=["Shopping to an approved list", "Receipts shared", "Delivery to your parent"],
         exclusions=COMMON_EXCL, required_consent_scope="errands", sort_order=20, fee=30000, lo=50000, hi=150000,
         checklist=[("list", "Confirmed the approved list", True), ("receipt", "Receipt uploaded", True), ("delivered", "Delivered items to parent", True)]),
    dict(code="pharmacy_pickup", name="Pharmacy pickup & delivery", summary="Collect and deliver medicines already prescribed by your parent's doctor.",
         description="Pickup and delivery of already-prescribed medicines from a pharmacy. Servixe does not advise on, select or change medicines.",
         inclusions=["Collection from the named pharmacy", "Receipt shared", "Safe delivery to parent"],
         exclusions=COMMON_EXCL + ["Substituting or recommending medicines"], required_consent_scope="errands", sort_order=30, fee=30000, lo=40000, hi=100000,
         checklist=[("rx", "Collected exactly what the pharmacy supplied", True), ("receipt", "Receipt uploaded", True), ("delivered", "Delivered to parent", True)]),
    dict(code="appointment_accompaniment", name="Appointment accompaniment", summary="Accompany your parent to an appointment with arranged transport.",
         description="A verified provider accompanies your parent to an appointment and back, with transport arranged on your approval. The provider does not make or relay medical decisions.",
         inclusions=["Transport coordination", "Accompaniment to and from", "Update to the family"],
         exclusions=COMMON_EXCL, required_consent_scope="home_visit", sort_order=40, fee=60000, lo=100000, hi=300000,
         checklist=[("pickup", "Picked up parent safely", True), ("attended", "Accompanied parent at the venue", True), ("returned", "Returned parent home", True)]),
]


def main() -> None:
    with SessionLocal() as db:
        seed_rbac(db)
        for name in AREAS:
            if not db.scalar(select(ServiceArea).where(ServiceArea.name == name)):
                db.add(ServiceArea(name=name))
        db.flush()
        for s in SERVICES:
            s = dict(s)
            fee, lo, hi, checklist = s.pop("fee"), s.pop("lo"), s.pop("hi"), s.pop("checklist")
            svc = db.scalar(select(Service).where(Service.code == s["code"]))
            if not svc:
                svc = Service(**s)
                db.add(svc)
                db.flush()
                db.add(PricingRule(service_id=svc.id, coordination_fee_minor=fee, urgent_surcharge_minor=20000, tax_percent=18,
                                   indicative_min_minor=lo, indicative_max_minor=hi, currency="INR",
                                   notes="Starter value - confirm in pricing workshop"))
                db.add(ChecklistTemplate(service_id=svc.id, name=f"{svc.name} checklist",
                                         items=[{"key": k, "label": l, "required": r} for k, l, r in checklist]))
        if not db.scalar(select(Package).where(Package.code == "monthly_checkin")):
            db.add(Package(code="monthly_checkin", name="Monthly check-in plan", description="Indicative plan: regular visits plus priority scheduling. Final quotes depend on location, timing and provider cost.",
                           interval=PackageInterval.MONTHLY, indicative_price_minor=250000, entitlements=["4 wellbeing visits / month", "Priority scheduling"]))
        email = os.environ.get("SEED_ADMIN_EMAIL")
        password = os.environ.get("SEED_ADMIN_PASSWORD")
        if email and password:
            if not db.scalar(select(User).where(User.email == email.lower())):
                role = db.scalar(select(Role).where(Role.name == "admin"))
                db.add(User(email=email.lower(), full_name="Servixe Admin", password_hash=hash_password(password), role_id=role.id, email_verified_at=None))
                print(f"Created admin {email}. MFA enrolment is required at first sign-in.")
        else:
            print("SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD not set: skipping admin creation.", file=sys.stderr)
        db.commit()
    print("Seed complete.")


if __name__ == "__main__":
    main()
