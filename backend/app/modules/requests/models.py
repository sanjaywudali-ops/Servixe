import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin, UTCDateTime, enum_col, utcnow


class RequestStatus(str, enum.Enum):
    NEW_REQUEST = "new_request"
    UNDER_REVIEW = "under_review"
    QUOTE_PENDING = "quote_pending"
    APPROVAL_PENDING = "approval_pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    QUALITY_CHECK = "quality_check"
    COMPLETED = "completed"
    CLOSED = "closed"
    # exception states
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"
    FAILED = "failed"
    REFUND_PENDING = "refund_pending"
    INCIDENT_OPEN = "incident_open"


class Priority(str, enum.Enum):
    NORMAL = "normal"
    URGENT = "urgent"


class Source(str, enum.Enum):
    PORTAL = "portal"
    ASSISTED = "assisted"  # created by staff on behalf of a customer (phone/WhatsApp)


class QualityOutcome(str, enum.Enum):
    PASS = "pass"
    PASS_WITH_NOTES = "pass_with_notes"
    FAIL = "fail"


class Counter(Base):
    __tablename__ = "counters"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class ServiceRequest(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_requests"
    reference: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)  # payer
    requestor_customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"))  # authorised requestor
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), index=True)  # service recipient
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"))
    service_area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_areas.id"))
    status = enum_col(RequestStatus, default=RequestStatus.NEW_REQUEST, index=True)
    status_before_incident: Mapped[str | None] = mapped_column(String(40))
    priority = enum_col(Priority, default=Priority.NORMAL)
    source = enum_col(Source, default=Source.PORTAL)
    task_details: Mapped[str] = mapped_column(Text)
    location_text: Mapped[str | None] = mapped_column(String(500))
    requested_start: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    requested_end: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    budget_cap_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    consent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consents.id"))
    consent_scope: Mapped[str | None] = mapped_column(String(40))
    approval_exception_reason: Mapped[str | None] = mapped_column(String(500))
    approval_exception_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    quality_outcome = enum_col(QualityOutcome, nullable=True)
    quality_notes: Mapped[str | None] = mapped_column(Text)
    quality_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    cancel_reason: Mapped[str | None] = mapped_column(String(500))
    internal_notes: Mapped[str | None] = mapped_column(Text)

    service = relationship("Service", lazy="joined")
    parent = relationship("Parent", lazy="joined")
    events: Mapped[list["RequestEvent"]] = relationship(
        back_populates="request", order_by="RequestEvent.created_at", lazy="select"
    )


class RequestEvent(Base, UUIDMixin):
    """Timeline of status changes and customer-visible updates (single source of truth)."""

    __tablename__ = "request_events"
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(40))  # status_change | note | update | quote | assignment ...
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str | None] = mapped_column(Text)
    visible_to_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    request: Mapped[ServiceRequest] = relationship(back_populates="events")
