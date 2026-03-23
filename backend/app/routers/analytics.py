"""API routes for analytics dashboard — workspace-scoped."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import AuthContext, get_auth_context
from ..database import RunStore, get_db
from ..services.risk_engine import score_run

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
def get_analytics(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregate analytics across all sandbox runs for the current workspace."""
    runs = RunStore(db).list_all(workspace_id=auth.workspace_id)

    total = len(runs)
    if total == 0:
        return {
            "total_runs": 0,
            "status_breakdown": {},
            "approval_breakdown": {},
            "tool_usage": {},
            "avg_actions_per_run": 0,
            "risk_distribution": {},
            "systems_touched": {},
            "runs_over_time": [],
            "top_agents": [],
        }

    # Status breakdown
    status_counts = Counter(r["status"] for r in runs)

    # Approval breakdown
    approval_counts: Counter = Counter()
    for r in runs:
        if r.get("approval"):
            approval_counts[r["approval"]["decision"]] += 1
        elif r["status"] == "complete":
            approval_counts["pending_review"] += 1

    # Tool usage
    tool_counts: Counter = Counter()
    for r in runs:
        for a in r.get("actions", []):
            if a.get("action_type") == "tool_call":
                tool = a.get("content", {}).get("tool", "unknown")
                tool_counts[tool] += 1

    # Avg actions
    total_actions = sum(len(r.get("actions", [])) for r in runs)
    avg_actions = round(total_actions / total, 1) if total else 0

    # Risk distribution
    risk_dist: Counter = Counter()
    for r in runs:
        rr = r.get("risk_report")
        if rr:
            risk_dist[rr.get("risk_level", "unknown")] += 1
        elif r["status"] == "complete":
            report = score_run(r.get("actions", []), r.get("diffs", []))
            risk_dist[report.risk_level] += 1

    # Systems touched
    system_counts: Counter = Counter()
    for r in runs:
        for d in r.get("diffs", []):
            system_counts[d.get("system", "unknown")] += 1

    # Runs over time (by date)
    date_counts: Counter = Counter()
    for r in runs:
        created = r.get("created_at", "")
        if isinstance(created, str) and len(created) >= 10:
            date_counts[created[:10]] += 1

    runs_over_time = [
        {"date": d, "count": c}
        for d, c in sorted(date_counts.items())
    ]

    # Top agents
    agent_counts: Counter = Counter()
    for r in runs:
        name = r.get("agent_definition", {}).get("name", "Unknown")
        agent_counts[name] += 1
    top_agents = [
        {"name": name, "run_count": count}
        for name, count in agent_counts.most_common(10)
    ]

    return {
        "total_runs": total,
        "status_breakdown": dict(status_counts),
        "approval_breakdown": dict(approval_counts),
        "tool_usage": dict(tool_counts.most_common(10)),
        "avg_actions_per_run": avg_actions,
        "risk_distribution": dict(risk_dist),
        "systems_touched": dict(system_counts),
        "runs_over_time": runs_over_time,
        "top_agents": top_agents,
    }
