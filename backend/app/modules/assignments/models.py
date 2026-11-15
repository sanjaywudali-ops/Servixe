import datetime as dt
import enum
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, UUIDMixin, UTCDateTime, enum_col


class AssignmentRole(str, enum.Enum):
    PRIMARY = "primary"
    BACKUP = "backup"


class AssignmentStatus(str, enum.Enum):
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"


class Assignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assignments"
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id"), index=True)
    role = enum_col(AssignmentRole, default=AssignmentRole.PRIMARY)
    status = enum_col(AssignmentStatus, default=AssignmentStatus.OFFERED)
    instructions: Mapped[str | None] = mapped_column(Text)  # minimum necessary, approved task instructions
    window_start: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    window_end: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    provider_payout_minor: Mapped[int] = mapped_column(default=0)
    offered_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    accepted_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    rejected_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    reject_reason: Mapped[str | None] = mapped_column(String(500))
    checked_in_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    checked_out_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    check_in_note: Mapped[str | None] = mapped_column(String(500))
    check_out_note: Mapped[str | None] = mapped_column(String(500))
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    provider = relationship("Provider", lazy="joined")
    request = relationship("ServiceRequest", lazy="joined")
