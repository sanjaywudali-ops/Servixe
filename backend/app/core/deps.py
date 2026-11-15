import datetime as dt
import uuid

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import STAFF_ROLES
from app.core.security import hash_token, new_token
from app.db import get_db, utcnow
from app.modules.identity.models import User, UserSession


def client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def create_session(db: Session, user: User, request: Request, response: Response) -> UserSession:
    token = new_token()
    now = utcnow()
    staff = user.role_name in STAFF_ROLES
    ttl = settings.session_ttl_hours_staff if staff else settings.session_ttl_hours_default
    row = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + dt.timedelta(hours=ttl),
        mfa_verified=False,
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(row)
    db.flush()
    response.set_cookie(
        settings.session_cookie_name, token, max_age=ttl * 3600, httponly=True,
        secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/",
    )
    return row


def revoke_all_sessions(db: Session, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    now = utcnow()
    for s in db.scalars(select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))):
        if except_id is None or s.id != except_id:
            s.revoked_at = now


def get_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(401, "Not authenticated")
    s = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    now = utcnow()
    if not s or s.revoked_at or s.expires_at < now or not s.user.is_active or s.user.deleted_at:
        raise HTTPException(401, "Session expired")
    staff = s.user.role_name in STAFF_ROLES
    idle = settings.session_idle_minutes_staff if staff else settings.session_idle_minutes_default
    if now - s.last_seen_at > dt.timedelta(minutes=idle):
        s.revoked_at = now
        db.commit()
        raise HTTPException(401, "Session expired due to inactivity")
    if now - s.last_seen_at > dt.timedelta(minutes=1):
        s.last_seen_at = now
        db.commit()
    request.state.session = s
    return s


def current_user_any(s: UserSession = Depends(get_session)) -> User:
    """Authenticated user, even if a staff session has not yet passed MFA (auth endpoints only)."""
    return s.user


def current_user(s: UserSession = Depends(get_session)) -> User:
    """Fully authenticated user. Staff sessions must have completed MFA."""
    if s.user.role_name in STAFF_ROLES and not s.mfa_verified:
        raise HTTPException(403, "MFA verification required")
    return s.user


def require_permission(*perms: str):
    def dep(user: User = Depends(current_user)) -> User:
        have = user.permissions
        if not all(p in have for p in perms):
            raise HTTPException(403, "You do not have permission to perform this action")
        return user

    return dep


def require_customer(user: User = Depends(require_permission("portal.customer")), db: Session = Depends(get_db)):
    from app.modules.families.models import Customer

    c = db.scalar(select(Customer).where(Customer.user_id == user.id, Customer.deleted_at.is_(None)))
    if not c:
        raise HTTPException(403, "No customer profile for this account")
    return c


def require_provider(user: User = Depends(require_permission("portal.provider")), db: Session = Depends(get_db)):
    from app.modules.providers.models import Provider

    p = db.scalar(select(Provider).where(Provider.user_id == user.id, Provider.deleted_at.is_(None)))
    if not p:
        raise HTTPException(403, "No provider profile for this account")
    return p
