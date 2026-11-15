import datetime as dt

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import (client_ip, create_session, current_user, current_user_any, get_session, revoke_all_sessions)
from app.core.permissions import STAFF_ROLES
from app.core.ratelimit import limiter
from app.core.security import (hash_password, hash_token, needs_rehash, new_token, validate_password_strength, verify_password)
from app.db import get_db, utcnow
from app.modules.audit.service import audit
from app.modules.families.models import Customer
from app.modules.identity.models import AuthToken, Role, User, UserSession
from app.modules.notifications.service import link, notify

router = APIRouter(prefix="/auth", tags=["auth"])

# A pre-computed hash so login timing doesn't reveal whether an email exists.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def user_out(u: User, s: UserSession | None = None) -> dict:
    d = {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role_name, "mfa_enabled": u.mfa_enabled,
         "email_verified": bool(u.email_verified_at)}
    if s is not None:
        d["mfa_verified"] = s.mfa_verified
        d["mfa_required"] = u.role_name in STAFF_ROLES and not s.mfa_verified
    return d


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(min_length=2, max_length=160)
    country: str = Field(min_length=2, max_length=80)
    phone: str | None = Field(default=None, max_length=32)
    whatsapp_opt_in: bool = False


@router.post("/register", status_code=201, dependencies=[Depends(limiter("register", 10, 3600))])
def register(body: RegisterBody, request: Request, response: Response, db: Session = Depends(get_db)):
    err = validate_password_strength(body.password)
    if err:
        raise HTTPException(422, err)
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    role = db.scalar(select(Role).where(Role.name == "customer"))
    u = User(email=email, phone=body.phone, full_name=body.full_name, password_hash=hash_password(body.password), role_id=role.id)
    db.add(u)
    db.flush()
    db.refresh(u)
    now = utcnow()
    db.add(Customer(user_id=u.id, full_name=body.full_name, country=body.country, phone=body.phone,
                    whatsapp_opt_in=body.whatsapp_opt_in, whatsapp_opt_in_at=now if body.whatsapp_opt_in else None))
    token = new_token()
    db.add(AuthToken(user_id=u.id, purpose="email_verify", token_hash=hash_token(token), expires_at=now + dt.timedelta(days=2)))
    audit(db, actor=u, action="user.register", entity_type="user", entity_id=u.id, ip=client_ip(request))
    s = create_session(db, u, request, response)
    db.commit()
    notify(db, template_key="account_verify", user=u, context={"link": link(f"/verify-email?token={token}")})
    return user_out(u, s)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


@router.post("/login", dependencies=[Depends(limiter("login", 20, 300))])
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower(), User.deleted_at.is_(None)))
    now = utcnow()
    generic = HTTPException(401, "Incorrect email or password")
    if not u:
        verify_password(body.password, _DUMMY_HASH)
        raise generic
    if u.locked_until and u.locked_until > now:
        raise HTTPException(423, "Account temporarily locked after repeated failed attempts. Try again later.")
    if not verify_password(body.password, u.password_hash) or not u.is_active:
        u.failed_logins += 1
        if u.failed_logins >= settings.max_failed_logins:
            u.locked_until = now + dt.timedelta(minutes=settings.lockout_minutes)
            u.failed_logins = 0
            audit(db, actor=u, action="user.locked", entity_type="user", entity_id=u.id, ip=client_ip(request))
        db.commit()
        raise generic
    if settings.require_email_verification and not u.email_verified_at and u.role_name == "customer":
        raise HTTPException(403, "Please verify your email address first")
    if needs_rehash(u.password_hash):
        u.password_hash = hash_password(body.password)
    u.failed_logins, u.locked_until, u.last_login_at = 0, None, now
    s = create_session(db, u, request, response)
    audit(db, actor=u, action="user.login", entity_type="user", entity_id=u.id, ip=client_ip(request))
    db.commit()
    return user_out(u, s)


@router.post("/logout")
def logout(response: Response, s: UserSession = Depends(get_session), db: Session = Depends(get_db)):
    s.revoked_at = utcnow()
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}


@router.get("/me")
def me(s: UserSession = Depends(get_session)):
    return user_out(s.user, s)


# ---- MFA (TOTP): mandatory for staff ----
@router.post("/mfa/setup")
def mfa_setup(s: UserSession = Depends(get_session), db: Session = Depends(get_db)):
    u = s.user
    if u.mfa_enabled:
        raise HTTPException(409, "MFA is already enabled")
    u.mfa_secret = pyotp.random_base32()
    db.commit()
    return {"secret": u.mfa_secret, "otpauth_uri": pyotp.TOTP(u.mfa_secret).provisioning_uri(name=u.email, issuer_name="Servixe")}


class CodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=8)


@router.post("/mfa/verify", dependencies=[Depends(limiter("mfa", 10, 300))])
def mfa_verify(body: CodeBody, request: Request, s: UserSession = Depends(get_session), db: Session = Depends(get_db)):
    u = s.user
    if not u.mfa_secret:
        raise HTTPException(409, "Start MFA setup first")
    if not pyotp.TOTP(u.mfa_secret).verify(body.code.strip(), valid_window=1):
        audit(db, actor=u, action="mfa.failed", entity_type="user", entity_id=u.id, ip=client_ip(request))
        db.commit()
        raise HTTPException(401, "Invalid code")
    if not u.mfa_enabled:
        u.mfa_enabled = True
        audit(db, actor=u, action="mfa.enabled", entity_type="user", entity_id=u.id)
    s.mfa_verified = True
    db.commit()
    return user_out(u, s)


# ---- password management ----
class ForgotBody(BaseModel):
    email: EmailStr


@router.post("/password/forgot", dependencies=[Depends(limiter("forgot", 5, 900))])
def forgot(body: ForgotBody, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower(), User.is_active.is_(True)))
    if u:
        token = new_token()
        db.add(AuthToken(user_id=u.id, purpose="password_reset", token_hash=hash_token(token), expires_at=utcnow() + dt.timedelta(hours=1)))
        db.commit()
        notify(db, template_key="password_reset", user=u, context={"link": link(f"/reset-password?token={token}")})
    return {"ok": True}  # same response whether or not the account exists


class ResetBody(BaseModel):
    token: str
    password: str


@router.post("/password/reset", dependencies=[Depends(limiter("reset", 10, 900))])
def reset(body: ResetBody, db: Session = Depends(get_db)):
    err = validate_password_strength(body.password)
    if err:
        raise HTTPException(422, err)
    t = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(body.token), AuthToken.purpose.in_(["password_reset", "invite"])))
    if not t or t.used_at or t.expires_at < utcnow():
        raise HTTPException(400, "This link is invalid or has expired")
    u = db.get(User, t.user_id)
    u.password_hash = hash_password(body.password)
    u.failed_logins, u.locked_until = 0, None
    if not u.email_verified_at:
        u.email_verified_at = utcnow()
    t.used_at = utcnow()
    revoke_all_sessions(db, u.id)
    audit(db, actor=u, action="user.password_reset", entity_type="user", entity_id=u.id)
    db.commit()
    return {"ok": True}


class ChangePwBody(BaseModel):
    current_password: str
    new_password: str


@router.post("/password/change")
def change_password(body: ChangePwBody, s: UserSession = Depends(get_session), db: Session = Depends(get_db)):
    u = s.user
    if not verify_password(body.current_password, u.password_hash):
        raise HTTPException(401, "Current password is incorrect")
    err = validate_password_strength(body.new_password)
    if err:
        raise HTTPException(422, err)
    u.password_hash = hash_password(body.new_password)
    revoke_all_sessions(db, u.id, except_id=s.id)  # session revocation on security events
    audit(db, actor=u, action="user.password_change", entity_type="user", entity_id=u.id)
    db.commit()
    return {"ok": True}


class VerifyBody(BaseModel):
    token: str


@router.post("/verify-email")
def verify_email(body: VerifyBody, db: Session = Depends(get_db)):
    t = db.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(body.token), AuthToken.purpose == "email_verify"))
    if not t or t.used_at or t.expires_at < utcnow():
        raise HTTPException(400, "This link is invalid or has expired")
    db.get(User, t.user_id).email_verified_at = utcnow()
    t.used_at = utcnow()
    db.commit()
    return {"ok": True}


# ---- session management ----
@router.get("/sessions")
def sessions(s: UserSession = Depends(get_session), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserSession).where(UserSession.user_id == s.user_id, UserSession.revoked_at.is_(None), UserSession.expires_at > utcnow()).order_by(UserSession.last_seen_at.desc())).all()
    return [{"id": r.id, "created_at": r.created_at, "last_seen_at": r.last_seen_at, "ip": r.ip, "user_agent": r.user_agent, "current": r.id == s.id} for r in rows]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, s: UserSession = Depends(get_session), db: Session = Depends(get_db)):
    import uuid

    row = db.get(UserSession, uuid.UUID(session_id))
    if not row or row.user_id != s.user_id:
        raise HTTPException(404, "Not found")
    row.revoked_at = utcnow()
    db.commit()
    return {"ok": True}
