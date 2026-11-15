import datetime as dt
import uuid

from sqlalchemy import JSON, ForeignKey, String, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UUIDMixin, UTCDateTime, utcnow


class AuditLog(Base, UUIDMixin):
    """Append-only event history. Updates/deletes are blocked in the ORM here and by a
    database trigger in the PostgreSQL migration."""

    __tablename__ = "audit_logs"
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64))


@event.listens_for(AuditLog, "before_update")
def _no_update(mapper, connection, target):  # pragma: no cover - trivial
    raise RuntimeError("audit_logs rows are immutable")


@event.listens_for(AuditLog, "before_delete")
def _no_delete(mapper, connection, target):  # pragma: no cover - trivial
    raise RuntimeError("audit_logs rows are immutable")
