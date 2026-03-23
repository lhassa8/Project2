"""API routes for policy configuration."""

from fastapi import APIRouter

from ..services.policy_engine import PolicyEngine

router = APIRouter(prefix="/api/policies", tags=["policies"])

_engine = PolicyEngine()


@router.get("")
def list_policies() -> list[dict]:
    """Get current policy configuration."""
    return _engine.get_policy_config()
