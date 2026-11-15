import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin, UUIDMixin, UTCDateTime, enum_col, utcnow


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategory(str, enum.Enum):
    SAFETY = "safety"
    COMPLAINT = "complaint"
    MISSED_VISIT = "missed_visit"
    PROVIDER_MISCONDUCT = "provider_misconduct"
    OTHER = "other"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Incident(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "incidents"
    reference: Mapped[str] = mapped_column(String(24), unique=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_requests.id"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("parents.id"))
    category = enum_col(IncidentCategory, default=IncidentCategory.OTHER)
    severity = enum_col(Severity, default=Severity.MEDIUM)
    status = enum_col(IncidentStatus, default=IncidentStatus.OPEN)
    description: Mapped[str] = mapped_column(Text)
    event_time: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=utcnow)
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reporter_role: Mapped[str] = mapped_column(String(32))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    escalation_contacts: Mapped[list] = mapped_column(JSON, default=list)
    actions_taken: Mapped[str | None] = mapped_column(Text)
    customer_communication: Mapped[str | None] = mapped_column(Text)
    closure_review: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)


class IncidentNote(Base, UUIDMixin):
    __tablename__ = "incident_notes"
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"), index=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=utcnow)
