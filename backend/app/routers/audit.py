"""API routes for audit log queries."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context
from ..database import get_db
from ..services.audit_log import AuditLogger

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def get_audit_log(
    event_type: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Query the audit log for the current workspace."""
    logger = AuditLogger(db)
    events = logger.query(
        workspace_id=auth.workspace_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
    )
    total = logger.count(auth.workspace_id, event_type=event_type)
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/summary")
def get_audit_summary(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Get summary counts of audit events by type."""
    logger = AuditLogger(db)
    from ..services.audit_log import (
        EVENT_RUN_CREATED, EVENT_APPROVAL_APPROVED, EVENT_APPROVAL_REJECTED,
        EVENT_POLICY_UPDATED, EVENT_API_KEY_CREATED, EVENT_API_KEY_REVOKED,
        EVENT_RUN_REPLAYED, EVENT_RUN_EXPORTED,
    )
    return {
        "runs_created": logger.count(auth.workspace_id, EVENT_RUN_CREATED),
        "approvals_granted": logger.count(auth.workspace_id, EVENT_APPROVAL_APPROVED),
        "approvals_rejected": logger.count(auth.workspace_id, EVENT_APPROVAL_REJECTED),
        "policy_changes": logger.count(auth.workspace_id, EVENT_POLICY_UPDATED),
        "api_keys_created": logger.count(auth.workspace_id, EVENT_API_KEY_CREATED),
        "api_keys_revoked": logger.count(auth.workspace_id, EVENT_API_KEY_REVOKED),
        "replays": logger.count(auth.workspace_id, EVENT_RUN_REPLAYED),
        "exports": logger.count(auth.workspace_id, EVENT_RUN_EXPORTED),
    }
