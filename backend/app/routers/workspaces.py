"""API routes for workspace management, API keys, and auth."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context, require_role
from ..database import WorkspaceStore, get_db
from ..models import APIKey, Workspace, _new_id

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str


class CreateAPIKeyRequest(BaseModel):
    name: str = "Default"
    role: str = "admin"


@router.get("/me")
async def get_current_workspace(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Get the current workspace based on auth context."""
    ws = WorkspaceStore(db).get_workspace(auth.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {**ws, "role": auth.role, "api_key_name": auth.api_key_name}


@router.post("", status_code=201)
async def create_workspace(req: CreateWorkspaceRequest, db: Session = Depends(get_db)) -> dict:
    """Create a new workspace and return it with an initial admin API key."""
    ws_store = WorkspaceStore(db)
    workspace_id = _new_id()
    ws = ws_store.create_workspace(workspace_id, req.name)

    # Auto-create an admin API key
    api_key = APIKey(workspace_id=workspace_id, name="Initial Admin Key")
    key_info = ws_store.create_api_key(api_key.key, workspace_id, api_key.name, api_key.role)

    return {
        "workspace": ws,
        "api_key": key_info,
    }


@router.post("/api-keys", status_code=201)
async def create_api_key(
    req: CreateAPIKeyRequest,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new API key for the current workspace (admin only)."""
    api_key = APIKey(workspace_id=auth.workspace_id, name=req.name, role=req.role)
    ws_store = WorkspaceStore(db)
    return ws_store.create_api_key(api_key.key, auth.workspace_id, req.name, req.role)


@router.get("/api-keys")
async def list_api_keys(
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List API keys for the current workspace (admin only)."""
    return WorkspaceStore(db).list_api_keys(auth.workspace_id)


@router.delete("/api-keys/{key}")
async def revoke_api_key(
    key: str,
    auth: AuthContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> dict:
    """Revoke an API key (admin only)."""
    ws_store = WorkspaceStore(db)
    key_info = ws_store.get_api_key(key)
    if key_info is None or key_info["workspace_id"] != auth.workspace_id:
        raise HTTPException(status_code=404, detail="API key not found")
    ws_store.revoke_api_key(key)
    return {"revoked": True}
