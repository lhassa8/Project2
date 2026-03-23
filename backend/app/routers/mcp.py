"""API routes for MCP-compatible server endpoint.

Provides both a WebSocket transport (primary) and HTTP POST transport
for MCP JSON-RPC messages. Existing Claude agents connect here instead
of a real MCP server — all tool calls are sandboxed.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context
from ..database import RunStore, get_db
from ..models import AgentDefinition, RunContext, SandboxRun, ToolConfig
from ..services.mcp_server import MCPSession
from ..services.sandbox_environment import SandboxEnvironment

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

# Active MCP sessions (keyed by run_id)
_sessions: dict[str, MCPSession] = {}


class MCPSessionRequest(BaseModel):
    """Request to create a new MCP session."""
    name: str = "MCP Agent"
    goal: str = "Autonomous agent connected via MCP"
    environment: dict | None = None


@router.post("/sessions", status_code=201)
async def create_mcp_session(
    req: MCPSessionRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new MCP session backed by a sandbox run."""
    run = SandboxRun(
        agent_definition=AgentDefinition(name=req.name, goal=req.goal),
        run_context=RunContext(),
    )
    env = SandboxEnvironment(req.environment) if req.environment else None
    session = MCPSession(run, environment=env)
    _sessions[run.id] = session

    store = RunStore(db)
    run_data = run.model_dump(mode="json")
    run_data["workspace_id"] = auth.workspace_id
    run_data["initial_snapshot"] = session.initial_snapshot
    store.save(run_data)

    return {
        "session_id": session.session_id,
        "run_id": run.id,
        "endpoint_ws": f"/api/mcp/sessions/{run.id}/ws",
        "endpoint_http": f"/api/mcp/sessions/{run.id}/message",
    }


@router.post("/sessions/{run_id}/message")
async def mcp_message(
    run_id: str,
    message: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Handle an MCP JSON-RPC message via HTTP POST."""
    session = _sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="MCP session not found")

    response = session.handle_message(message)

    # Persist updated run state
    store = RunStore(db)
    run_data = session.run.model_dump(mode="json")
    run_data["initial_snapshot"] = session.initial_snapshot
    run_data["final_snapshot"] = session.env.to_snapshot()
    store.save(run_data)

    return response


@router.websocket("/sessions/{run_id}/ws")
async def mcp_websocket(websocket: WebSocket, run_id: str):
    """Handle an MCP session over WebSocket (primary transport)."""
    session = _sessions.get(run_id)
    if session is None:
        await websocket.close(code=4004, reason="MCP session not found")
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                })
                continue

            response = session.handle_message(message)
            if response:  # Skip empty responses (notifications)
                await websocket.send_json(response)
    except WebSocketDisconnect:
        pass
    finally:
        # Finalize the session — compute risk report and save
        session.run.status = "complete"
        risk_report = session.get_risk_report()

        from ..database import SessionLocal
        db = SessionLocal()
        try:
            store = RunStore(db)
            run_data = session.run.model_dump(mode="json")
            run_data["risk_report"] = risk_report
            run_data["policy_violations"] = session.policy_violations
            run_data["initial_snapshot"] = session.initial_snapshot
            run_data["final_snapshot"] = session.env.to_snapshot()
            store.save(run_data)
        finally:
            db.close()


@router.get("/sessions/{run_id}")
async def get_mcp_session(run_id: str) -> dict:
    """Get status of an MCP session."""
    session = _sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="MCP session not found")

    return {
        "session_id": session.session_id,
        "run_id": run_id,
        "initialized": session.initialized,
        "action_count": len(session.run.actions),
        "policy_violations": session.policy_violations,
        "status": session.run.status,
    }


@router.post("/sessions/{run_id}/finalize")
async def finalize_mcp_session(
    run_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Explicitly finalize an MCP session and compute risk report."""
    session = _sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail="MCP session not found")

    session.run.status = "complete"
    risk_report = session.get_risk_report()

    store = RunStore(db)
    run_data = session.run.model_dump(mode="json")
    run_data["risk_report"] = risk_report
    run_data["policy_violations"] = session.policy_violations
    run_data["initial_snapshot"] = session.initial_snapshot
    run_data["final_snapshot"] = session.env.to_snapshot()
    run_data["workspace_id"] = run_data.get("workspace_id")
    store.save(run_data)

    # Clean up session
    del _sessions[run_id]

    return {
        "run_id": run_id,
        "status": "complete",
        "risk_report": risk_report,
        "action_count": len(session.run.actions),
    }
