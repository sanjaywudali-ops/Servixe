import enum
import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin, UUIDMixin, enum_col


class ContactMethod(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"


class EnquiryStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    CLOSED = "closed"


class Enquiry(Base, UUIDMixin, TimestampMixin):
    """Lead stage: basic details only. No health records or sensitive medical details."""

    __tablename__ = "enquiries"
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80))
    contact_method = enum_col(ContactMethod)
    contact_value: Mapped[str] = mapped_column(String(255))
    parent_city_area: Mapped[str] = mapped_column(String(160))
    service_interest: Mapped[str] = mapped_column(String(120))
    callback_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_to_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    status = enum_col(EnquiryStatus, default=EnquiryStatus.NEW)
    handled_by: Mapped[str | None] = mapped_column(String(160))
