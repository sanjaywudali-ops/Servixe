import datetime as dt
import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Table, Column, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin, UTCDateTime, enum_col


class ProviderStatus(str, enum.Enum):
    APPLICANT = "applicant"
    IN_VERIFICATION = "in_verification"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class DocType(str, enum.Enum):
    IDENTITY = "identity"
    ADDRESS = "address"
    REFERENCE = "reference"
    LICENCE = "licence"
    INSURANCE = "insurance"
    POLICE_VERIFICATION = "police_verification"
    OTHER = "other"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


provider_services = Table(
    "provider_services", Base.metadata,
    Column("provider_id", Uuid, ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", Uuid, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)
provider_areas = Table(
    "provider_areas", Base.metadata,
    Column("provider_id", Uuid, ForeignKey("providers.id", ondelete="CASCADE"), primary_key=True),
    Column("service_area_id", Uuid, ForeignKey("service_areas.id", ondelete="CASCADE"), primary_key=True),
)

REQUIRED_DOC_TYPES = {DocType.IDENTITY, DocType.ADDRESS, DocType.REFERENCE}


class Provider(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "providers"
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    provider_type: Mapped[str] = mapped_column(String(60), default="individual")  # individual|pharmacy|transport|clinic
    status = enum_col(ProviderStatus, default=ProviderStatus.APPLICANT)
    capacity_per_week: Mapped[int] = mapped_column(Integer, default=10)
    can_be_backup: Mapped[bool] = mapped_column(Boolean, default=True)
    interview_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    induction_completed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    trial_job_completed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    verified_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    user = relationship("User", lazy="joined")
    services = relationship("Service", secondary=provider_services, lazy="selectin")
    areas = relationship("ServiceArea", secondary=provider_areas, lazy="selectin")
    documents: Mapped[list["ProviderDocument"]] = relationship(back_populates="provider", lazy="selectin")


class ProviderDocument(Base, UUIDMixin, TimestampMixin):
    """Verification documents. Files live in private object storage; only metadata here."""

    __tablename__ = "provider_documents"
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id"), index=True)
    doc_type = enum_col(DocType)
    storage_key: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer)
    reference_last4: Mapped[str | None] = mapped_column(String(8))  # never store full ID numbers
    issued_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    expires_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    review_status = enum_col(ReviewStatus, default=ReviewStatus.PENDING)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    review_notes: Mapped[str | None] = mapped_column(String(500))
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[Provider] = relationship(back_populates="documents")
