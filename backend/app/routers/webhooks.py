"""API routes for webhook configuration and delivery history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context, require_role
from ..database import get_db
from ..services.webhooks import WEBHOOK_EVENTS, WebhookStore

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    events: list[str]
    secret: str | None = None


class UpdateWebhookRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    is_active: bool | None = None


@router.get("/events")
def list_webhook_events() -> list[str]:
    """List all subscribable event types."""
    return WEBHOOK_EVENTS


@router.get("")
def list_webhooks(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all active webhooks for the current workspace."""
    return WebhookStore(db).list_for_workspace(auth.workspace_id)


@router.post("", status_code=201)
def create_webhook(
    req: CreateWebhookRequest,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new webhook (admin only)."""
    invalid_events = [e for e in req.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(status_code=400, detail=f"Invalid event types: {invalid_events}")
    return WebhookStore(db).create(
        workspace_id=auth.workspace_id,
        name=req.name,
        url=req.url,
        events=req.events,
        secret=req.secret,
    )


@router.put("/{webhook_id}")
def update_webhook(
    webhook_id: int,
    req: UpdateWebhookRequest,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Update a webhook (admin only)."""
    store = WebhookStore(db)
    hook = store.get(webhook_id)
    if hook is None or hook["workspace_id"] != auth.workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    updates = req.model_dump(exclude_none=True)
    if "events" in updates:
        invalid = [e for e in updates["events"] if e not in WEBHOOK_EVENTS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid event types: {invalid}")

    result = store.update(webhook_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return result


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a webhook (admin only)."""
    store = WebhookStore(db)
    hook = store.get(webhook_id)
    if hook is None or hook["workspace_id"] != auth.workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    store.delete(webhook_id)
    return {"deleted": True}


@router.get("/{webhook_id}/deliveries")
def get_deliveries(
    webhook_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get recent delivery history for a webhook."""
    store = WebhookStore(db)
    hook = store.get(webhook_id)
    if hook is None or hook["workspace_id"] != auth.workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return store.get_deliveries(webhook_id)


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Send a test event to a webhook."""
    store = WebhookStore(db)
    hook = store.get(webhook_id)
    if hook is None or hook["workspace_id"] != auth.workspace_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    from ..services.webhooks import deliver_webhook
    test_payload = {
        "event": "webhook.test",
        "workspace_id": auth.workspace_id,
        "webhook_id": webhook_id,
        "message": "This is a test webhook delivery from AgentSandbox.",
    }
    status_code, resp_body, success = await deliver_webhook(
        url=hook["url"],
        event_type="webhook.test",
        payload=test_payload,
        secret=hook.get("secret"),
    )
    store.record_delivery(webhook_id, "webhook.test", test_payload, status_code, resp_body, success)
    return {
        "success": success,
        "status_code": status_code,
        "response": resp_body[:500] if resp_body else None,
    }
