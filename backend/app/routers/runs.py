"""API routes for sandbox runs, approvals, and WebSocket streaming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..database import RunStore, get_db
from ..models import (
    ApprovalRecord,
    ApprovalRequest,
    CreateRunRequest,
    SandboxRun,
)
from ..services.sandbox_runner import SandboxRunner
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
async def create_run(req: CreateRunRequest, db: Session = Depends(get_db)) -> dict:
    """Create and start a new sandbox run."""
    run = SandboxRun(
        agent_definition=req.agent_definition,
        run_context=req.run_context,
    )
    store = RunStore(db)

    # Save initial state
    store.save(run.model_dump(mode="json"))

    # Run the agent in the background
    asyncio.create_task(_execute_run(run, store))

    return {"id": run.id, "status": run.status}


async def _execute_run(run: SandboxRun, store: RunStore) -> None:
    runner = SandboxRunner(run)
    risk_report = None
    policy_violations = []

    async for event in runner.run_agent():
        if isinstance(event, dict):
            # Non-action events (risk report, policy violations)
            if event.get("type") == "risk_report":
                risk_report = event["report"]
                await _broadcast(run.id, event)
            elif event.get("type") == "policy_violation":
                policy_violations.append(event["violation"])
                await _broadcast(run.id, event)
        else:
            # Regular AgentAction
            await _broadcast(run.id, {
                "type": "action",
                "action": event.model_dump(mode="json"),
            })
        # Persist after each event
        run_data = run.model_dump(mode="json")
        run_data["risk_report"] = risk_report
        run_data["policy_violations"] = policy_violations
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
    run_data["risk_report"] = risk_report
    run_data["policy_violations"] = policy_violations
    store.save(run_data)


@router.get("")
def list_runs(db: Session = Depends(get_db)) -> list[dict]:
    """List all sandbox runs."""
    return RunStore(db).list_all()


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    """Get a single sandbox run with full action timeline."""
    run = RunStore(db).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/approve")
def approve_run(
    run_id: str, req: ApprovalRequest, db: Session = Depends(get_db)
) -> dict:
    """Submit an approval decision for a completed run."""
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

    # Recompute risk report for export
    risk_report = score_run(
        run_data.get("actions", []),
        run_data.get("diffs", []),
    )

    return {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "run": run_data,
        "risk_report": risk_report.to_dict(),
        "audit_metadata": {
            "tool_count": sum(1 for a in run_data.get("actions", []) if a.get("action_type") == "tool_call"),
            "systems_touched": list(set(
                d.get("system", "unknown") for d in run_data.get("diffs", [])
            )),
            "has_approval": run_data.get("approval") is not None,
            "approval_decision": run_data.get("approval", {}).get("decision") if run_data.get("approval") else None,
        },
    }


# ── WebSocket endpoint ───────────────────────────────────────────────────────

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
