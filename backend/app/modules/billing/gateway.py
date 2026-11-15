"""Payment gateway adapter. Hosted/tokenised checkout only: card data never touches Servixe.
Implement a real adapter (Razorpay, Stripe, ...) after the India/overseas payment review."""
import json

from app.core.config import settings
from app.core.security import verify_signature


class StubGateway:
    name = "stub"

    def create_checkout(self, invoice) -> tuple[str, str]:
        ref = f"stub_{invoice.number}"
        return ref, f"{settings.frontend_url.rstrip('/')}/portal/invoices/{invoice.id}?checkout={ref}"

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        return verify_signature(settings.payment_webhook_secret, body, signature)

    def parse_event(self, body: bytes) -> dict:
        """Normalised: {event_id, type: payment.succeeded|payment.failed|refund.processed,
        payment_id, invoice_number, amount_minor, currency, refund_id?}"""
        return json.loads(body)

    def refund(self, payment, amount_minor: int) -> str:
        return f"stub_refund_{payment.gateway_payment_id}"


def get_gateway():
    return StubGateway()
