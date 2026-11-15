import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin, UUIDMixin, UTCDateTime, enum_col


class Channel(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class NotificationStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Notification(Base, UUIDMixin, TimestampMixin):
    """Delivery log: an accepted API call is not treated as a delivered message."""

    __tablename__ = "notifications"
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_requests.id"), index=True)
    channel = enum_col(Channel)
    recipient: Mapped[str] = mapped_column(String(255))
    template_key: Mapped[str] = mapped_column(String(60))
    context: Mapped[dict] = mapped_column(JSON, default=dict)  # non-sensitive values only
    status = enum_col(NotificationStatus, default=NotificationStatus.QUEUED, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
    provider_message_id: Mapped[str | None] = mapped_column(String(160), index=True)
    next_retry_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    sent_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    dedupe_key: Mapped[str | None] = mapped_column(String(160), unique=True)
