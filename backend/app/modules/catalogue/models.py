import enum
import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin, UUIDMixin, enum_col


class ServiceArea(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "service_areas"
    name: Mapped[str] = mapped_column(String(120), unique=True)
    district: Mapped[str] = mapped_column(String(80), default="Nellore")
    state: Mapped[str] = mapped_column(String(80), default="Andhra Pradesh")
    pincodes: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Service(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "services"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    inclusions: Mapped[list] = mapped_column(JSON, default=list)
    exclusions: Mapped[list] = mapped_column(JSON, default=list)
    requirements: Mapped[str] = mapped_column(Text, default="")
    # Which parent-consent scope must be active before this service can proceed.
    required_consent_scope: Mapped[str] = mapped_column(String(40), default="home_visit")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)


class PricingRule(Base, UUIDMixin, TimestampMixin):
    """Coordination-fee rule. Area-specific rule wins over the service-wide rule."""

    __tablename__ = "pricing_rules"
    __table_args__ = (UniqueConstraint("service_id", "service_area_id", name="uq_pricing_service_area"),)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("services.id"), index=True)
    service_area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_areas.id"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    coordination_fee_minor: Mapped[int] = mapped_column(Integer)
    urgent_surcharge_minor: Mapped[int] = mapped_column(Integer, default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=18)
    indicative_min_minor: Mapped[int | None] = mapped_column(Integer)
    indicative_max_minor: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PackageInterval(str, enum.Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class Package(Base, UUIDMixin, TimestampMixin):
    """Optional recurring plan. Complex subscription billing is deferred until validated."""

    __tablename__ = "packages"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    interval = enum_col(PackageInterval, default=PackageInterval.MONTHLY)
    indicative_price_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    entitlements: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
