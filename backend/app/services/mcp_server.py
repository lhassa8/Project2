"""MCP-compatible server layer.

Implements the Model Context Protocol (MCP) JSON-RPC interface so that
existing Claude agents can connect to AgentSandbox as a drop-in replacement
for a real MCP server. All tool calls are routed through SandboxEnvironment.

Supports the core MCP methods:
  - initialize
  - tools/list
  - tools/call
  - resources/list
  - resources/read
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..models import AgentAction, SandboxRun, StateDiff
from .mock_tools import TOOL_SCHEMAS
from .sandbox_environment import SandboxEnvironment
from .policy_engine import PolicyEngine
from .risk_engine import score_run


MCP_PROTOCOL_VERSION = "2024-11-05"

MCP_SERVER_INFO = {
    "name": "agent-sandbox",
    "version": "1.0.0",
}

MCP_CAPABILITIES = {
    "tools": {"listChanged": False},
    "resources": {"subscribe": False, "listChanged": False},
}


class MCPSession:
    """Handles a single MCP client session with sandboxed tool execution."""

    def __init__(self, run: SandboxRun, environment: SandboxEnvironment | None = None):
        self.run = run
        self.session_id = uuid.uuid4().hex[:12]
        self.initialized = False
        self.sequence = 0
        self.policy_engine = PolicyEngine()
        self.policy_violations: list[dict] = []
        self._enabled_tools: set[str] = {
            t.name for t in run.agent_definition.tools if t.enabled
        }

        env_config = run.run_context.environment.model_dump() if hasattr(run.run_context, 'environment') else {}
        self.env = environment or SandboxEnvironment(
            env_config if env_config.get("filesystem") or env_config.get("database") or env_config.get("http_stubs") else None
        )
        self.initial_snapshot = self.env.to_snapshot()

    def handle_message(self, message: dict) -> dict:
        """Process an incoming MCP JSON-RPC message and return a response."""
        msg_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params", {})

        if method == "initialize":
            return self._handle_initialize(msg_id, params)
        elif method == "initialized":
            return self._handle_initialized_notification()
        elif method == "tools/list":
            return self._handle_tools_list(msg_id)
        elif method == "tools/call":
            return self._handle_tools_call(msg_id, params)
        elif method == "resources/list":
            return self._handle_resources_list(msg_id)
        elif method == "resources/read":
            return self._handle_resources_read(msg_id, params)
        elif method == "ping":
            return self._success(msg_id, {})
        else:
            return self._error(msg_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, msg_id: Any, params: dict) -> dict:
        self.initialized = True
        return self._success(msg_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": MCP_CAPABILITIES,
            "serverInfo": MCP_SERVER_INFO,
        })

    def _handle_initialized_notification(self) -> dict:
        # Notification — no response needed (but we return empty for consistency)
        return {}

    def _handle_tools_list(self, msg_id: Any) -> dict:
        tools = []
        for schema in TOOL_SCHEMAS:
            if schema["name"] in self._enabled_tools:
                tools.append({
                    "name": schema["name"],
                    "description": schema["description"],
                    "inputSchema": schema["input_schema"],
                })
        return self._success(msg_id, {"tools": tools})

    def _handle_tools_call(self, msg_id: Any, params: dict) -> dict:
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in self._enabled_tools:
            return self._error(msg_id, -32602, f"Tool not available: {tool_name}")

        # Policy check
        violations = self.policy_engine.evaluate(tool_name, tool_args, self.sequence + 1)
        if violations:
            for v in violations:
                self.policy_violations.append(v.to_dict())
            blocker = next((v for v in violations if v.policy_action.value == "block"), None)
            if blocker:
                return self._error(msg_id, -32000, f"Policy blocked: {blocker.description}")
            approval_required = next((v for v in violations if v.policy_action.value == "require_approval"), None)
            if approval_required:
                return self._error(msg_id, -32001, f"Human approval required: {approval_required.description}")

        # Record action
        self.sequence += 1
        call_action = AgentAction(
            sequence=self.sequence,
            action_type="tool_call",
            content={"tool": tool_name, "arguments": tool_args},
            timestamp=datetime.now(timezone.utc),
            mock_system=tool_name.split("_")[0] if "_" in tool_name else tool_name,
        )
        self.run.actions.append(call_action)

        # Execute
        result, diffs = self._execute_tool(tool_name, tool_args)
        self.run.diffs.extend(diffs)

        # Record response
        self.sequence += 1
        resp_action = AgentAction(
            sequence=self.sequence,
            action_type="tool_response",
            content={"tool": tool_name, "result": result},
            timestamp=datetime.now(timezone.utc),
            mock_system=tool_name.split("_")[0] if "_" in tool_name else tool_name,
        )
        self.run.actions.append(resp_action)

        return self._success(msg_id, {
            "content": [{"type": "text", "text": json.dumps(result)}],
            "isError": False,
        })

    def _handle_resources_list(self, msg_id: Any) -> dict:
        resources = []
        for path in self.env.filesystem:
            resources.append({
                "uri": f"file://{path}",
                "name": path.rsplit("/", 1)[-1],
                "mimeType": "text/plain",
            })
        for table in self.env.database:
            resources.append({
                "uri": f"db://{table}",
                "name": table,
                "mimeType": "application/json",
            })
        return self._success(msg_id, {"resources": resources})

    def _handle_resources_read(self, msg_id: Any, params: dict) -> dict:
        uri = params.get("uri", "")
        if uri.startswith("file://"):
            path = uri[7:]
            if path in self.env.filesystem:
                return self._success(msg_id, {
                    "contents": [{"uri": uri, "mimeType": "text/plain", "text": self.env.filesystem[path]}],
                })
            return self._error(msg_id, -32602, f"Resource not found: {uri}")
        elif uri.startswith("db://"):
            table = uri[5:]
            if table in self.env.database:
                return self._success(msg_id, {
                    "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(self.env.database[table])}],
                })
            return self._error(msg_id, -32602, f"Resource not found: {uri}")
        return self._error(msg_id, -32602, f"Unsupported URI scheme: {uri}")

    def _execute_tool(self, name: str, args: dict) -> tuple[dict, list[StateDiff]]:
        if name == "read_file":
            return self.env.read_file(args.get("path", ""))
        elif name == "write_file":
            return self.env.write_file(args.get("path", ""), args.get("content", ""))
        elif name == "send_email":
            return self.env.send_email(args.get("to", ""), args.get("subject", ""), args.get("body", ""))
        elif name == "http_request":
            return self.env.http_request(args.get("method", "GET"), args.get("url", ""), args.get("body"))
        elif name == "query_database":
            return self.env.query_database(args.get("query", ""))
        return {"error": f"Unknown tool: {name}"}, []

    def get_risk_report(self) -> dict:
        actions_dicts = [a.model_dump(mode="json") for a in self.run.actions]
        diffs_dicts = [d.model_dump(mode="json") for d in self.run.diffs]
        report = score_run(actions_dicts, diffs_dicts)
        return report.to_dict()

    @staticmethod
    def _success(msg_id: Any, result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
