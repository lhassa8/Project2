"""Shared test fixtures for backend tests."""

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, RunStore, WorkspaceStore
from app.main import app
from app.database import get_db
from app.auth import AuthContext, get_auth_context


# ── In-memory SQLite for tests ──────────────────────────────────────────────

@pytest.fixture()
def db_engine():
    """Shared in-memory engine for one test — same connection pool so all
    code (including the MCP router) sees the same tables."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def run_store(db_session):
    return RunStore(db_session)


@pytest.fixture()
def workspace_store(db_session):
    return WorkspaceStore(db_session)


# ── FastAPI test client with dependency overrides ───────────────────────────

def _make_client(db_session, workspace_id, role, key_name):
    def _override_db():
        yield db_session

    def _override_auth():
        return AuthContext(workspace_id=workspace_id, role=role, api_key_name=key_name)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_auth_context] = _override_auth
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client(db_session):
    c = _make_client(db_session, "ws_test", "admin", "test-key")
    yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def viewer_client(db_session):
    c = _make_client(db_session, "ws_test", "viewer", "viewer-key")
    yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def other_workspace_client(db_session):
    c = _make_client(db_session, "ws_other", "admin", "other-key")
    yield c
    app.dependency_overrides.clear()


# ── Helpers ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_run_data():
    """A minimal completed run dict for seeding the DB."""
    return {
        "id": "run_test_001",
        "workspace_id": "ws_test",
        "agent_definition": {"name": "Test Agent", "goal": "Do something", "tools": [], "model": "claude-sonnet-4-20250514", "max_tokens": 1024, "temperature": 0.0},
        "run_context": {"user_persona": "Tester", "initial_state": {}, "environment": {"filesystem": {}, "database": {}, "http_stubs": []}},
        "status": "complete",
        "actions": [
            {"sequence": 1, "action_type": "tool_call", "content": {"tool": "read_file", "arguments": {"path": "/data.txt"}}, "timestamp": "2025-01-01T00:00:00+00:00", "duration_ms": 10, "mock_system": "read"},
            {"sequence": 2, "action_type": "tool_response", "content": {"tool": "read_file", "result": {"path": "/data.txt", "content": "hello"}}, "timestamp": "2025-01-01T00:00:01+00:00", "duration_ms": 5, "mock_system": "read"},
            {"sequence": 3, "action_type": "final_output", "content": {"text": "Done"}, "timestamp": "2025-01-01T00:00:02+00:00", "duration_ms": 100, "mock_system": None},
        ],
        "diffs": [],
        "approval": None,
        "risk_report": {"overall_score": 10, "risk_level": "low", "signals": [], "summary": "Low risk", "recommendations": []},
        "policy_violations": [],
        "error": None,
        "initial_snapshot": {"filesystem": {}, "database": {}, "emails_sent": [], "http_log": []},
        "final_snapshot": {"filesystem": {}, "database": {}, "emails_sent": [], "http_log": []},
        "created_at": "2025-01-01T00:00:00+00:00",
    }
