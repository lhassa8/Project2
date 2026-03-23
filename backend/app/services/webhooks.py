"""Webhook notification system — delivers events to external services.

Supports configurable webhook endpoints per workspace for events like:
run completion, approval decisions, policy violations, and high-risk alerts.

Delivers via async HTTP POST with HMAC-SHA256 signatures for verification.
Includes retry logic with exponential backoff.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from ..database import Base


class WebhookRow(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=True)  # For HMAC signing
    events = Column(Text, nullable=False, default="[]")  # JSON array of event types
    is_active = Column(String, nullable=False, default="true")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class WebhookDeliveryRow(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    webhook_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(String, nullable=False, default="false")
    attempt = Column(Integer, nullable=False, default=1)
    delivered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


# Subscribable event types
WEBHOOK_EVENTS = [
    "run.completed",
    "run.failed",
    "approval.submitted",
    "policy.violation",
    "risk.critical",
    "risk.high",
]


class WebhookStore:
    """CRUD for webhook configurations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, workspace_id: str, name: str, url: str, events: list[str], secret: str | None = None) -> dict:
        row = WebhookRow(
            workspace_id=workspace_id,
            name=name,
            url=url,
            secret=secret,
            events=json.dumps(events),
        )
        self.session.add(row)
        self.session.commit()
        return self._row_to_dict(row)

    def list_for_workspace(self, workspace_id: str) -> list[dict]:
        rows = self.session.query(WebhookRow).filter(
            WebhookRow.workspace_id == workspace_id,
            WebhookRow.is_active == "true",
        ).all()
        return [self._row_to_dict(r) for r in rows]

    def get(self, webhook_id: int) -> dict | None:
        row = self.session.get(WebhookRow, webhook_id)
        if row is None:
            return None
        return self._row_to_dict(row)

    def update(self, webhook_id: int, **kwargs) -> dict | None:
        row = self.session.get(WebhookRow, webhook_id)
        if row is None:
            return None
        if "name" in kwargs:
            row.name = kwargs["name"]
        if "url" in kwargs:
            row.url = kwargs["url"]
        if "events" in kwargs:
            row.events = json.dumps(kwargs["events"])
        if "secret" in kwargs:
            row.secret = kwargs["secret"]
        if "is_active" in kwargs:
            row.is_active = "true" if kwargs["is_active"] else "false"
        self.session.commit()
        return self._row_to_dict(row)

    def delete(self, webhook_id: int) -> bool:
        row = self.session.get(WebhookRow, webhook_id)
        if row is None:
            return False
        row.is_active = "false"
        self.session.commit()
        return True

    def get_subscribers(self, workspace_id: str, event_type: str) -> list[dict]:
        """Get all webhooks subscribed to a given event type."""
        all_hooks = self.list_for_workspace(workspace_id)
        return [h for h in all_hooks if event_type in h.get("events", [])]

    def record_delivery(
        self,
        webhook_id: int,
        event_type: str,
        payload: dict,
        status_code: int | None,
        response_body: str | None,
        success: bool,
        attempt: int = 1,
    ) -> dict:
        row = WebhookDeliveryRow(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=json.dumps(payload, default=str),
            status_code=status_code,
            response_body=response_body,
            success="true" if success else "false",
            attempt=attempt,
        )
        self.session.add(row)
        self.session.commit()
        return {
            "id": row.id,
            "webhook_id": row.webhook_id,
            "event_type": row.event_type,
            "status_code": row.status_code,
            "success": success,
            "attempt": row.attempt,
            "delivered_at": row.delivered_at.isoformat() if row.delivered_at else None,
        }

    def get_deliveries(self, webhook_id: int, limit: int = 20) -> list[dict]:
        rows = self.session.query(WebhookDeliveryRow).filter(
            WebhookDeliveryRow.webhook_id == webhook_id
        ).order_by(WebhookDeliveryRow.delivered_at.desc()).limit(limit).all()
        return [{
            "id": r.id,
            "event_type": r.event_type,
            "status_code": r.status_code,
            "success": r.success == "true",
            "attempt": r.attempt,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
        } for r in rows]

    @staticmethod
    def _row_to_dict(row: WebhookRow) -> dict:
        return {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "name": row.name,
            "url": row.url,
            "events": json.loads(row.events) if row.events else [],
            "is_active": row.is_active == "true",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


def sign_payload(payload: dict, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook verification."""
    body = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def deliver_webhook(
    url: str,
    event_type: str,
    payload: dict,
    secret: str | None = None,
    max_retries: int = 3,
) -> tuple[int | None, str | None, bool]:
    """Deliver a webhook payload via HTTP POST with retries.

    Returns (status_code, response_body, success).
    """
    import aiohttp

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event_type,
        "X-Webhook-Timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if secret:
        headers["X-Webhook-Signature"] = sign_payload(payload, secret)

    body = json.dumps(payload, default=str)

    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    resp_body = await resp.text()
                    if 200 <= resp.status < 300:
                        return resp.status, resp_body, True
                    # Retry on 5xx
                    if resp.status >= 500 and attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return resp.status, resp_body, False
        except Exception as e:
            if attempt < max_retries:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            return None, str(e), False

    return None, "Max retries exceeded", False


async def dispatch_event(
    session: Session,
    workspace_id: str,
    event_type: str,
    payload: dict,
) -> list[dict]:
    """Dispatch an event to all subscribed webhooks for a workspace."""
    store = WebhookStore(session)
    subscribers = store.get_subscribers(workspace_id, event_type)
    results = []

    for hook in subscribers:
        status_code, resp_body, success = await deliver_webhook(
            url=hook["url"],
            event_type=event_type,
            payload=payload,
            secret=hook.get("secret"),
        )
        delivery = store.record_delivery(
            webhook_id=hook["id"],
            event_type=event_type,
            payload=payload,
            status_code=status_code,
            response_body=resp_body,
            success=success,
        )
        results.append(delivery)

    return results
