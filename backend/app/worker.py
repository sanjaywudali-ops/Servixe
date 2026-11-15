"""Celery worker: notifications, reminders, retries and scheduled housekeeping."""
import datetime as dt

from celery import Celery
from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal, utcnow

celery_app = Celery("servixe", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    beat_schedule={
        "retry-queued-notifications": {"task": "app.worker.sweep_notifications", "schedule": 120.0},
        "job-reminders": {"task": "app.worker.send_job_reminders", "schedule": 900.0},
        "provider-doc-expiry": {"task": "app.worker.flag_expiring_documents", "schedule": 86400.0},
        "expire-quotes": {"task": "app.worker.expire_quotes", "schedule": 3600.0},
    },
)


@celery_app.task(bind=True, max_retries=5, name="app.worker.send_notification")
def send_notification(self, notification_id: str):
    from app.modules.notifications.service import deliver

    with SessionLocal() as db:
        try:
            deliver(db, notification_id)
        except Exception as exc:  # noqa: BLE001
            raise self.retry(exc=exc, countdown=min(60 * 2**self.request.retries, 3600))


@celery_app.task(name="app.worker.sweep_notifications")
def sweep_notifications():
    """Pick up queued notifications whose first dispatch failed, or whose retry time has arrived."""
    from app.modules.notifications.models import Notification, NotificationStatus

    with SessionLocal() as db:
        now = utcnow()
        rows = db.scalars(
            select(Notification).where(
                Notification.status == NotificationStatus.QUEUED,
                (Notification.next_retry_at.is_(None) | (Notification.next_retry_at <= now)),
                Notification.created_at <= now - dt.timedelta(minutes=1),
            ).limit(200)
        ).all()
        for n in rows:
            send_notification.delay(str(n.id))
        return len(rows)


@celery_app.task(name="app.worker.send_job_reminders")
def send_job_reminders():
    from app.modules.assignments.models import Assignment, AssignmentStatus
    from app.modules.notifications.service import link, notify

    with SessionLocal() as db:
        now = utcnow()
        horizon = now + dt.timedelta(hours=24)
        rows = db.scalars(
            select(Assignment).where(
                Assignment.status == AssignmentStatus.ACCEPTED,
                Assignment.window_start.is_not(None),
                Assignment.window_start.between(now, horizon),
                Assignment.checked_in_at.is_(None),
            )
        ).all()
        for a in rows:
            if a.provider.email:
                notify(
                    db, template_key="job_reminder", email=a.provider.email, request_id=a.request_id,
                    context={"reference": a.request.reference, "link": link(f"/provider/jobs/{a.id}")},
                    dedupe_key=f"reminder:{a.id}:{a.window_start.date()}",
                )
        return len(rows)


@celery_app.task(name="app.worker.flag_expiring_documents")
def flag_expiring_documents():
    from app.modules.providers.models import ProviderDocument
    from app.modules.identity.models import User
    from app.modules.notifications.service import link, notify

    with SessionLocal() as db:
        soon = utcnow() + dt.timedelta(days=30)
        docs = db.scalars(select(ProviderDocument).where(ProviderDocument.expires_at.is_not(None), ProviderDocument.expires_at <= soon)).all()
        admins = db.scalars(select(User).where(User.is_active.is_(True))).all()
        admins = [u for u in admins if u.role_name == "admin"]
        for d in docs:
            for u in admins:
                notify(db, template_key="doc_expiring", user=u,
                       context={"date": d.expires_at.date(), "link": link(f"/admin/providers/{d.provider_id}")},
                       dedupe_key=f"docexp:{d.id}:{u.id}")
        return len(docs)


@celery_app.task(name="app.worker.expire_quotes")
def expire_quotes():
    from app.modules.approvals.models import Approval, ApprovalStatus

    with SessionLocal() as db:
        now = utcnow()
        rows = db.scalars(select(Approval).where(Approval.status == ApprovalStatus.PENDING, Approval.valid_until.is_not(None), Approval.valid_until < now)).all()
        for a in rows:
            a.status = ApprovalStatus.EXPIRED
        db.commit()
        return len(rows)
