import json

from tests.conftest import (PW, ids, login, login_staff, make_user, make_verified_provider, new_client, register_customer, setup_parent_with_consent)

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def test_csrf_header_required():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)  # no X-Requested-With
    assert c.post(f"{API}/auth/login", json={"email": "x@y.z", "password": "x"}).status_code == 403


def test_customer_cannot_see_other_customer(admin):
    a = register_customer("a@c.test")
    b = register_customer("b@c.test")
    pa, _ = setup_parent_with_consent(a, admin)
    sid, _ = ids()
    rid = a.post(f"{API}/portal/requests", json={"parent_id": pa, "service_id": str(sid), "task_details": "Visit please"}).json()["id"]
    assert b.get(f"{API}/portal/requests/{rid}").status_code == 404
    assert b.get(f"{API}/portal/parents/{pa}").status_code == 404
    assert b.get(f"{API}/portal/requests").json() == []
    # B cannot create a request for A's parent
    r = b.post(f"{API}/portal/requests", json={"parent_id": pa, "service_id": str(sid), "task_details": "Visit please"})
    assert r.status_code == 404


def test_payer_has_no_authority_until_consent_recorded(admin, customer):
    p = customer.post(f"{API}/portal/parents", json={"full_name": "Parent Y"}).json()
    assert p["authorisation"]["status"] == "pending" and p["consent_status"] == "none"


def test_provider_cannot_view_unassigned_job(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin)
    p1, prov1 = make_verified_provider(admin, "p1@nd.test")
    p2, prov2 = make_verified_provider(admin, "p2@nd.test")
    sid, _ = ids()
    rid = customer.post(f"{API}/portal/requests", json={"parent_id": parent_id, "service_id": str(sid), "task_details": "Visit please"}).json()["id"]
    admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "under_review"})
    q = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "scope", "provider_cost_minor": 1}).json()
    customer.post(f"{API}/portal/quotes/{q['id']}/decision", json={"decision": "approve"})
    aid = admin.post(f"{API}/admin/requests/{rid}/assignments", json={"provider_id": prov1}).json()["id"]
    assert p2.get(f"{API}/provider/jobs/{aid}").status_code == 404
    assert p2.get(f"{API}/provider/jobs").json() == []
    assert p1.get(f"{API}/provider/jobs/{aid}").status_code == 200


def test_support_cannot_do_admin_only_actions(support, admin):
    assert support.get(f"{API}/admin/audit-logs").status_code == 403
    assert support.post(f"{API}/admin/staff", json={"email": "n@nd.test", "full_name": "New", "role": "admin"}).status_code == 403
    assert support.post(f"{API}/admin/catalogue/areas", json={"name": "Z Area"}).status_code == 403
    assert admin.post(f"{API}/admin/catalogue/areas", json={"name": "Z Area"}).status_code == 201
    assert support.get(f"{API}/admin/overview").status_code == 200


def test_customer_cannot_reach_admin_endpoints(customer):
    assert customer.get(f"{API}/admin/requests").status_code == 403
    assert customer.get(f"{API}/admin/audit-logs").status_code == 403


def test_staff_requires_mfa():
    make_user("s@nd.test", "admin")
    c = new_client()
    assert login(c, "s@nd.test").json()["mfa_required"] is True
    assert c.get(f"{API}/admin/overview").status_code == 403
    assert c.post(f"{API}/auth/mfa/verify", json={"code": "000000"}).status_code in (401, 409)


def test_login_lockout_and_generic_error():
    make_user("l@c.test", "customer")
    c = new_client()
    assert login(c, "nobody@c.test", "x" * 12).json()["detail"] == "Incorrect email or password"
    for _ in range(5):
        assert login(c, "l@c.test", "wrong-password").status_code == 401
    assert login(c, "l@c.test", PW).status_code == 423


def test_session_revoked_on_password_change():
    c1, c2 = register_customer("pw@c.test"), new_client()
    login(c2, "pw@c.test")
    r = c1.post(f"{API}/auth/password/change", json={"current_password": PW, "new_password": "An0therStrongPass"})
    assert r.status_code == 200
    assert c1.get(f"{API}/auth/me").status_code == 200  # current session kept
    assert c2.get(f"{API}/auth/me").status_code == 401  # others revoked


def test_upload_validation(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin)
    pc, prov = make_verified_provider(admin)
    sid, _ = ids()
    rid = customer.post(f"{API}/portal/requests", json={"parent_id": parent_id, "service_id": str(sid), "task_details": "Visit please"}).json()["id"]
    admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "under_review"})
    q = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "scope", "provider_cost_minor": 1}).json()
    customer.post(f"{API}/portal/quotes/{q['id']}/decision", json={"decision": "approve"})
    aid = admin.post(f"{API}/admin/requests/{rid}/assignments", json={"provider_id": prov}).json()["id"]
    pc.post(f"{API}/provider/jobs/{aid}/accept")
    pc.post(f"{API}/provider/jobs/{aid}/check-in", json={})
    up = lambda name, data, ctype: pc.post(f"{API}/provider/jobs/{aid}/evidence", files={"file": (name, data, ctype)}, data={"purpose": "completion_photo"})
    assert up("x.exe", b"MZ" + b"0" * 50, "application/x-msdownload").status_code == 422
    assert up("x.png", b"not really a png", "image/png").status_code == 422
    assert up("big.png", PNG + b"0" * (9 * 1024 * 1024), "image/png").status_code == 422
    assert up("ok.png", PNG, "image/png").status_code == 201


def test_photo_requires_parent_consent(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin, scopes=("home_visit",))  # no photographs
    pc, prov = make_verified_provider(admin)
    sid, _ = ids()
    rid = customer.post(f"{API}/portal/requests", json={"parent_id": parent_id, "service_id": str(sid), "task_details": "Visit please"}).json()["id"]
    admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "under_review"})
    q = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "scope", "provider_cost_minor": 1}).json()
    customer.post(f"{API}/portal/quotes/{q['id']}/decision", json={"decision": "approve"})
    aid = admin.post(f"{API}/admin/requests/{rid}/assignments", json={"provider_id": prov}).json()["id"]
    pc.post(f"{API}/provider/jobs/{aid}/accept")
    pc.post(f"{API}/provider/jobs/{aid}/check-in", json={})
    r = pc.post(f"{API}/provider/jobs/{aid}/evidence", files={"file": ("a.png", PNG, "image/png")}, data={"purpose": "completion_photo"})
    assert r.status_code == 403


def test_signed_link_expiry(monkeypatch):
    from app.core import storage
    from app.core.storage import LocalStorage, verify_local_token
    import time

    s = LocalStorage(storage.settings.local_storage_dir)
    url = s.signed_url("k", "f.png", "image/png", ttl=1)
    token = url.rsplit("/", 1)[1]
    assert verify_local_token(token)
    assert verify_local_token(token[:-2] + "00") is None
    time.sleep(2.1)
    assert verify_local_token(token) is None


def test_public_enquiry_minimal_data():
    c = new_client()
    body = {"name": "Priya", "country": "UK", "contact_method": "email", "contact_value": "p@x.test", "parent_city_area": "Nellore", "service_interest": "Home visit", "consent_to_contact": True}
    assert c.post(f"{API}/public/enquiries", json=body).status_code == 201
    assert c.post(f"{API}/public/enquiries", json={**body, "consent_to_contact": False}).status_code == 422


def test_audit_immutable():
    import pytest
    from app.db import SessionLocal
    from app.modules.audit.models import AuditLog
    from app.modules.audit.service import audit

    with SessionLocal() as db:
        row = audit(db, action="x", entity_type="t")
        db.commit()
        row.action = "tampered"
        with pytest.raises(RuntimeError):
            db.commit()
