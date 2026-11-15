import pytest

from app.modules.approvals.service import compute_quote
from app.modules.catalogue.models import PricingRule
from app.modules.requests.workflow import TRANSITIONS, TERMINAL
from app.modules.requests.models import RequestStatus as S


def rule(fee=50000, urgent=20000, tax=18):
    return PricingRule(coordination_fee_minor=fee, urgent_surcharge_minor=urgent, tax_percent=tax, currency="INR")


def test_quote_math():
    q = compute_quote(rule(), 100000, False)
    assert (q["coordination_fee_minor"], q["tax_minor"], q["total_minor"]) == (50000, 9000, 159000)
    q = compute_quote(rule(), 0, True)
    assert q["coordination_fee_minor"] == 70000 and q["tax_minor"] == 12600
    with pytest.raises(ValueError):
        compute_quote(rule(), -1, False)


def test_tax_rounding_half_up():
    assert compute_quote(rule(fee=1, urgent=0, tax=50), 0, False)["tax_minor"] == 1  # 0.5 -> 1


def test_terminal_states_have_no_exits():
    for s in TERMINAL:
        assert TRANSITIONS[s] == set()


def test_cannot_skip_to_completed():
    for s in (S.NEW_REQUEST, S.UNDER_REVIEW, S.APPROVAL_PENDING, S.ASSIGNED, S.IN_PROGRESS):
        assert S.COMPLETED not in TRANSITIONS[s]
