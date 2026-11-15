from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.modules.approvals.models import Approval, ApprovalStatus
from app.modules.assignments.models import Assignment, AssignmentRole, AssignmentStatus
from app.modules.billing.models import Invoice, InvoiceStatus, Payment, PaymentStatus, ProviderPayout
from app.modules.families.service import next_reference
from app.modules.requests.models import ServiceRequest


def create_invoice_from_approval(db: Session, req: ServiceRequest) -> Invoice:
    a = db.scalar(select(Approval).where(Approval.request_id == req.id, Approval.status == ApprovalStatus.APPROVED).order_by(Approval.version.desc()))
    if not a:
        raise HTTPException(409, "No approved quote to invoice")
    if db.scalar(select(Invoice).where(Invoice.request_id == req.id, Invoice.status != InvoiceStatus.VOID)):
        raise HTTPException(409, "An invoice already exists for this request")
    inv = Invoice(
        number=next_reference(db, "invoice", "INV"), request_id=req.id, customer_id=req.customer_id, approval_id=a.id,
        line_items=a.line_items or [
            {"label": "Provider / third-party charges", "amount_minor": a.provider_cost_minor},
            {"label": "Servixe coordination fee", "amount_minor": a.coordination_fee_minor},
            {"label": "Tax", "amount_minor": a.tax_minor},
        ],
        provider_cost_minor=a.provider_cost_minor, coordination_fee_minor=a.coordination_fee_minor,
        tax_minor=a.tax_minor, total_minor=a.total_minor, currency=a.currency, status=InvoiceStatus.DRAFT,
    )
    db.add(inv)
    db.flush()
    return inv


def apply_successful_payment(db: Session, inv: Invoice, payment: Payment) -> None:
    payment.status = PaymentStatus.SUCCEEDED
    payment.reconciled_at = utcnow()
    db.flush()
    paid = sum(p.amount_minor for p in db.scalars(select(Payment).where(Payment.invoice_id == inv.id, Payment.status == PaymentStatus.SUCCEEDED)))
    if paid >= inv.total_minor and inv.status == InvoiceStatus.ISSUED:
        inv.status = InvoiceStatus.PAID
        inv.paid_at = utcnow()


def create_payout_for_request(db: Session, req: ServiceRequest) -> ProviderPayout | None:
    a = db.scalar(select(Assignment).where(Assignment.request_id == req.id, Assignment.status == AssignmentStatus.ACCEPTED, Assignment.role == AssignmentRole.PRIMARY))
    if not a:
        return None
    a.status = AssignmentStatus.COMPLETED
    if db.scalar(select(ProviderPayout).where(ProviderPayout.assignment_id == a.id)):
        return None
    p = ProviderPayout(provider_id=a.provider_id, request_id=req.id, assignment_id=a.id, amount_minor=a.provider_payout_minor, currency=req.currency)
    db.add(p)
    return p
