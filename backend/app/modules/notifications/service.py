"""Notifications: templates -> delivery log -> channel senders, retried by Celery.

Keep templates free of sensitive parent details. Use the request reference and a portal link."""
import datetime as dt
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import utcnow
from app.modules.notifications.models import Channel, Notification, NotificationStatus

log = logging.getLogger("servixe.notifications")
MAX_ATTEMPTS = 5

TEMPLATES: dict[str, dict[str, str]] = {
    "account_verify": {"subject": "Verify your Servixe email", "body": "Welcome to Servixe. Verify your email: {link}"},
    "password_reset": {"subject": "Reset your Servixe password", "body": "Reset your password (valid 1 hour): {link}"},
    "provider_invite": {"subject": "You're invited to Servixe", "body": "Set your password to access your provider portal: {link}"},
    "request_received": {"subject": "We received your request {reference}", "body": "Request {reference} was received. Track it at {link}"},
    "quote_ready": {"subject": "Quote ready for {reference}", "body": "A quote is ready for request {reference}. Review and approve at {link}"},
    "request_update": {"subject": "Update on {reference}", "body": "There is a new update on request {reference}: {link}"},
    "job_offered": {"subject": "New job offer {reference}", "body": "You have a new job offer ({reference}). Open your portal: {link}"},
    "job_reminder": {"subject": "Reminder: job {reference}", "body": "Reminder: job {reference} is scheduled soon. Details: {link}"},
    "request_completed": {"subject": "Request {reference} completed", "body": "Request {reference} has been completed. See the summary: {link}"},
    "invoice_issued": {"subject": "Invoice {number}", "body": "Invoice {number} is ready. View and pay: {link}"},
    "incident_alert": {"subject": "Incident {reference} ({severity})", "body": "Incident {reference} requires attention: {link}"},
    "doc_expiring": {"subject": "Provider document expiring", "body": "A provider document expires on {date}: {link}"},
}


def render(template_key: str, context: dict) -> tuple[str, str]:
    t = TEMPLATES[template_key]
    ctx = {k: str(v) for k, v in context.items()}
    return t["subject"].format_map(_Safe(ctx)), t["body"].format_map(_Safe(ctx))


class _Safe(dict):
    def __missing__(self, key):
        return ""


def queue_notification(
    db: Session, *, template_key: str, context: dict, user=None, email: str | None = None,
    phone: str | None = None, prefer_whatsapp: bool = False, request_id=None, dedupe_key: str | None = None,
) -> Notification | None:
    """Create a delivery-log row. WhatsApp is used only with opt-in; otherwise falls back to email."""
    if dedupe_key and db.scalar(select(Notification).where(Notification.dedupe_key == dedupe_key)):
        return None
    channel, recipient = None, None
    if prefer_whatsapp and phone:
        channel, recipient = Channel.WHATSAPP, phone
    elif email or (user is not None and user.email):
        channel, recipient = Channel.EMAIL, email or user.email
    if not channel:
        return None
    n = Notification(
        user_id=getattr(user, "id", None), request_id=request_id, channel=channel, recipient=recipient,
        template_key=template_key, context=context, status=NotificationStatus.QUEUED, dedupe_key=dedupe_key,
    )
    db.add(n)
    db.flush()
    return n


def link(path: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{path}"


# --- channel senders (adapters) ---------------------------------------------------------------
def _send_email(to: str, subject: str, body: str) -> str:
    if settings.email_backend == "ses":
        import boto3

        client = boto3.client("ses", region_name=settings.ses_region)
        resp = client.send_email(
            Source=settings.email_from, Destination={"ToAddresses": [to]},
            Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}},
        )
        return resp["MessageId"]
    log.info("EMAIL to=%s subject=%s body=%s", to, subject, body)
    return f"console-{uuid.uuid4()}"


def _send_whatsapp(to: str, template_key: str, body: str) -> str:
    if settings.whatsapp_backend == "cloud_api":
        # Approved message templates are required outside the 24h window; map template_key -> approved name.
        r = httpx.post(
            f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["messages"][0]["id"]
    log.info("WHATSAPP to=%s body=%s", to, body)
    return f"console-{uuid.uuid4()}"


def deliver(db: Session, notification_id) -> Notification | None:
    """Attempt one delivery. Raises on failure so Celery can retry; the log row records the attempt."""
    n = db.get(Notification, notification_id)
    if not n or n.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ):
        return n
    n.attempts += 1
    subject, body = render(n.template_key, n.context)
    try:
        if n.channel == Channel.EMAIL:
            n.provider_message_id = _send_email(n.recipient, subject, body)
        else:
            n.provider_message_id = _send_whatsapp(n.recipient, n.template_key, body)
        n.status = NotificationStatus.SENT
        n.sent_at = utcnow()
        n.last_error = None
        n.next_retry_at = None
    except Exception as exc:  # noqa: BLE001
        n.last_error = str(exc)[:500]
        if n.attempts >= MAX_ATTEMPTS:
            n.status = NotificationStatus.FAILED
            n.next_retry_at = None
        else:
            n.next_retry_at = utcnow() + dt.timedelta(minutes=2 ** n.attempts)
        db.commit()
        raise
    db.commit()
    return n


def dispatch(db: Session, notification: Notification | None) -> None:
    """Hand a committed notification to the worker (or deliver inline in dev/tests)."""
    if notification is None:
        return
    nid = str(notification.id)
    if settings.celery_eager:
        try:
            deliver(db, notification.id)
        except Exception:  # noqa: BLE001 - logged on the row; retried by the sweeper
            log.exception("inline delivery failed")
        return
    try:
        from app.worker import send_notification

        send_notification.delay(nid)
    except Exception:  # noqa: BLE001 - broker down: row stays queued; sweeper task will pick it up
        log.exception("could not enqueue notification %s", nid)


def notify(db: Session, **kwargs) -> None:
    """Queue + commit + dispatch. Call after the business change is ready to be committed."""
    n = queue_notification(db, **kwargs)
    db.commit()
    dispatch(db, n)


def update_delivery_status(db: Session, provider_message_id: str, status: str, error: str | None = None) -> bool:
    n = db.scalar(select(Notification).where(Notification.provider_message_id == provider_message_id))
    if not n:
        return False
    order = [NotificationStatus.QUEUED, NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ]
    new = NotificationStatus(status)
    if new == NotificationStatus.FAILED or order.index(new) > order.index(n.status if n.status in order else NotificationStatus.QUEUED):
        n.status = new
        n.last_error = error
    return True
