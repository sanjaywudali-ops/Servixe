import datetime as dt
import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import client_ip, require_customer, require_permission
from app.core.serialize import pick
from app.db import get_db, utcnow
from app.modules.audit.service import audit
from app.modules.billing.gateway import get_gateway
from app.modules.billing.models import (Invoice, InvoiceStatus, Payment, PaymentStatus, PayoutStatus, ProviderPayout, Refund,
                                        RefundStatus, WebhookEvent)
from app.modules.billing.service import apply_successful_payment, create_invoice_from_approval
from app.modules.families.models import Customer
from app.modules.notifications.service import link, notify
from app.modules.requests.router import load

admin = APIRouter(tags=["admin: billing"])
portal = APIRouter(prefix="/portal", tags=["customer: billing"])
webhooks = APIRouter(prefix="/webhooks", tags=["webhooks"])

INV_FIELDS = ("id", "number", "request_id", "status", "line_items", "provider_cost_minor", "coordination_fee_minor", "tax_minor",
              "total_minor", "currency", "issued_at", "due_at", "paid_at", "checkout_url", "created_at")


# ---------------- admin ----------------
@admin.post("/admin/requests/{request_id}/invoice", status_code=201)
def make_invoice(request_id: uuid.UUID, user=Depends(require_permission("billing.manage")), db: Session = Depends(get_db)):
    req = load(db, request_id)
    inv = create_invoice_from_approval(db, req)
    audit(db, actor=user, action="invoice.create", entity_type="invoice", entity_id=inv.id, after={"total_minor": inv.total_minor})
    db.commit()
    return pick(inv, *INV_FIELDS)


@admin.post("/admin/invoices/{invoice_id}/issue")
def issue_invoice(invoice_id: uuid.UUID, user=Depends(require_permission("billing.manage")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.status != InvoiceStatus.DRAFT:
        raise HTTPException(409, "Only draft invoices can be issued")
    inv.status, inv.issued_at, inv.due_at = InvoiceStatus.ISSUED, utcnow(), utcnow() + dt.timedelta(days=7)
    audit(db, actor=user, action="invoice.issue", entity_type="invoice", entity_id=inv.id)
    db.commit()
    c = db.get(Customer, inv.customer_id)
    notify(db, template_key="invoice_issued", user=c.user, request_id=inv.request_id, context={"number": inv.number, "link": link(f"/portal/invoices/{inv.id}")})
    return pick(inv, *INV_FIELDS)


class WaiveBody(BaseModel):
    reason: str = Field(min_length=5, max_length=255)


@admin.post("/admin/invoices/{invoice_id}/waive")
def waive(invoice_id: uuid.UUID, body: WaiveBody, user=Depends(require_permission("refund.approve")), db: Session = Depends(get_db)):
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.status not in (InvoiceStatus.DRAFT, InvoiceStatus.ISSUED):
        raise HTTPException(409, "Invoice cannot be waived")
    inv.waived_reason = body.reason
    inv.status = InvoiceStatus.PAID
    inv.paid_at = utcnow()
    audit(db, actor=user, action="invoice.waive", entity_type="invoice", entity_id=inv.id, after={"reason": body.reason})
    db.commit()
    return pick(inv, *INV_FIELDS)


@admin.get("/admin/invoices")
def list_invoices(user=Depends(require_permission("billing.manage")), db: Session = Depends(get_db)):
    return [pick(i, *INV_FIELDS) for i in db.scalars(select(Invoice).order_by(Invoice.created_at.desc()).limit(300)).all()]


class RefundBody(BaseModel):
    payment_id: uuid.UUID
    amount_minor: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=500)


@admin.post("/admin/refunds", status_code=201)
def request_refund(body: RefundBody, user=Depends(require_permission("billing.manage")), db: Session = Depends(get_db)):
    pay = db.get(Payment, body.payment_id)
    if not pay or pay.status != PaymentStatus.SUCCEEDED:
        raise HTTPException(409, "Only succeeded payments can be refunded")
    already = db.scalar(select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(Refund.payment_id == pay.id, Refund.status != RefundStatus.REJECTED))
    if already + body.amount_minor > pay.amount_minor:
        raise HTTPException(409, "Refund exceeds the amount paid")
    r = Refund(payment_id=pay.id, invoice_id=pay.invoice_id, amount_minor=body.amount_minor, reason=body.reason, requested_by_user_id=user.id)
    db.add(r)
    audit(db, actor=user, action="refund.request", entity_type="refund", entity_id=None, after=body.model_dump())
    db.commit()
    return pick(r, "id", "status", "amount_minor")


@admin.post("/admin/refunds/{refund_id}/approve")
def approve_refund(refund_id: uuid.UUID, user=Depends(require_permission("refund.approve")), db: Session = Depends(get_db)):
    r = db.get(Refund, refund_id)
    if not r or r.status != RefundStatus.REQUESTED:
        raise HTTPException(409, "Refund is not awaiting approval")
    if r.requested_by_user_id == user.id:
        raise HTTPException(403, "A refund must be approved by a different person than the requester")
    pay = db.get(Payment, r.payment_id)
    r.approved_by_user_id = user.id
    r.gateway_refund_id = get_gateway().refund(pay, r.amount_minor)
    r.status, r.processed_at = RefundStatus.PROCESSED, utcnow()
    inv = db.get(Invoice, r.invoice_id)
    total_refunded = db.scalar(select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(Refund.payment_id == pay.id, Refund.status == RefundStatus.PROCESSED))
    if total_refunded >= pay.amount_minor:
        pay.status, inv.status = PaymentStatus.REFUNDED, InvoiceStatus.REFUNDED
    audit(db, actor=user, action="refund.approve", entity_type="refund", entity_id=r.id, after={"amount_minor": r.amount_minor})
    db.commit()
    return pick(r, "id", "status", "amount_minor", "gateway_refund_id")


@admin.get("/admin/payouts")
def list_payouts(user=Depends(require_permission("billing.manage")), db: Session = Depends(get_db)):
    return [pick(p, "id", "provider_id", "request_id", "amount_minor", "currency", "status", "paid_at", "payment_reference") for p in db.scalars(select(ProviderPayout).order_by(ProviderPayout.created_at.desc()).limit(300))]


class PayoutBody(BaseModel):
    status: PayoutStatus
    payment_reference: str | None = Field(default=None, max_length=120)


@admin.patch("/admin/payouts/{payout_id}")
def update_payout(payout_id: uuid.UUID, body: PayoutBody, user=Depends(require_permission("payout.approve")), db: Session = Depends(get_db)):
    p = db.get(ProviderPayout, payout_id)
    if not p:
        raise HTTPException(404, "Not found")
    if body.status == PayoutStatus.PAID and not body.payment_reference:
        raise HTTPException(422, "A payment reference is required to mark a payout paid")
    p.status, p.approved_by_user_id = body.status, user.id
    if body.status == PayoutStatus.PAID:
        p.paid_at, p.payment_reference = utcnow(), body.payment_reference
    audit(db, actor=user, action="payout.update", entity_type="provider_payout", entity_id=p.id, after=body.model_dump())
    db.commit()
    return pick(p, "id", "status", "amount_minor", "paid_at")


# ---------------- customer ----------------
def _own_invoice(db, customer, invoice_id) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.customer_id != customer.id or inv.status == InvoiceStatus.DRAFT:
        raise HTTPException(404, "Invoice not found")
    return inv


@portal.get("/invoices")
def my_invoices(customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    rows = db.scalars(select(Invoice).where(Invoice.customer_id == customer.id, Invoice.status != InvoiceStatus.DRAFT).order_by(Invoice.created_at.desc())).all()
    return [pick(i, *INV_FIELDS) for i in rows]


@portal.get("/invoices/{invoice_id}")
def my_invoice(invoice_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    inv = _own_invoice(db, customer, invoice_id)
    d = pick(inv, *INV_FIELDS)
    pays = db.scalars(select(Payment).where(Payment.invoice_id == inv.id)).all()
    d["payments"] = [pick(p, "id", "amount_minor", "currency", "status", "method", "created_at") for p in pays]
    d["refunds"] = [pick(r, "id", "amount_minor", "status", "reason", "processed_at") for r in db.scalars(select(Refund).where(Refund.invoice_id == inv.id))]
    return d


@portal.post("/invoices/{invoice_id}/checkout")
def checkout(invoice_id: uuid.UUID, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    inv = _own_invoice(db, customer, invoice_id)
    if inv.status != InvoiceStatus.ISSUED:
        raise HTTPException(409, "Invoice is not payable")
    ref, url = get_gateway().create_checkout(inv)
    inv.checkout_url = url
    db.commit()
    return {"checkout_url": url, "reference": ref}


# ---------------- gateway webhook (signature-verified, idempotent) ----------------
@webhooks.post("/payments")
async def payment_webhook(request: Request, x_signature: str = Header(default=""), db: Session = Depends(get_db)):
    body = await request.body()
    gw = get_gateway()
    if not gw.verify_webhook(body, x_signature):
        raise HTTPException(401, "Invalid signature")
    ev = gw.parse_event(body)
    db.add(WebhookEvent(source=gw.name, event_id=ev["event_id"]))
    try:
        db.flush()
    except IntegrityError:  # duplicate delivery: acknowledge without reprocessing
        db.rollback()
        return {"status": "duplicate"}
    inv = db.scalar(select(Invoice).where(Invoice.number == ev.get("invoice_number")))
    if not inv:
        db.commit()
        return {"status": "ignored"}
    if ev["type"] == "payment.succeeded":
        if ev.get("amount_minor") != inv.total_minor or ev.get("currency") != inv.currency:
            audit(db, action="payment.amount_mismatch", entity_type="invoice", entity_id=inv.id, after=ev)
            db.commit()
            return {"status": "amount_mismatch"}
        pay = db.scalar(select(Payment).where(Payment.gateway_payment_id == ev["payment_id"]))
        if not pay:
            pay = Payment(invoice_id=inv.id, gateway=gw.name, gateway_payment_id=ev["payment_id"], amount_minor=ev["amount_minor"], currency=ev["currency"], method=ev.get("method"))
            db.add(pay)
            db.flush()
        apply_successful_payment(db, inv, pay)
        audit(db, action="payment.succeeded", entity_type="invoice", entity_id=inv.id, after={"payment_id": ev["payment_id"]})
    elif ev["type"] == "payment.failed":
        audit(db, action="payment.failed", entity_type="invoice", entity_id=inv.id, after={"payment_id": ev.get("payment_id")})
    db.commit()
    return {"status": "ok"}
