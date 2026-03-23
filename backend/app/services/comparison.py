"""Run comparison engine — diff two sandbox runs side-by-side.

Compares actions, state changes, risk profiles, tool usage patterns,
and environment state between two runs to identify behavioral differences.
"""

from __future__ import annotations

from typing import Any


def compare_runs(run_a: dict, run_b: dict) -> dict:
    """Produce a structured diff between two sandbox runs."""
    return {
        "run_a_id": run_a["id"],
        "run_b_id": run_b["id"],
        "metadata": _compare_metadata(run_a, run_b),
        "tool_usage": _compare_tool_usage(run_a, run_b),
        "risk": _compare_risk(run_a, run_b),
        "state_changes": _compare_state_changes(run_a, run_b),
        "action_sequence": _compare_action_sequences(run_a, run_b),
        "environment": _compare_environments(run_a, run_b),
        "summary": _generate_summary(run_a, run_b),
    }


def _compare_metadata(a: dict, b: dict) -> dict:
    return {
        "run_a": {
            "name": a.get("agent_definition", {}).get("name", "Unknown"),
            "status": a.get("status"),
            "action_count": len(a.get("actions", [])),
            "diff_count": len(a.get("diffs", [])),
            "created_at": a.get("created_at"),
        },
        "run_b": {
            "name": b.get("agent_definition", {}).get("name", "Unknown"),
            "status": b.get("status"),
            "action_count": len(b.get("actions", [])),
            "diff_count": len(b.get("diffs", [])),
            "created_at": b.get("created_at"),
        },
    }


def _compare_tool_usage(a: dict, b: dict) -> dict:
    def _count_tools(run: dict) -> dict[str, int]:
        counts: dict[str, int] = {}
        for action in run.get("actions", []):
            if action.get("action_type") == "tool_call":
                tool = action.get("content", {}).get("tool", "unknown")
                counts[tool] = counts.get(tool, 0) + 1
        return counts

    tools_a = _count_tools(a)
    tools_b = _count_tools(b)
    all_tools = sorted(set(tools_a) | set(tools_b))

    comparison = []
    for tool in all_tools:
        ca = tools_a.get(tool, 0)
        cb = tools_b.get(tool, 0)
        comparison.append({
            "tool": tool,
            "run_a_count": ca,
            "run_b_count": cb,
            "difference": cb - ca,
        })

    return {
        "run_a_total": sum(tools_a.values()),
        "run_b_total": sum(tools_b.values()),
        "per_tool": comparison,
        "tools_only_in_a": [t for t in tools_a if t not in tools_b],
        "tools_only_in_b": [t for t in tools_b if t not in tools_a],
    }


def _compare_risk(a: dict, b: dict) -> dict:
    ra = a.get("risk_report") or {}
    rb = b.get("risk_report") or {}

    def _signal_categories(report: dict) -> dict[str, int]:
        cats: dict[str, int] = {}
        for s in report.get("signals", []):
            cat = s.get("category", "unknown")
            cats[cat] = cats.get(cat, 0) + 1
        return cats

    return {
        "run_a": {
            "overall_score": ra.get("overall_score", 0),
            "risk_level": ra.get("risk_level", "unknown"),
            "signal_count": len(ra.get("signals", [])),
            "categories": _signal_categories(ra),
        },
        "run_b": {
            "overall_score": rb.get("overall_score", 0),
            "risk_level": rb.get("risk_level", "unknown"),
            "signal_count": len(rb.get("signals", [])),
            "categories": _signal_categories(rb),
        },
        "score_difference": rb.get("overall_score", 0) - ra.get("overall_score", 0),
        "risk_level_changed": ra.get("risk_level") != rb.get("risk_level"),
    }


def _compare_state_changes(a: dict, b: dict) -> dict:
    def _by_system(diffs: list[dict]) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {}
        for d in diffs:
            system = d.get("system", "unknown")
            result.setdefault(system, []).append(d)
        return result

    diffs_a = _by_system(a.get("diffs", []))
    diffs_b = _by_system(b.get("diffs", []))
    all_systems = sorted(set(diffs_a) | set(diffs_b))

    per_system = {}
    for system in all_systems:
        sa = diffs_a.get(system, [])
        sb = diffs_b.get(system, [])

        resources_a = {d.get("resource_id") for d in sa}
        resources_b = {d.get("resource_id") for d in sb}

        per_system[system] = {
            "run_a_changes": len(sa),
            "run_b_changes": len(sb),
            "common_resources": sorted(resources_a & resources_b),
            "only_in_a": sorted(resources_a - resources_b),
            "only_in_b": sorted(resources_b - resources_a),
        }

    return {
        "per_system": per_system,
        "systems_only_in_a": [s for s in diffs_a if s not in diffs_b],
        "systems_only_in_b": [s for s in diffs_b if s not in diffs_a],
    }


def _compare_action_sequences(a: dict, b: dict) -> dict:
    def _tool_sequence(run: dict) -> list[str]:
        return [
            action.get("content", {}).get("tool", "unknown")
            for action in run.get("actions", [])
            if action.get("action_type") == "tool_call"
        ]

    seq_a = _tool_sequence(a)
    seq_b = _tool_sequence(b)

    # Find longest common subsequence length
    lcs_len = _lcs_length(seq_a, seq_b)

    return {
        "run_a_sequence": seq_a,
        "run_b_sequence": seq_b,
        "sequences_identical": seq_a == seq_b,
        "common_subsequence_length": lcs_len,
        "similarity": round(lcs_len / max(len(seq_a), len(seq_b), 1), 2),
    }


def _compare_environments(a: dict, b: dict) -> dict:
    snap_a = a.get("final_snapshot") or {}
    snap_b = b.get("final_snapshot") or {}

    if not snap_a and not snap_b:
        return {"available": False}

    result: dict[str, Any] = {"available": True}

    # Compare filesystems
    fs_a = set(snap_a.get("filesystem", {}).keys())
    fs_b = set(snap_b.get("filesystem", {}).keys())
    result["filesystem"] = {
        "only_in_a": sorted(fs_a - fs_b),
        "only_in_b": sorted(fs_b - fs_a),
        "common": sorted(fs_a & fs_b),
        "content_differs": [
            f for f in (fs_a & fs_b)
            if snap_a.get("filesystem", {}).get(f) != snap_b.get("filesystem", {}).get(f)
        ],
    }

    # Compare database tables
    db_a = set(snap_a.get("database", {}).keys())
    db_b = set(snap_b.get("database", {}).keys())
    result["database"] = {
        "only_in_a": sorted(db_a - db_b),
        "only_in_b": sorted(db_b - db_a),
        "common": sorted(db_a & db_b),
        "row_count_diff": {
            t: len(snap_b.get("database", {}).get(t, [])) - len(snap_a.get("database", {}).get(t, []))
            for t in (db_a & db_b)
        },
    }

    # Compare emails
    emails_a = snap_a.get("emails_sent", [])
    emails_b = snap_b.get("emails_sent", [])
    result["emails"] = {
        "run_a_count": len(emails_a),
        "run_b_count": len(emails_b),
    }

    return result


def _generate_summary(a: dict, b: dict) -> list[str]:
    """Generate human-readable summary of key differences."""
    points: list[str] = []
    actions_a = len(a.get("actions", []))
    actions_b = len(b.get("actions", []))

    if actions_a != actions_b:
        points.append(f"Run B used {actions_b} actions vs Run A's {actions_a} ({'+' if actions_b > actions_a else ''}{actions_b - actions_a}).")

    ra = a.get("risk_report") or {}
    rb = b.get("risk_report") or {}
    score_a = ra.get("overall_score", 0)
    score_b = rb.get("overall_score", 0)
    if score_a != score_b:
        direction = "higher" if score_b > score_a else "lower"
        points.append(f"Run B risk score is {direction}: {score_b} vs {score_a}.")

    if ra.get("risk_level") != rb.get("risk_level"):
        points.append(f"Risk level changed from {ra.get('risk_level', 'unknown')} to {rb.get('risk_level', 'unknown')}.")

    status_a = a.get("status")
    status_b = b.get("status")
    if status_a != status_b:
        points.append(f"Status differs: Run A is {status_a}, Run B is {status_b}.")

    diffs_a = len(a.get("diffs", []))
    diffs_b = len(b.get("diffs", []))
    if diffs_a != diffs_b:
        points.append(f"Run B made {diffs_b} state changes vs Run A's {diffs_a}.")

    if not points:
        points.append("Both runs are very similar in behavior, risk, and outcomes.")

    return points


def _lcs_length(a: list, b: list) -> int:
    """Compute length of longest common subsequence."""
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0
    # Use space-optimized DP
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[n]
