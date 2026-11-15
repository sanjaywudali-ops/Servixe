from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalogue.models import PricingRule


def find_rule(db: Session, service_id, area_id) -> PricingRule | None:
    q = select(PricingRule).where(PricingRule.service_id == service_id, PricingRule.is_active.is_(True))
    rules = db.scalars(q).all()
    if area_id:
        for r in rules:
            if r.service_area_id == area_id:
                return r
    for r in rules:
        if r.service_area_id is None:
            return r
    return None


def compute_quote(rule: PricingRule, provider_cost_minor: int, urgent: bool) -> dict:
    """Totals in minor units. Tax applies to Servixe's coordination fee; provider/third-party charges
    are passed through at cost (adjust to your tax advice)."""
    if provider_cost_minor < 0:
        raise ValueError("provider cost cannot be negative")
    fee = rule.coordination_fee_minor + (rule.urgent_surcharge_minor if urgent else 0)
    tax = int((Decimal(fee) * Decimal(rule.tax_percent) / Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {
        "provider_cost_minor": provider_cost_minor, "coordination_fee_minor": fee, "tax_minor": tax,
        "total_minor": provider_cost_minor + fee + tax, "currency": rule.currency,
    }
