"""API routes for sandbox runs, approvals, and WebSocket streaming."""

from __future__ import annotations

import asyncio
import json
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
    store.save(run.model_dump())

    # Run the agent in the background
    asyncio.create_task(_execute_run(run, store))

    return {"id": run.id, "status": run.status}


async def _execute_run(run: SandboxRun, store: RunStore) -> None:
    runner = SandboxRunner(run)
    async for action in runner.run_agent():
        # Broadcast to any WebSocket listeners
        await _broadcast(run.id, {
            "type": "action",
            "action": action.model_dump(mode="json"),
        })
        # Persist after each action
        store.save(run.model_dump(mode="json"))

    # Final broadcast
    await _broadcast(run.id, {
        "type": "run_complete",
        "status": run.status,
        "error": run.error,
    })
    store.save(run.model_dump(mode="json"))


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


# ── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/{run_id}/ws")
async def run_websocket(websocket: WebSocket, run_id: str):
    """Stream live action updates for a running sandbox."""
    await websocket.accept()
    _ws_connections.setdefault(run_id, []).append(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        conns = _ws_connections.get(run_id, [])
        if websocket in conns:
            conns.remove(websocket)
