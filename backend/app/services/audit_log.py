"""Audit logging — immutable event log for compliance and forensics.

Records every significant action: run creation, approvals, policy changes,
API key operations, and webhook deliveries. Stored in a separate append-only
table with workspace scoping.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from ..database import Base


class AuditLogRow(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    actor = Column(String, nullable=False)  # API key name or "system"
    resource_type = Column(String, nullable=False)  # "run", "approval", "policy", "api_key", "webhook"
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


# Event types
EVENT_RUN_CREATED = "run.created"
EVENT_RUN_COMPLETED = "run.completed"
EVENT_RUN_FAILED = "run.failed"
EVENT_APPROVAL_SUBMITTED = "approval.submitted"
EVENT_APPROVAL_APPROVED = "approval.approved"
EVENT_APPROVAL_REJECTED = "approval.rejected"
EVENT_POLICY_UPDATED = "policy.updated"
EVENT_POLICY_CREATED = "policy.created"
EVENT_POLICY_DELETED = "policy.deleted"
EVENT_API_KEY_CREATED = "api_key.created"
EVENT_API_KEY_REVOKED = "api_key.revoked"
EVENT_WEBHOOK_DELIVERED = "webhook.delivered"
EVENT_WEBHOOK_FAILED = "webhook.failed"
EVENT_RUN_REPLAYED = "run.replayed"
EVENT_RUN_EXPORTED = "run.exported"
EVENT_MCP_SESSION_CREATED = "mcp.session_created"
EVENT_MCP_SESSION_FINALIZED = "mcp.session_finalized"


class AuditLogger:
    """Writes audit events to the database."""

    def __init__(self, session: Session):
        self.session = session

    def log(
        self,
        workspace_id: str,
        event_type: str,
        actor: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict:
        row = AuditLogRow(
            workspace_id=workspace_id,
            event_type=event_type,
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details, default=str) if details else None,
        )
        self.session.add(row)
        self.session.commit()
        return self._row_to_dict(row)

    def query(
        self,
        workspace_id: str,
        event_type: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        q = self.session.query(AuditLogRow).filter(
            AuditLogRow.workspace_id == workspace_id
        )
        if event_type:
            q = q.filter(AuditLogRow.event_type == event_type)
        if resource_type:
            q = q.filter(AuditLogRow.resource_type == resource_type)
        if resource_id:
            q = q.filter(AuditLogRow.resource_id == resource_id)
        q = q.order_by(AuditLogRow.timestamp.desc())
        q = q.offset(offset).limit(limit)
        return [self._row_to_dict(row) for row in q.all()]

    def count(self, workspace_id: str, event_type: str | None = None) -> int:
        q = self.session.query(AuditLogRow).filter(
            AuditLogRow.workspace_id == workspace_id
        )
        if event_type:
            q = q.filter(AuditLogRow.event_type == event_type)
        return q.count()

    @staticmethod
    def _row_to_dict(row: AuditLogRow) -> dict:
        return {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "event_type": row.event_type,
            "actor": row.actor,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "details": json.loads(row.details) if row.details else None,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
