import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin, UTCDateTime, enum_col


class ConsentScope(str, enum.Enum):
    HOME_VISIT = "home_visit"
    ERRANDS = "errands"
    PHOTOGRAPHS = "photographs"
    UPDATES = "updates"
    INFORMATION_SHARING = "information_sharing"


class CaptureMethod(str, enum.Enum):
    IN_PERSON = "in_person"
    PHONE_CALL = "phone_call"
    SIGNED_FORM = "signed_form"
    VIDEO_CALL = "video_call"
    OTHER = "other"


class AuthStatus(str, enum.Enum):
    PENDING = "pending"  # requested by customer; awaiting parent's informed agreement
    ACTIVE = "active"
    REVOKED = "revoked"


class Customer(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Overseas payer/customer account. Deliberately separate from the parent record."""

    __tablename__ = "customers"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    full_name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(32))
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_opt_in_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    preferred_currency: Mapped[str] = mapped_column(String(3), default="INR")
    user = relationship("User", lazy="joined")


class Parent(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Service recipient (parent). Never merged with the customer or authorised requestor."""

    __tablename__ = "parents"
    created_by_customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(32))
    preferred_language: Mapped[str | None] = mapped_column(String(40))
    contact_preferences: Mapped[str | None] = mapped_column(String(255))
    address_line: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(80), default="Nellore")
    area: Mapped[str | None] = mapped_column(String(120))
    service_area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_areas.id"))
    location_notes: Mapped[str | None] = mapped_column(String(500))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(160))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32))
    authorisations: Mapped[list["FamilyAuthorisation"]] = relationship(back_populates="parent", lazy="selectin")


class Consent(Base, UUIDMixin, TimestampMixin):
    """Dated, scoped consent record. Never edited in place: revoke and create a new one."""

    __tablename__ = "consents"
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), index=True)
    scopes: Mapped[list] = mapped_column(JSON)  # list[ConsentScope values]
    given_by: Mapped[str] = mapped_column(String(160))  # who gave it (normally the parent)
    captured_via = enum_col(CaptureMethod)
    captured_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    captured_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    valid_from: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    valid_until: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    evidence_ref: Mapped[str | None] = mapped_column(String(255))  # form number / call reference
    notes: Mapped[str | None] = mapped_column(Text)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    revoked_reason: Mapped[str | None] = mapped_column(String(255))

    def covers(self, scope: str, at: dt.datetime) -> bool:
        if self.revoked_at is not None or scope not in self.scopes:
            return False
        if self.valid_from > at:
            return False
        return self.valid_until is None or self.valid_until >= at


class FamilyAuthorisation(Base, UUIDMixin, TimestampMixin):
    """Links a customer/requestor to a parent and defines exactly what they may do."""

    __tablename__ = "family_authorisations"
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    relationship_to_parent: Mapped[str] = mapped_column(String(60))  # son, daughter, ...
    can_request_services: Mapped[bool] = mapped_column(Boolean, default=True)
    can_receive_updates: Mapped[bool] = mapped_column(Boolean, default=True)
    can_approve_costs: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    status = enum_col(AuthStatus, default=AuthStatus.PENDING)
    valid_from: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    valid_until: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    consent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consents.id"))
    activated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    revoked_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    parent: Mapped[Parent] = relationship(back_populates="authorisations")

    def is_active(self, at: dt.datetime) -> bool:
        if self.status != AuthStatus.ACTIVE:
            return False
        if self.valid_from and self.valid_from > at:
            return False
        return self.valid_until is None or self.valid_until >= at
