import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin, UUIDMixin, UTCDateTime, enum_col


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class Approval(Base, UUIDMixin, TimestampMixin):
    """A versioned quote and the customer's explicit, time-stamped decision on it."""

    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("request_id", "version", name="uq_approval_request_version"),)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    scope_summary: Mapped[str] = mapped_column(Text)
    line_items: Mapped[list] = mapped_column(JSON, default=list)
    provider_cost_minor: Mapped[int] = mapped_column(Integer, default=0)  # provider/pharmacy/transport charges
    coordination_fee_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_minor: Mapped[int] = mapped_column(Integer, default=0)
    total_minor: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    exceeds_budget_cap: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_window_start: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    scheduled_window_end: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    valid_until: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    cancellation_terms: Mapped[str] = mapped_column(Text, default="")
    status = enum_col(ApprovalStatus, default=ApprovalStatus.PENDING)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approver_customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"))
    decided_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    decision_note: Mapped[str | None] = mapped_column(String(500))
