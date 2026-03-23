"""Authentication middleware and dependency injection for workspace-scoped access.

Supports two auth modes:
1. API key via X-API-Key header — for programmatic access
2. No auth (development mode) — auto-creates a default workspace

Enterprise SSO-ready: the auth layer is a single point to swap in
OAuth2/SAML/OIDC without changing any route logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import WorkspaceStore, get_db
from .models import _new_id


@dataclass
class AuthContext:
    """Resolved authentication context for a request."""
    workspace_id: str
    role: str  # "admin", "reviewer", "viewer"
    api_key_name: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def can_approve(self) -> bool:
        return self.role in ("admin", "reviewer")

    @property
    def can_create_runs(self) -> bool:
        return self.role in ("admin", "reviewer")


# Default workspace for development mode
_DEFAULT_WORKSPACE_ID = "default"
_DEFAULT_WORKSPACE_NAME = "Default Workspace"


async def get_auth_context(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Resolve authentication from request headers.

    If no API key is provided, falls back to a default workspace
    (development mode). In production, this would return 401.
    """
    ws_store = WorkspaceStore(db)

    if x_api_key:
        key_info = ws_store.get_api_key(x_api_key)
        if key_info is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return AuthContext(
            workspace_id=key_info["workspace_id"],
            role=key_info["role"],
            api_key_name=key_info["name"],
        )

    # Development mode: ensure default workspace exists
    ws = ws_store.get_workspace(_DEFAULT_WORKSPACE_ID)
    if ws is None:
        ws_store.create_workspace(_DEFAULT_WORKSPACE_ID, _DEFAULT_WORKSPACE_NAME)

    return AuthContext(
        workspace_id=_DEFAULT_WORKSPACE_ID,
        role="admin",
    )


def require_role(*roles: str):
    """Dependency factory that enforces minimum role requirement."""
    async def _check(auth: AuthContext = Depends(get_auth_context)):
        if auth.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles: {', '.join(roles)}. You have: {auth.role}",
            )
        return auth
    return _check
