import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_permission
from app.core.security import verify_signature
from app.core.serialize import pick
from app.db import get_db
from app.modules.notifications.models import Notification
from app.modules.notifications.service import update_delivery_status

admin = APIRouter(prefix="/admin/notifications", tags=["admin: notifications"])
webhooks = APIRouter(prefix="/webhooks", tags=["webhooks"])


@admin.get("")
def list_notifications(user=Depends(require_permission("request.read_all")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(300)).all()
    return [pick(n, "id", "channel", "template_key", "status", "attempts", "last_error", "created_at", "sent_at", "request_id") for n in rows]


@webhooks.get("/whatsapp")
def whatsapp_verify(hub_mode: str = Query(alias="hub.mode", default=""), hub_verify_token: str = Query(alias="hub.verify_token", default=""), hub_challenge: str = Query(alias="hub.challenge", default="")):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    raise HTTPException(403, "Forbidden")


@webhooks.post("/whatsapp")
async def whatsapp_status(request: Request, x_hub_signature_256: str = Header(default=""), db: Session = Depends(get_db)):
    body = await request.body()
    if not verify_signature(settings.whatsapp_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")
    payload = json.loads(body)
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for st in change.get("value", {}).get("statuses", []):
                status = {"sent": "sent", "delivered": "delivered", "read": "read", "failed": "failed"}.get(st.get("status"))
                if status:
                    err = (st.get("errors") or [{}])[0].get("title")
                    update_delivery_status(db, st.get("id"), status, err)
    db.commit()
    return {"ok": True}
