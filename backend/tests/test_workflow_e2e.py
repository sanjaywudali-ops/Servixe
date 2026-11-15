import datetime as dt

from tests.conftest import (ids, login, make_verified_provider, new_client, register_customer, setup_parent_with_consent)

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def create_request(customer, parent_id, **kw):
    sid, _ = ids()
    body = {"parent_id": parent_id, "service_id": str(sid), "task_details": "Check on my mother and bring groceries", **kw}
    r = customer.post(f"{API}/portal/requests", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_full_lifecycle(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin)
    prov_client, prov_id = make_verified_provider(admin)
    req = create_request(customer, parent_id, budget_cap_minor=500000)
    rid = req["id"]
    assert req["status"] == "new_request"

    assert admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "under_review"}).status_code == 200
    q = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "Visit and groceries", "provider_cost_minor": 100000})
    assert q.status_code == 201, q.text
    assert q.json()["total_minor"] == 100000 + 50000 + 9000  # cost + fee + 18% tax on fee
    assert admin.get(f"{API}/admin/requests/{rid}").json()["status"] == "approval_pending"

    # cannot assign before customer approval
    a = admin.post(f"{API}/admin/requests/{rid}/assignments", json={"provider_id": prov_id, "provider_payout_minor": 80000})
    assert a.status_code == 409

    d = customer.post(f"{API}/portal/quotes/{q.json()['id']}/decision", json={"decision": "approve"})
    assert d.status_code == 200 and d.json()["status"] == "approved"

    a = admin.post(f"{API}/admin/requests/{rid}/assignments", json={"provider_id": prov_id, "provider_payout_minor": 80000, "instructions": "Greet and deliver groceries"})
    assert a.status_code == 201, a.text
    aid = a.json()["id"]

    # provider sees minimum data before accepting
    job = prov_client.get(f"{API}/provider/jobs/{aid}").json()
    assert job["location"] is None and job["contact_phone"] is None and job["task_details"] is None
    assert prov_client.post(f"{API}/provider/jobs/{aid}/accept").status_code == 200
    job = prov_client.get(f"{API}/provider/jobs/{aid}").json()
    assert job["parent_first_name"] == "Lakshmi" and "Lakshmi Devi" not in str(job)

    assert prov_client.post(f"{API}/provider/jobs/{aid}/check-in", json={}).status_code == 200
    # cannot check out with incomplete required checklist
    assert prov_client.post(f"{API}/provider/jobs/{aid}/check-out", json={}).status_code == 409
    cl = prov_client.put(f"{API}/provider/jobs/{aid}/checklist", json={"responses": {"greeted": {"done": True}}})
    assert cl.json()["complete"] is True
    up = prov_client.post(f"{API}/provider/jobs/{aid}/evidence", files={"file": ("p.png", PNG, "image/png")}, data={"purpose": "completion_photo"})
    assert up.status_code == 201, up.text
    assert prov_client.post(f"{API}/provider/jobs/{aid}/check-out", json={}).status_code == 200

    # staff cannot skip the quality gate via the generic endpoint
    assert admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "completed"}).status_code == 409
    qr = admin.post(f"{API}/admin/requests/{rid}/quality-review", json={"outcome": "pass", "customer_message": "All done, mother is well."})
    assert qr.status_code == 200 and qr.json()["status"] == "completed"

    # cannot close before invoice/payment close-out
    assert admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "closed"}).status_code == 409
    inv = admin.post(f"{API}/admin/requests/{rid}/invoice").json()
    assert admin.post(f"{API}/admin/invoices/{inv['id']}/issue").status_code == 200

    import json
    from app.core.security import sign
    ev = {"event_id": "evt_1", "type": "payment.succeeded", "payment_id": "pay_1", "invoice_number": inv["number"], "amount_minor": inv["total_minor"], "currency": "INR"}
    body = json.dumps(ev).encode()
    sig = sign("whsec_test", body)
    w = new_client()
    assert w.post(f"{API}/webhooks/payments", content=body, headers={"X-Signature": sig}).json()["status"] == "ok"
    assert w.post(f"{API}/webhooks/payments", content=body, headers={"X-Signature": sig}).json()["status"] == "duplicate"
    assert w.post(f"{API}/webhooks/payments", content=body, headers={"X-Signature": "bad"}).status_code == 401

    cl = admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "closed"})
    assert cl.status_code == 200, cl.text
    # customer-visible evidence only after ops releases it
    assert customer.get(f"{API}/portal/requests/{rid}/evidence").json() == []
    ev_id = admin.get(f"{API}/admin/requests/{rid}/evidence").json()[0]["id"]
    admin.patch(f"{API}/admin/evidence/{ev_id}", json={"access_scope": "customer_visible"})
    assert len(customer.get(f"{API}/portal/requests/{rid}/evidence").json()) == 1
    url = customer.get(f"{API}/portal/evidence/{ev_id}/url").json()["url"]
    assert new_client().get(url).status_code == 200
    # audit trail exists
    actions = {a["action"] for a in admin.get(f"{API}/admin/audit-logs").json()}
    assert {"request.transition", "quote.approve", "consent.record", "evidence.access", "assignment.create"} <= actions


def test_no_work_without_consent(admin, customer):
    p = customer.post(f"{API}/portal/parents", json={"full_name": "Parent X"}).json()
    req = create_request(customer, p["id"])
    admin.post(f"{API}/admin/requests/{req['id']}/transition", json={"to_status": "under_review"})
    r = admin.post(f"{API}/admin/requests/{req['id']}/transition", json={"to_status": "quote_pending"})
    assert r.status_code == 409 and "consent" in r.json()["detail"].lower()


def test_renewed_approval_pauses_work(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin)
    prov_client, prov_id = make_verified_provider(admin)
    rid = create_request(customer, parent_id)["id"]
    admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "under_review"})
    q1 = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "scope one", "provider_cost_minor": 1000}).json()
    customer.post(f"{API}/portal/quotes/{q1['id']}/decision", json={"decision": "approve"})
    aid = admin.post(f"{API}/admin/requests/{rid}/assignments", json={"provider_id": prov_id}).json()["id"]
    prov_client.post(f"{API}/provider/jobs/{aid}/accept")
    # cost changes materially -> new version, request paused, check-in blocked
    q2 = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "scope two", "provider_cost_minor": 5000}).json()
    assert q2["version"] == 2
    assert admin.get(f"{API}/admin/requests/{rid}").json()["status"] == "approval_pending"
    assert prov_client.post(f"{API}/provider/jobs/{aid}/check-in", json={}).status_code == 409
    customer.post(f"{API}/portal/quotes/{q2['id']}/decision", json={"decision": "approve"})
    assert admin.get(f"{API}/admin/requests/{rid}").json()["status"] == "assigned"
    assert prov_client.post(f"{API}/provider/jobs/{aid}/check-in", json={}).status_code == 200


def test_budget_cap_flag_and_reject(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin)
    rid = create_request(customer, parent_id, budget_cap_minor=1000)["id"]
    admin.post(f"{API}/admin/requests/{rid}/transition", json={"to_status": "under_review"})
    q = admin.post(f"{API}/admin/requests/{rid}/quotes", json={"scope_summary": "scope one", "provider_cost_minor": 100000}).json()
    assert q["exceeds_budget_cap"] is True
    customer.post(f"{API}/portal/quotes/{q['id']}/decision", json={"decision": "reject", "note": "too high"})
    assert admin.get(f"{API}/admin/requests/{rid}").json()["status"] == "under_review"


def test_high_severity_incident_blocks_closure(admin, customer):
    parent_id, _ = setup_parent_with_consent(customer, admin)
    rid = create_request(customer, parent_id)["id"]
    inc = admin.post(f"{API}/admin/incidents", json={"request_id": rid, "category": "safety", "severity": "high", "description": "Parent fell during visit"}).json()
    assert admin.get(f"{API}/admin/requests/{rid}").json()["status"] == "incident_open"
    r = admin.patch(f"{API}/admin/incidents/{inc['id']}", json={"status": "closed"})
    assert r.status_code == 422  # closure review required
    r = admin.patch(f"{API}/admin/incidents/{inc['id']}", json={"status": "closed", "closure_review": "Reviewed with family"})
    assert r.status_code == 200
    assert admin.get(f"{API}/admin/requests/{rid}").json()["status"] == "new_request"
