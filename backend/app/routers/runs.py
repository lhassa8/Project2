"""API routes for sandbox runs, approvals, comparison, replay, and WebSocket streaming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context, require_role
from ..database import RunStore, get_db
from ..models import (
    ApprovalRecord,
    ApprovalRequest,
    CreateRunRequest,
    ReplayRequest,
    RunComparisonRequest,
    SandboxRun,
)
from ..services.comparison import compare_runs
from ..services.sandbox_runner import SandboxRunner
from ..services.sandbox_environment import SandboxEnvironment
from ..services.risk_engine import score_run

router = APIRouter(prefix="/api/runs", tags=["runs"])

# Track active WebSocket connections per run
_ws_connections: dict[str, list[WebSocket]] = {}


async def _broadcast(run_id: str, data: dict) -> None:
    conns = _ws_connections.get(run_id, [])
    dead = []
    for ws in conns:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        conns.remove(ws)


# ── REST endpoints ───────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_run(
    req: CreateRunRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Create and start a new sandbox run."""
    run = SandboxRun(
        agent_definition=req.agent_definition,
        run_context=req.run_context,
    )
    store = RunStore(db)

    # Build environment from config
    env_config = req.run_context.environment.model_dump()
    env = SandboxEnvironment(env_config if env_config.get("filesystem") or env_config.get("database") or env_config.get("http_stubs") else None)

    # Save initial state with workspace scoping
    run_data = run.model_dump(mode="json")
    run_data["workspace_id"] = auth.workspace_id
    run_data["initial_snapshot"] = env.to_snapshot()
    store.save(run_data)

    # Run the agent in the background
    asyncio.create_task(_execute_run(run, store, auth.workspace_id, env))

    return {"id": run.id, "status": run.status}


async def _execute_run(
    run: SandboxRun,
    store: RunStore,
    workspace_id: str,
    environment: SandboxEnvironment,
) -> None:
    runner = SandboxRunner(run, environment=environment)
    risk_report = None
    policy_violations = []
    final_snapshot = None

    async for event in runner.run_agent():
        if isinstance(event, dict):
            if event.get("type") == "risk_report":
                risk_report = event["report"]
                await _broadcast(run.id, event)
            elif event.get("type") == "policy_violation":
                policy_violations.append(event["violation"])
                await _broadcast(run.id, event)
            elif event.get("type") == "final_snapshot":
                final_snapshot = event["snapshot"]
        else:
            await _broadcast(run.id, {
                "type": "action",
                "action": event.model_dump(mode="json"),
            })
        # Persist after each event
        run_data = run.model_dump(mode="json")
        run_data["workspace_id"] = workspace_id
        run_data["risk_report"] = risk_report
        run_data["policy_violations"] = policy_violations
        run_data["initial_snapshot"] = runner.initial_snapshot
        if final_snapshot:
            run_data["final_snapshot"] = final_snapshot
        store.save(run_data)

    # Final broadcast
    await _broadcast(run.id, {
        "type": "run_complete",
        "status": run.status,
        "error": run.error,
        "risk_report": risk_report,
        "policy_violations": policy_violations,
    })
    run_data = run.model_dump(mode="json")
    run_data["workspace_id"] = workspace_id
    run_data["risk_report"] = risk_report
    run_data["policy_violations"] = policy_violations
    run_data["initial_snapshot"] = runner.initial_snapshot
    run_data["final_snapshot"] = runner.env.to_snapshot()
    store.save(run_data)


@router.get("")
def list_runs(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all sandbox runs for the current workspace."""
    return RunStore(db).list_all(workspace_id=auth.workspace_id)


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    """Get a single sandbox run with full action timeline."""
    run = RunStore(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/approve")
def approve_run(
    run_id: str,
    req: ApprovalRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Submit an approval decision for a completed run."""
    if not auth.can_approve:
        raise HTTPException(status_code=403, detail="Insufficient permissions to approve runs")

    store = RunStore(db)
    run_data = store.get(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run_data["status"] != "complete":
        raise HTTPException(status_code=400, detail="Can only approve completed runs")

    record = ApprovalRecord(
        run_id=run_id,
        decision=req.decision,
        reviewer_notes=req.reviewer_notes,
    )
    record.sign()

    run_data["approval"] = record.model_dump(mode="json")
    store.save(run_data)
    return run_data["approval"]


@router.get("/{run_id}/export")
def export_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    """Export a full audit artifact for a run — suitable for compliance storage."""
    run_data = RunStore(db).get(run_id)
    if run_data is None:
        raise HTTPException(status_code=404, detail="Run not found")

    risk_report = score_run(
        run_data.get("actions", []),
        run_data.get("diffs", []),
    )

    return {
        "export_version": "2.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "run": run_data,
        "risk_report": risk_report.to_dict(),
        "environment_snapshots": {
            "initial": run_data.get("initial_snapshot"),
            "final": run_data.get("final_snapshot"),
        },
        "audit_metadata": {
            "tool_count": sum(1 for a in run_data.get("actions", []) if a.get("action_type") == "tool_call"),
            "systems_touched": list(set(
                d.get("system", "unknown") for d in run_data.get("diffs", [])
            )),
            "has_approval": run_data.get("approval") is not None,
            "approval_decision": run_data.get("approval", {}).get("decision") if run_data.get("approval") else None,
            "workspace_id": run_data.get("workspace_id"),
        },
    }


# ── Run comparison ──────────────────────────────────────────────────────────

@router.post("/compare")
def compare(
    req: RunComparisonRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Compare two sandbox runs side by side."""
    store = RunStore(db)
    run_a = store.get(req.run_id_a)
    run_b = store.get(req.run_id_b)

    if run_a is None:
        raise HTTPException(status_code=404, detail=f"Run {req.run_id_a} not found")
    if run_b is None:
        raise HTTPException(status_code=404, detail=f"Run {req.run_id_b} not found")

    return compare_runs(run_a, run_b)


# ── Replay approved runs ───────────────────────────────────────────────────

@router.post("/{run_id}/replay", status_code=201)
async def replay_run(
    run_id: str,
    req: ReplayRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Replay an approved run — re-execute the same agent with optional env overrides.

    If target is 'sandbox', creates a new sandbox run with the same agent
    definition. This lets you test the same agent against different environments.
    """
    store = RunStore(db)
    original = store.get(run_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Run not found")

    if req.target == "live":
        # Live replay requires approval
        if not original.get("approval") or original["approval"].get("decision") != "approved":
            raise HTTPException(
                status_code=400,
                detail="Only approved runs can be replayed against live systems. This run is not approved.",
            )
        return {
            "status": "queued",
            "message": "Live replay queued. Connect your execution backend to consume approved runs.",
            "original_run_id": run_id,
            "approval": original["approval"],
        }

    # Sandbox replay: create a new run with same agent definition
    from ..models import AgentDefinition, RunContext, EnvironmentConfig
    agent_def = AgentDefinition(**original["agent_definition"])
    run_ctx = RunContext(**original.get("run_context", {}))

    # Apply environment overrides
    if req.environment_overrides:
        env_data = run_ctx.environment.model_dump()
        for key, val in req.environment_overrides.items():
            if key in env_data:
                if isinstance(env_data[key], dict) and isinstance(val, dict):
                    env_data[key].update(val)
                else:
                    env_data[key] = val
        run_ctx.environment = EnvironmentConfig(**env_data)

    new_run = SandboxRun(
        agent_definition=agent_def,
        run_context=run_ctx,
    )

    env_config = run_ctx.environment.model_dump()
    env = SandboxEnvironment(env_config if env_config.get("filesystem") or env_config.get("database") or env_config.get("http_stubs") else None)

    run_data = new_run.model_dump(mode="json")
    run_data["workspace_id"] = auth.workspace_id
    run_data["initial_snapshot"] = env.to_snapshot()
    store.save(run_data)

    asyncio.create_task(_execute_run(new_run, store, auth.workspace_id, env))

    return {
        "id": new_run.id,
        "status": new_run.status,
        "replayed_from": run_id,
    }


# ── WebSocket endpoint ───────────────────────────────────────────────────

@router.websocket("/{run_id}/ws")
async def run_websocket(websocket: WebSocket, run_id: str):
    """Stream live action updates for a running sandbox."""
    await websocket.accept()
    _ws_connections.setdefault(run_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        conns = _ws_connections.get(run_id, [])
        if websocket in conns:
            conns.remove(websocket)
