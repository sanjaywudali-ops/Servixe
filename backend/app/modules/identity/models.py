import datetime as dt
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin, UTCDateTime


class Permission(Base):
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class Role(Base, UUIDMixin):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[list["RolePermission"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(ForeignKey("permissions.code"), primary_key=True)


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    full_name: Mapped[str] = mapped_column(String(160), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    role: Mapped[Role] = relationship(lazy="joined")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    last_login_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)

    @property
    def role_name(self) -> str:
        return self.role.name

    @property
    def permissions(self) -> set[str]:
        return {rp.permission_code for rp in self.role.permissions}


class UserSession(Base, UUIDMixin):
    __tablename__ = "user_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
    mfa_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    user: Mapped[User] = relationship(lazy="joined")


class AuthToken(Base, UUIDMixin):
    """One-time tokens: password reset and email verification."""

    __tablename__ = "auth_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))  # password_reset | email_verify | invite
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[dt.datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[dt.datetime | None] = mapped_column(UTCDateTime)
