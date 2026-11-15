import enum
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


SENSITIVE_KEYS = {"password", "password_hash", "mfa_secret", "token", "token_hash"}


def _redact(d: dict | None) -> dict | None:
    if d is None:
        return None
    return {k: ("***" if k in SENSITIVE_KEYS else v) for k, v in _clean(d).items()}


def audit(
    db: Session,
    *,
    actor=None,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    before: dict | None = None,
    after: dict | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Record an audit event inside the caller's transaction (commits with the business change)."""
    row = AuditLog(
        actor_user_id=getattr(actor, "id", None),
        actor_role=getattr(actor, "role_name", None) if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=_redact(before),
        after=_redact(after),
        ip=ip,
    )
    db.add(row)
    return row
