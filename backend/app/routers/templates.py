"""API routes for template library."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context
from ..database import RunStore, get_db
from ..models import (
    AgentDefinition,
    CreateRunRequest,
    EnvironmentConfig,
    RunContext,
    SandboxRun,
)
from ..services.audit_log import AuditLogger, EVENT_RUN_CREATED
from ..services.sandbox_environment import SandboxEnvironment
from ..services.templates import get_template, list_templates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def get_templates() -> list[dict]:
    """List all available agent scenario templates."""
    return list_templates()


@router.get("/{template_id}")
def get_template_detail(template_id: str) -> dict:
    """Get full template definition including agent config and run context."""
    tmpl = get_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.post("/{template_id}/quick-run", status_code=201)
async def quick_run_template(
    template_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """One-click run: instantly create and start a sandbox run from a template."""
    tmpl = get_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")

    agent_def = AgentDefinition(**tmpl["agent_definition"])
    run_ctx = RunContext(**tmpl["run_context"])

    run = SandboxRun(agent_definition=agent_def, run_context=run_ctx)
    store = RunStore(db)

    env_config = run_ctx.environment.model_dump()
    has_data = env_config.get("filesystem") or env_config.get("database") or env_config.get("http_stubs")
    env = SandboxEnvironment(env_config if has_data else None)

    run_data = run.model_dump(mode="json")
    run_data["workspace_id"] = auth.workspace_id
    run_data["initial_snapshot"] = env.to_snapshot()
    store.save(run_data)

    AuditLogger(db).log(
        workspace_id=auth.workspace_id,
        event_type=EVENT_RUN_CREATED,
        actor=auth.api_key_name or "default",
        resource_type="run",
        resource_id=run.id,
        details={"agent_name": agent_def.name, "template": template_id},
    )

    # Import and reuse the run execution logic from runs router
    from .runs import _execute_run
    asyncio.create_task(_execute_run(run, store, auth.workspace_id, env))

    return {"id": run.id, "status": run.status, "template": template_id}
