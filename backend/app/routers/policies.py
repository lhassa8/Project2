"""API routes for policy configuration — full CRUD.

Supports reading, creating, updating, enabling/disabling, and deleting
policies. Custom policies are stored per-workspace in the database.
Built-in policies ship with defaults but can be toggled.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context, require_role
from ..database import Base, get_db
from ..services.policy_engine import PolicyEngine

router = APIRouter(prefix="/api/policies", tags=["policies"])


class PolicyRow(Base):
    __tablename__ = "custom_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    action = Column(String, nullable=False, default="warn")
    enabled = Column(String, nullable=False, default="true")
    tool_name = Column(String, nullable=True)  # Tool this policy applies to, or null for all
    pattern = Column(String, nullable=True)  # Regex pattern to match
    target_field = Column(String, nullable=True)  # Which argument field to check (path, url, query, to)
    created_at = Column(DateTime, nullable=True)


class CreatePolicyRequest(BaseModel):
    name: str
    description: str
    action: str = "warn"  # allow, warn, block, require_approval
    tool_name: str | None = None
    pattern: str | None = None
    target_field: str | None = None


class UpdatePolicyRequest(BaseModel):
    description: str | None = None
    action: str | None = None
    enabled: bool | None = None
    pattern: str | None = None
    target_field: str | None = None


# ── Built-in policies (read-only config) ────────────────────────────────

@router.get("")
def list_policies(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Get all policies: built-in + custom for this workspace."""
    engine = PolicyEngine()
    builtin = engine.get_policy_config()

    # Fetch custom policies
    custom_rows = db.query(PolicyRow).filter(
        PolicyRow.workspace_id == auth.workspace_id
    ).all()
    custom = [_policy_row_to_dict(r) for r in custom_rows]

    return {
        "builtin": builtin,
        "custom": custom,
    }


@router.post("", status_code=201)
def create_policy(
    req: CreatePolicyRequest,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Create a custom policy for this workspace (admin only)."""
    from datetime import datetime, timezone
    row = PolicyRow(
        workspace_id=auth.workspace_id,
        name=req.name,
        description=req.description,
        action=req.action,
        tool_name=req.tool_name,
        pattern=req.pattern,
        target_field=req.target_field,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return _policy_row_to_dict(row)


@router.put("/{policy_id}")
def update_policy(
    policy_id: int,
    req: UpdatePolicyRequest,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Update a custom policy (admin only)."""
    row = db.get(PolicyRow, policy_id)
    if row is None or row.workspace_id != auth.workspace_id:
        raise HTTPException(status_code=404, detail="Policy not found")

    if req.description is not None:
        row.description = req.description
    if req.action is not None:
        row.action = req.action
    if req.enabled is not None:
        row.enabled = "true" if req.enabled else "false"
    if req.pattern is not None:
        row.pattern = req.pattern
    if req.target_field is not None:
        row.target_field = req.target_field
    db.commit()
    return _policy_row_to_dict(row)


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a custom policy (admin only)."""
    row = db.get(PolicyRow, policy_id)
    if row is None or row.workspace_id != auth.workspace_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


def _policy_row_to_dict(row: PolicyRow) -> dict:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "name": row.name,
        "description": row.description,
        "action": row.action,
        "enabled": row.enabled == "true",
        "tool_name": row.tool_name,
        "pattern": row.pattern,
        "target_field": row.target_field,
        "type": "custom",
    }
