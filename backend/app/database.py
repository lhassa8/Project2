"""SQLite database layer using SQLAlchemy."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./agent_sandbox.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class RunRow(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True)
    agent_definition = Column(Text, nullable=False)
    run_context = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="running")
    actions = Column(Text, nullable=False, default="[]")
    diffs = Column(Text, nullable=False, default="[]")
    approval = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class RunStore:
    """Thin data-access wrapper around the runs table."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, run: dict) -> None:
        row = self.session.get(RunRow, run["id"])
        if row is None:
            row = RunRow(
                id=run["id"],
                agent_definition=json.dumps(run["agent_definition"]),
                run_context=json.dumps(run["run_context"]),
                status=run["status"],
                actions=json.dumps(run["actions"], default=str),
                diffs=json.dumps(run.get("diffs", []), default=str),
                approval=json.dumps(run["approval"], default=str) if run.get("approval") else None,
                error=run.get("error"),
                created_at=datetime.fromisoformat(run["created_at"]) if isinstance(run["created_at"], str) else run["created_at"],
            )
            self.session.add(row)
        else:
            row.status = run["status"]
            row.actions = json.dumps(run["actions"], default=str)
            row.diffs = json.dumps(run.get("diffs", []), default=str)
            row.approval = json.dumps(run["approval"], default=str) if run.get("approval") else None
            row.error = run.get("error")
        self.session.commit()

    def get(self, run_id: str) -> dict | None:
        row = self.session.get(RunRow, run_id)
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_all(self) -> list[dict]:
        rows = self.session.query(RunRow).order_by(RunRow.created_at.desc()).all()
        return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: RunRow) -> dict:
        return {
            "id": row.id,
            "agent_definition": json.loads(row.agent_definition),
            "run_context": json.loads(row.run_context),
            "status": row.status,
            "actions": json.loads(row.actions),
            "diffs": json.loads(row.diffs),
            "approval": json.loads(row.approval) if row.approval else None,
            "error": row.error,
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
