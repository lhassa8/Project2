"""Tests for the MCP server API — session management, tool calls, policy enforcement."""

import pytest
import app.routers.mcp as mcp_module


@pytest.fixture(autouse=True)
def clear_sessions():
    """Ensure MCP session cache is clean between tests."""
    mcp_module._sessions.clear()
    yield
    mcp_module._sessions.clear()


class TestMCPSession:
    def test_create_session(self, client):
        resp = client.post("/api/mcp/sessions", json={"name": "Test", "goal": "Test goal"})
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert "run_id" in data
        assert "endpoint_ws" in data

    def test_get_session(self, client):
        create_resp = client.post("/api/mcp/sessions", json={"name": "Test", "goal": "Test goal"})
        run_id = create_resp.json()["run_id"]
        resp = client.get(f"/api/mcp/sessions/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_get_nonexistent_session(self, client):
        resp = client.get("/api/mcp/sessions/nonexistent")
        assert resp.status_code == 404


class TestMCPToolCalls:
    def _create_session(self, client):
        resp = client.post("/api/mcp/sessions", json={"name": "Test", "goal": "Test goal"})
        return resp.json()["run_id"]

    def _send_message(self, client, run_id, method, params=None, msg_id=1):
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params:
            msg["params"] = params
        return client.post(f"/api/mcp/sessions/{run_id}/message", json=msg)

    def test_initialize(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "initialize", {"protocolVersion": "2024-11-05"})
        assert resp.status_code == 200
        result = resp.json()
        assert result["result"]["protocolVersion"] == "2024-11-05"

    def test_tools_list(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "tools/list")
        tools = resp.json()["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "read_file" in tool_names
        assert "write_file" in tool_names

    def test_tools_call_read_file(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "tools/call", {
            "name": "read_file",
            "arguments": {"path": "/data.txt"},
        })
        result = resp.json()
        assert "result" in result
        assert result["result"]["isError"] is False

    def test_tools_call_missing_args(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "tools/call", {
            "name": "read_file",
            "arguments": {},  # Missing required "path"
        })
        result = resp.json()
        assert "error" in result
        assert "Missing required" in result["error"]["message"]

    def test_tools_call_unavailable_tool(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "tools/call", {
            "name": "nonexistent_tool",
            "arguments": {},
        })
        assert "error" in resp.json()

    def test_policy_blocks_production_access(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "tools/call", {
            "name": "read_file",
            "arguments": {"path": "/etc/production/secrets.key"},
        })
        result = resp.json()
        assert "error" in result
        assert "Policy blocked" in result["error"]["message"]

    def test_unknown_method(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "nonexistent/method")
        assert "error" in resp.json()
        assert resp.json()["error"]["code"] == -32601

    def test_ping(self, client):
        run_id = self._create_session(client)
        resp = self._send_message(client, run_id, "ping")
        assert "result" in resp.json()


class TestMCPFinalize:
    def test_finalize_session(self, client):
        create_resp = client.post("/api/mcp/sessions", json={"name": "Test", "goal": "Test goal"})
        run_id = create_resp.json()["run_id"]
        resp = client.post(f"/api/mcp/sessions/{run_id}/finalize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "complete"
        assert "risk_report" in data
        # Session should be cleaned up
        assert client.get(f"/api/mcp/sessions/{run_id}").status_code == 404

    def test_finalize_nonexistent(self, client):
        resp = client.post("/api/mcp/sessions/nonexistent/finalize")
        assert resp.status_code == 404


class TestMCPWorkspaceIsolation:
    def test_session_saves_workspace_id(self, client, run_store):
        create_resp = client.post("/api/mcp/sessions", json={"name": "Test", "goal": "Test goal"})
        run_id = create_resp.json()["run_id"]
        run_data = run_store.get(run_id)
        assert run_data["workspace_id"] == "ws_test"
