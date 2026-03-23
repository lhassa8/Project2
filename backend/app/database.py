"""SQLite database layer using SQLAlchemy."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./agent_sandbox.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class WorkspaceRow(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class APIKeyRow(Base):
    __tablename__ = "api_keys"

    key = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, default="Default")
    role = Column(String, nullable=False, default="admin")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(String, nullable=False, default="true")


class UserRow(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="viewer")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class RunRow(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, nullable=True, index=True)
    agent_definition = Column(Text, nullable=False)
    run_context = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="running")
    actions = Column(Text, nullable=False, default="[]")
    diffs = Column(Text, nullable=False, default="[]")
    approval = Column(Text, nullable=True)
    risk_report = Column(Text, nullable=True)
    policy_violations = Column(Text, nullable=True, default="[]")
    error = Column(Text, nullable=True)
    initial_snapshot = Column(Text, nullable=True)
    final_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class WorkspaceStore:
    """Data-access wrapper for workspaces, API keys, and users."""

    def __init__(self, session: Session):
        self.session = session

    def create_workspace(self, workspace_id: str, name: str) -> dict:
        row = WorkspaceRow(id=workspace_id, name=name)
        self.session.add(row)
        self.session.commit()
        return {"id": row.id, "name": row.name, "created_at": row.created_at.isoformat()}

    def get_workspace(self, workspace_id: str) -> dict | None:
        row = self.session.get(WorkspaceRow, workspace_id)
        if row is None:
            return None
        return {"id": row.id, "name": row.name, "created_at": row.created_at.isoformat()}

    def create_api_key(self, key: str, workspace_id: str, name: str, role: str) -> dict:
        row = APIKeyRow(key=key, workspace_id=workspace_id, name=name, role=role)
        self.session.add(row)
        self.session.commit()
        return {"key": row.key, "workspace_id": row.workspace_id, "name": row.name, "role": row.role}

    def get_api_key(self, key: str) -> dict | None:
        row = self.session.get(APIKeyRow, key)
        if row is None or row.is_active != "true":
            return None
        return {"key": row.key, "workspace_id": row.workspace_id, "name": row.name, "role": row.role}

    def list_api_keys(self, workspace_id: str) -> list[dict]:
        rows = self.session.query(APIKeyRow).filter(
            APIKeyRow.workspace_id == workspace_id, APIKeyRow.is_active == "true"
        ).all()
        return [{"key": r.key, "workspace_id": r.workspace_id, "name": r.name, "role": r.role} for r in rows]

    def revoke_api_key(self, key: str) -> bool:
        row = self.session.get(APIKeyRow, key)
        if row is None:
            return False
        row.is_active = "false"
        self.session.commit()
        return True


class RunStore:
    """Thin data-access wrapper around the runs table."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, run: dict) -> None:
        row = self.session.get(RunRow, run["id"])
        if row is None:
            row = RunRow(
                id=run["id"],
                workspace_id=run.get("workspace_id"),
                agent_definition=json.dumps(run["agent_definition"]),
                run_context=json.dumps(run["run_context"]),
                status=run["status"],
                actions=json.dumps(run["actions"], default=str),
                diffs=json.dumps(run.get("diffs", []), default=str),
                approval=json.dumps(run["approval"], default=str) if run.get("approval") else None,
                risk_report=json.dumps(run.get("risk_report"), default=str) if run.get("risk_report") else None,
                policy_violations=json.dumps(run.get("policy_violations", []), default=str),
                error=run.get("error"),
                initial_snapshot=json.dumps(run.get("initial_snapshot"), default=str) if run.get("initial_snapshot") else None,
                final_snapshot=json.dumps(run.get("final_snapshot"), default=str) if run.get("final_snapshot") else None,
                created_at=datetime.fromisoformat(run["created_at"]) if isinstance(run["created_at"], str) else run["created_at"],
            )
            self.session.add(row)
        else:
            row.status = run["status"]
            row.actions = json.dumps(run["actions"], default=str)
            row.diffs = json.dumps(run.get("diffs", []), default=str)
            row.approval = json.dumps(run["approval"], default=str) if run.get("approval") else None
            row.risk_report = json.dumps(run.get("risk_report"), default=str) if run.get("risk_report") else None
            row.policy_violations = json.dumps(run.get("policy_violations", []), default=str)
            row.error = run.get("error")
            if run.get("initial_snapshot"):
                row.initial_snapshot = json.dumps(run["initial_snapshot"], default=str)
            if run.get("final_snapshot"):
                row.final_snapshot = json.dumps(run["final_snapshot"], default=str)
        self.session.commit()

    def get(self, run_id: str) -> dict | None:
        row = self.session.get(RunRow, run_id)
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_all(self, workspace_id: str | None = None) -> list[dict]:
        query = self.session.query(RunRow)
        if workspace_id:
            query = query.filter(RunRow.workspace_id == workspace_id)
        rows = query.order_by(RunRow.created_at.desc()).all()
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: RunRow) -> dict:
        return {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "agent_definition": json.loads(row.agent_definition),
            "run_context": json.loads(row.run_context),
            "status": row.status,
            "actions": json.loads(row.actions),
            "diffs": json.loads(row.diffs),
            "approval": json.loads(row.approval) if row.approval else None,
            "risk_report": json.loads(row.risk_report) if row.risk_report else None,
            "policy_violations": json.loads(row.policy_violations) if row.policy_violations else [],
            "error": row.error,
            "initial_snapshot": json.loads(row.initial_snapshot) if row.initial_snapshot else None,
            "final_snapshot": json.loads(row.final_snapshot) if row.final_snapshot else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
