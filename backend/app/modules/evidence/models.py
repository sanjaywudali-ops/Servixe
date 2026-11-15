import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin, UTCDateTime, enum_col


class EvidencePurpose(str, enum.Enum):
    COMPLETION_PHOTO = "completion_photo"
    RECEIPT = "receipt"
    DOCUMENT = "document"
    OTHER = "other"


class AccessScope(str, enum.Enum):
    OPS_ONLY = "ops_only"
    CUSTOMER_VISIBLE = "customer_visible"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    SKIPPED = "skipped"


class ChecklistTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "checklist_templates"
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    items: Mapped[list] = mapped_column(JSON, default=list)  # [{key,label,required}]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ChecklistResponse(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "checklist_responses"
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignments.id"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("checklist_templates.id"))
    template_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    responses: Mapped[dict] = mapped_column(JSON, default=dict)  # {key: {done: bool, note: str}}
    completed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class Evidence(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Metadata for a privately stored job file. The database never holds a public URL."""

    __tablename__ = "evidence"
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_requests.id"), index=True)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assignments.id"))
    uploader_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    purpose = enum_col(EvidencePurpose, default=EvidencePurpose.COMPLETION_PHOTO)
    access_scope = enum_col(AccessScope, default=AccessScope.OPS_ONLY)
    scan_status = enum_col(ScanStatus, default=ScanStatus.SKIPPED)
    caption: Mapped[str | None] = mapped_column(String(300))
    retain_until: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
