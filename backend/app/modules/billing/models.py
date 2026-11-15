import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin, UUIDMixin, UTCDateTime, enum_col, utcnow


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"
    REFUNDED = "refunded"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class RefundStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    PROCESSED = "processed"
    REJECTED = "rejected"


class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    ON_HOLD = "on_hold"


class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"
    number: Mapped[str] = mapped_column(String(24), unique=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("approvals.id"))
    status = enum_col(InvoiceStatus, default=InvoiceStatus.DRAFT)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    provider_cost_minor: Mapped[int] = mapped_column(Integer, default=0)
    coordination_fee_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    issued_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    due_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    paid_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    waived_reason: Mapped[str | None] = mapped_column(String(255))
    checkout_url: Mapped[str | None] = mapped_column(String(500))


class Payment(Base, UUIDMixin, TimestampMixin):
    """Gateway payment record. Never stores card numbers, security codes or credentials."""

    __tablename__ = "payments"
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    gateway: Mapped[str] = mapped_column(String(40))
    gateway_payment_id: Mapped[str] = mapped_column(String(120), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    status = enum_col(PaymentStatus, default=PaymentStatus.PENDING)
    method: Mapped[str | None] = mapped_column(String(40))
    reconciled_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)


class Refund(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refunds"
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    status = enum_col(RefundStatus, default=RefundStatus.REQUESTED)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    gateway_refund_id: Mapped[str | None] = mapped_column(String(120))
    processed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)


class WebhookEvent(Base, UUIDMixin):
    """Idempotency record for payment/messaging callbacks."""

    __tablename__ = "webhook_events"
    source: Mapped[str] = mapped_column(String(40))
    event_id: Mapped[str] = mapped_column(String(160), unique=True)
    received_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=utcnow)


class ProviderPayout(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "provider_payouts"
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id"), index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assignments.id"), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status = enum_col(PayoutStatus, default=PayoutStatus.PENDING)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    payment_reference: Mapped[str | None] = mapped_column(String(120))
