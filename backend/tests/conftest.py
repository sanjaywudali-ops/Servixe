import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db", "ENV": "test", "LOCAL_STORAGE_DIR": f"{_tmp}/storage",
    "CELERY_EAGER": "true", "RATE_LIMIT_ENABLED": "false", "SECRET_KEY": "test-secret",
    "PAYMENT_WEBHOOK_SECRET": "whsec_test",
})

import email_validator  # noqa: E402
email_validator.TEST_ENVIRONMENT = True  # allow .test domains in tests
import datetime as dt  # noqa: E402

import pyotp  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.catalogue.models import PricingRule, Service, ServiceArea  # noqa: E402
from app.modules.evidence.models import ChecklistTemplate  # noqa: E402
from app.modules.identity.models import Role, User  # noqa: E402
from app.rbac import seed_rbac  # noqa: E402

PW = "Str0ngPassword!"
HDR = {"X-Requested-With": "Servixe"}


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_rbac(db)
        area = ServiceArea(name="Stonehousepet")
        svc = Service(code="home_visit", name="Parent home visit", required_consent_scope="home_visit")
        db.add_all([area, svc])
        db.flush()
        db.add(PricingRule(service_id=svc.id, coordination_fee_minor=50000, urgent_surcharge_minor=20000, tax_percent=18, currency="INR"))
        db.add(ChecklistTemplate(service_id=svc.id, name="Visit", items=[{"key": "greeted", "label": "Greeted parent", "required": True}, {"key": "photo", "label": "Photo taken", "required": False}]))
        db.commit()
    yield


def new_client() -> TestClient:
    return TestClient(app, headers=HDR)


def make_user(email: str, role: str, full_name="Test User") -> User:
    with SessionLocal() as db:
        r = db.scalar(select(Role).where(Role.name == role))
        u = User(email=email, full_name=full_name, password_hash=hash_password(PW), role_id=r.id)
        db.add(u)
        db.commit()
        return u


def login(client: TestClient, email: str, password: str = PW):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def login_staff(email: str, role="admin") -> TestClient:
    make_user(email, role)
    c = new_client()
    lr = login(c, email)
    assert lr.status_code == 200, lr.text
    assert lr.json()["mfa_required"] is True
    secret = c.post("/api/v1/auth/mfa/setup").json()["secret"]
    r = c.post("/api/v1/auth/mfa/verify", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200, r.text
    return c


def register_customer(email: str) -> TestClient:
    c = new_client()
    r = c.post("/api/v1/auth/register", json={"email": email, "password": PW, "full_name": "Anil Kumar", "country": "USA"})
    assert r.status_code == 201, r.text
    return c


def ids():
    with SessionLocal() as db:
        return db.scalar(select(Service)).id, db.scalar(select(ServiceArea)).id


@pytest.fixture
def admin():
    return login_staff("admin@nd.test", "admin")


@pytest.fixture
def support():
    return login_staff("support@nd.test", "support")


@pytest.fixture
def customer():
    return register_customer("a@cust.test")


def setup_parent_with_consent(customer: TestClient, admin: TestClient, scopes=("home_visit", "photographs", "updates")):
    p = customer.post("/api/v1/portal/parents", json={"full_name": "Lakshmi Devi", "phone": "9000000000", "area": "Stonehousepet", "address_line": "12 Main Rd"}).json()
    c = admin.post(f"/api/v1/admin/parents/{p['id']}/consents", json={"scopes": list(scopes), "given_by": "Lakshmi Devi", "captured_via": "in_person"})
    assert c.status_code == 201, c.text
    a = admin.post(f"/api/v1/admin/authorisations/{p['authorisation']['id']}/activate", json={"consent_id": c.json()["id"], "can_view_evidence": True})
    assert a.status_code == 200, a.text
    return p["id"], c.json()["id"]


def make_verified_provider(admin: TestClient, email="prov@nd.test") -> tuple[TestClient, str]:
    sid, aid = ids()
    r = admin.post("/api/v1/admin/providers", json={"full_name": "Ravi Kumar", "phone": "9111111111", "email": email, "service_ids": [str(sid)], "service_area_ids": [str(aid)], "send_invite": False})
    pid = r.json()["id"]
    pdf = b"%PDF-1.4 test"
    for t in ("identity", "address", "reference"):
        d = admin.post(f"/api/v1/admin/providers/{pid}/documents", files={"file": ("d.pdf", pdf, "application/pdf")}, data={"doc_type": t})
        assert d.status_code == 201, d.text
        assert admin.post(f"/api/v1/admin/providers/documents/{d.json()['id']}/review", json={"decision": "approved"}).status_code == 200
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    admin.patch(f"/api/v1/admin/providers/{pid}", json={"interview_at": now, "induction_completed_at": now})
    r = admin.post(f"/api/v1/admin/providers/{pid}/status", json={"status": "verified"})
    assert r.status_code == 200, r.text
    # give the provider a login
    with SessionLocal() as db:
        from app.modules.providers.models import Provider
        role = db.scalar(select(Role).where(Role.name == "provider"))
        u = User(email=email, full_name="Ravi Kumar", password_hash=hash_password(PW), role_id=role.id)
        db.add(u)
        db.flush()
        db.get(Provider, __import__("uuid").UUID(pid)).user_id = u.id
        db.commit()
    pc = new_client()
    assert login(pc, email).status_code == 200
    return pc, pid
