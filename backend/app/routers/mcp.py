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


class _MCPSessionEntry:
    """In-memory session state including workspace context."""
    __slots__ = ("session", "workspace_id")

    def __init__(self, session: MCPSession, workspace_id: str):
        self.session = session
        self.workspace_id = workspace_id


# Active MCP sessions (keyed by run_id)
_sessions: dict[str, _MCPSessionEntry] = {}


class MCPSessionRequest(BaseModel):
    """Request to create a new MCP session."""
    name: str = "MCP Agent"
    goal: str = "Autonomous agent connected via MCP"
    environment: dict | None = None


def _save_session(entry: _MCPSessionEntry, db_session: Session) -> None:
    """Persist current MCP session state to the database with workspace_id."""
    store = RunStore(db_session)
    run_data = entry.session.run.model_dump(mode="json")
    run_data["workspace_id"] = entry.workspace_id
    run_data["initial_snapshot"] = entry.session.initial_snapshot
    run_data["final_snapshot"] = entry.session.env.to_snapshot()
    run_data["policy_violations"] = entry.session.policy_violations
    store.save(run_data)


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
    entry = _MCPSessionEntry(session, auth.workspace_id)
    _sessions[run.id] = entry

    _save_session(entry, db)

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
    entry = _sessions.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="MCP session not found")

    response = entry.session.handle_message(message)
    _save_session(entry, db)

    return response


@router.websocket("/sessions/{run_id}/ws")
async def mcp_websocket(websocket: WebSocket, run_id: str):
    """Handle an MCP session over WebSocket (primary transport)."""
    entry = _sessions.get(run_id)
    if entry is None:
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

            response = entry.session.handle_message(message)
            if response:
                await websocket.send_json(response)
    except WebSocketDisconnect:
        pass
    finally:
        # Finalize the session
        entry.session.run.status = "complete"
        risk_report = entry.session.get_risk_report()

        from ..database import SessionLocal
        db = SessionLocal()
        try:
            store = RunStore(db)
            run_data = entry.session.run.model_dump(mode="json")
            run_data["workspace_id"] = entry.workspace_id
            run_data["risk_report"] = risk_report
            run_data["policy_violations"] = entry.session.policy_violations
            run_data["initial_snapshot"] = entry.session.initial_snapshot
            run_data["final_snapshot"] = entry.session.env.to_snapshot()
            store.save(run_data)
        finally:
            db.close()


@router.get("/sessions/{run_id}")
async def get_mcp_session(run_id: str) -> dict:
    """Get status of an MCP session."""
    entry = _sessions.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="MCP session not found")

    return {
        "session_id": entry.session.session_id,
        "run_id": run_id,
        "initialized": entry.session.initialized,
        "action_count": len(entry.session.run.actions),
        "policy_violations": entry.session.policy_violations,
        "status": entry.session.run.status,
    }


@router.post("/sessions/{run_id}/finalize")
async def finalize_mcp_session(
    run_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Explicitly finalize an MCP session and compute risk report."""
    entry = _sessions.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="MCP session not found")

    entry.session.run.status = "complete"
    risk_report = entry.session.get_risk_report()

    store = RunStore(db)
    run_data = entry.session.run.model_dump(mode="json")
    run_data["workspace_id"] = entry.workspace_id
    run_data["risk_report"] = risk_report
    run_data["policy_violations"] = entry.session.policy_violations
    run_data["initial_snapshot"] = entry.session.initial_snapshot
    run_data["final_snapshot"] = entry.session.env.to_snapshot()
    store.save(run_data)

    del _sessions[run_id]

    return {
        "run_id": run_id,
        "status": "complete",
        "risk_report": risk_report,
        "action_count": len(entry.session.run.actions),
    }
