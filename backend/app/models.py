"""Core data models for AgentSandbox."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# ── Agent definition & run context ──────────────────────────────────────────

class ToolConfig(BaseModel):
    name: str
    enabled: bool = True


class AgentDefinition(BaseModel):
    name: str = "Unnamed Agent"
    goal: str
    tools: list[ToolConfig] = Field(default_factory=lambda: [
        ToolConfig(name="read_file"),
        ToolConfig(name="write_file"),
        ToolConfig(name="send_email"),
        ToolConfig(name="http_request"),
        ToolConfig(name="query_database"),
    ])
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.0


MAX_ENV_FILES = 50
MAX_ENV_FILE_SIZE = 100_000  # 100KB per file
MAX_ENV_TABLES = 20
MAX_ENV_ROWS_PER_TABLE = 500
MAX_ENV_HTTP_STUBS = 50


class EnvironmentConfig(BaseModel):
    """Configurable seed data for the sandbox environment."""
    filesystem: dict[str, str] = Field(default_factory=dict)
    database: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    http_stubs: list[dict[str, Any]] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if len(self.filesystem) > MAX_ENV_FILES:
            raise ValueError(f"Environment filesystem exceeds {MAX_ENV_FILES} files")
        for path, content in self.filesystem.items():
            if len(content) > MAX_ENV_FILE_SIZE:
                raise ValueError(f"File {path} exceeds {MAX_ENV_FILE_SIZE} bytes")
        if len(self.database) > MAX_ENV_TABLES:
            raise ValueError(f"Environment database exceeds {MAX_ENV_TABLES} tables")
        for table, rows in self.database.items():
            if len(rows) > MAX_ENV_ROWS_PER_TABLE:
                raise ValueError(f"Table {table} exceeds {MAX_ENV_ROWS_PER_TABLE} rows")
        if len(self.http_stubs) > MAX_ENV_HTTP_STUBS:
            raise ValueError(f"Environment http_stubs exceeds {MAX_ENV_HTTP_STUBS} stubs")


class RunContext(BaseModel):
    user_persona: str = "Enterprise user"
    initial_state: dict[str, Any] = Field(default_factory=dict)
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)


# ── Actions & diffs ────────────────────────────────────────────────────────

class AgentAction(BaseModel):
    sequence: int
    action_type: Literal["thought", "tool_call", "tool_response", "final_output"]
    content: dict[str, Any]
    timestamp: datetime = Field(default_factory=_utcnow)
    duration_ms: int = 0
    mock_system: str | None = None


class StateDiff(BaseModel):
    system: str
    resource_id: str
    before: dict[str, Any] | str | None = None
    after: dict[str, Any] | str
    change_type: Literal["created", "modified", "deleted"]


# ── Approval ────────────────────────────────────────────────────────────────

import os as _os
APPROVAL_SECRET = _os.environ.get("SANDBOX_APPROVAL_SECRET", "agent-sandbox-hmac-secret-change-me")


class ApprovalRecord(BaseModel):
    run_id: str
    decision: Literal["approved", "changes_requested", "rejected"]
    reviewer_notes: str = ""
    approved_at: datetime = Field(default_factory=_utcnow)
    signature: str = ""

    def _payload(self) -> str:
        return f"{self.run_id}:{self.decision}:{self.approved_at.isoformat()}"

    def sign(self) -> None:
        self.signature = hmac.new(
            APPROVAL_SECRET.encode(), self._payload().encode(), hashlib.sha256
        ).hexdigest()

    def verify(self) -> bool:
        """Verify the HMAC signature matches the current payload."""
        if not self.signature:
            return False
        expected = hmac.new(
            APPROVAL_SECRET.encode(), self._payload().encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(self.signature, expected)


# ── Sandbox run ─────────────────────────────────────────────────────────────

class SandboxRun(BaseModel):
    id: str = Field(default_factory=_new_id)
    agent_definition: AgentDefinition
    run_context: RunContext = Field(default_factory=RunContext)
    status: Literal["running", "complete", "failed"] = "running"
    actions: list[AgentAction] = Field(default_factory=list)
    diffs: list[StateDiff] = Field(default_factory=list)
    approval: ApprovalRecord | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    error: str | None = None


# ── API request/response models ─────────────────────────────────────────────

class CreateRunRequest(BaseModel):
    agent_definition: AgentDefinition
    run_context: RunContext = Field(default_factory=RunContext)


class ApprovalRequest(BaseModel):
    decision: Literal["approved", "changes_requested", "rejected"]
    reviewer_notes: str = ""


# ── Auth & workspaces ─────────────────────────────────────────────────────

class Workspace(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str
    created_at: datetime = Field(default_factory=_utcnow)


class APIKey(BaseModel):
    key: str = Field(default_factory=lambda: f"ask_{uuid.uuid4().hex}")
    workspace_id: str
    name: str = "Default"
    role: Literal["admin", "reviewer", "viewer"] = "admin"
    created_at: datetime = Field(default_factory=_utcnow)
    is_active: bool = True


class User(BaseModel):
    id: str = Field(default_factory=_new_id)
    email: str
    name: str
    workspace_id: str
    role: Literal["admin", "reviewer", "viewer"] = "viewer"
    created_at: datetime = Field(default_factory=_utcnow)


# ── Run comparison ────────────────────────────────────────────────────────

class RunComparisonRequest(BaseModel):
    run_id_a: str
    run_id_b: str


# ── Execution replay ─────────────────────────────────────────────────────

class ReplayRequest(BaseModel):
    target: Literal["sandbox", "live"] = "sandbox"
    environment_overrides: dict[str, Any] = Field(default_factory=dict)
