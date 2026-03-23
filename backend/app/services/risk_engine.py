"""Risk scoring engine — automatically assesses danger level of agent actions.

Scores each action on a 0-100 scale across multiple dimensions:
- Data sensitivity (PII, credentials, financial data)
- Blast radius (number of systems affected, write vs read)
- Reversibility (can the action be undone?)
- Privilege escalation (auth tokens, admin operations)
- External exposure (emails sent, HTTP calls to external services)

Produces per-action scores and an aggregate run risk profile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskSignal:
    category: str
    description: str
    severity: int  # 0-100
    action_sequence: int | None = None


@dataclass
class RiskReport:
    overall_score: int
    risk_level: str  # "low", "medium", "high", "critical"
    signals: list[RiskSignal] = field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "signals": [
                {
                    "category": s.category,
                    "description": s.description,
                    "severity": s.severity,
                    "action_sequence": s.action_sequence,
                }
                for s in self.signals
            ],
            "summary": self.summary,
            "recommendations": self.recommendations,
        }


# ── Pattern matchers ─────────────────────────────────────────────────────────

_PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email address"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "credit card number"),
    (r"\b(?:password|passwd|secret|api_key|api[-_]?secret|token)\b", "credential keyword"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone number"),
]

_SENSITIVE_PATHS = [
    (r"\.env", "environment file", 80),
    (r"(?:credentials|secrets|keys)\.", "credentials file", 90),
    (r"/etc/(?:passwd|shadow|sudoers)", "system auth file", 95),
    (r"\.pem|\.key|\.crt|\.cert", "certificate/key file", 85),
    (r"config.*(?:prod|production)", "production config", 75),
    (r"(?:database|db).*(?:prod|production)", "production database config", 85),
]

_DANGEROUS_SQL = [
    (r"\bDROP\s+TABLE\b", "DROP TABLE", 95),
    (r"\bDROP\s+DATABASE\b", "DROP DATABASE", 100),
    (r"\bTRUNCATE\b", "TRUNCATE", 90),
    (r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)", "DELETE without WHERE", 85),
    (r"\bUPDATE\b(?!.*\bWHERE\b)", "UPDATE without WHERE", 80),
    (r"\bALTER\s+TABLE\b", "ALTER TABLE", 60),
    (r"\bGRANT\b|\bREVOKE\b", "permission change", 75),
]

_HIGH_RISK_URLS = [
    (r"(?:admin|management|internal)", "admin/internal endpoint", 70),
    (r"(?:payment|billing|stripe|paypal)", "payment system", 80),
    (r"(?:auth|oauth|token|login|session)", "authentication endpoint", 65),
    (r"(?:delete|remove|destroy|purge)", "destructive endpoint", 75),
    (r"(?:prod|production)\..*\.com", "production URL", 70),
]


def _scan_text(text: str, patterns: list[tuple], base_category: str) -> list[RiskSignal]:
    signals = []
    for pattern, name, *severity in patterns:
        sev = severity[0] if severity else 50
        if re.search(pattern, text, re.IGNORECASE):
            signals.append(RiskSignal(
                category=base_category,
                description=f"Detected {name}",
                severity=sev,
            ))
    return signals


def _scan_pii(text: str) -> list[RiskSignal]:
    signals = []
    for pattern, name in _PII_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            signals.append(RiskSignal(
                category="data_sensitivity",
                description=f"Contains {name} ({len(matches)} occurrence{'s' if len(matches) > 1 else ''})",
                severity=60 if name == "email address" else 80,
            ))
    return signals


# ── Main scoring function ────────────────────────────────────────────────────

def score_action(action: dict) -> list[RiskSignal]:
    """Score a single agent action for risk signals."""
    signals: list[RiskSignal] = []
    content = action.get("content", {})
    action_type = action.get("action_type", "")
    seq = action.get("sequence", 0)

    if action_type == "tool_call":
        tool = content.get("tool", "")
        args = content.get("arguments", {})

        if tool == "write_file":
            path = args.get("path", "")
            file_content = args.get("content", "")
            signals.append(RiskSignal("blast_radius", f"File write to {path}", 40, seq))
            signals.extend(s := _scan_text(path, _SENSITIVE_PATHS, "data_sensitivity"))
            for s_item in s:
                s_item.action_sequence = seq
            signals.extend(pii := _scan_pii(file_content))
            for p in pii:
                p.action_sequence = seq

        elif tool == "read_file":
            path = args.get("path", "")
            signals.extend(s := _scan_text(path, _SENSITIVE_PATHS, "data_sensitivity"))
            for s_item in s:
                s_item.action_sequence = seq
                s_item.severity = max(20, s_item.severity - 20)  # reads are less dangerous

        elif tool == "send_email":
            to = args.get("to", "")
            body = args.get("body", "")
            signals.append(RiskSignal("external_exposure", f"Email to {to}", 50, seq))
            signals.extend(pii := _scan_pii(body))
            for p in pii:
                p.action_sequence = seq
            # Multiple recipients
            if "," in to or ";" in to:
                signals.append(RiskSignal("blast_radius", "Email to multiple recipients", 60, seq))

        elif tool == "http_request":
            method = args.get("method", "GET").upper()
            url = args.get("url", "")
            body = args.get("body")

            if method in ("POST", "PUT", "PATCH", "DELETE"):
                signals.append(RiskSignal("blast_radius", f"{method} request to {url}", 45, seq))
            if method == "DELETE":
                signals.append(RiskSignal("reversibility", f"DELETE request (hard to undo)", 65, seq))

            signals.extend(s := _scan_text(url, _HIGH_RISK_URLS, "external_exposure"))
            for s_item in s:
                s_item.action_sequence = seq

            if body:
                signals.extend(pii := _scan_pii(str(body)))
                for p in pii:
                    p.action_sequence = seq

        elif tool == "query_database":
            query = args.get("query", "")
            signals.extend(s := _scan_text(query, _DANGEROUS_SQL, "blast_radius"))
            for s_item in s:
                s_item.action_sequence = seq
            signals.extend(pii := _scan_pii(query))
            for p in pii:
                p.action_sequence = seq

    elif action_type == "thought":
        text = content.get("text", "")
        # Flag if agent is reasoning about dangerous operations
        danger_words = ["delete all", "drop table", "override", "bypass", "escalat", "admin access"]
        for word in danger_words:
            if word in text.lower():
                signals.append(RiskSignal(
                    "privilege_escalation",
                    f"Agent reasoning about '{word}'",
                    55,
                    seq,
                ))

    return signals


def score_run(actions: list[dict], diffs: list[dict]) -> RiskReport:
    """Produce a full risk report for a completed sandbox run."""
    all_signals: list[RiskSignal] = []

    # Score each action
    for action in actions:
        all_signals.extend(score_action(action))

    # Score aggregate patterns
    write_count = sum(1 for a in actions if a.get("content", {}).get("tool") == "write_file")
    email_count = sum(1 for a in actions if a.get("content", {}).get("tool") == "send_email")
    http_mut_count = sum(
        1 for a in actions
        if a.get("content", {}).get("tool") == "http_request"
        and a.get("content", {}).get("arguments", {}).get("method", "GET").upper() in ("POST", "PUT", "DELETE")
    )
    db_mut_count = sum(
        1 for a in actions
        if a.get("content", {}).get("tool") == "query_database"
        and not a.get("content", {}).get("arguments", {}).get("query", "").strip().lower().startswith("select")
    )

    total_mutations = write_count + email_count + http_mut_count + db_mut_count
    if total_mutations > 5:
        all_signals.append(RiskSignal("blast_radius", f"High mutation count: {total_mutations} write operations", 60))
    if email_count > 3:
        all_signals.append(RiskSignal("external_exposure", f"Sending {email_count} emails in one run", 55))

    unique_systems = set()
    for d in diffs:
        unique_systems.add(d.get("system", "unknown"))
    if len(unique_systems) >= 3:
        all_signals.append(RiskSignal("blast_radius", f"Touches {len(unique_systems)} different systems", 50))

    # Compute overall score
    if not all_signals:
        overall = 0
    else:
        max_sev = max(s.severity for s in all_signals)
        avg_sev = sum(s.severity for s in all_signals) / len(all_signals)
        overall = int(0.6 * max_sev + 0.4 * avg_sev)

    if overall >= 80:
        level = "critical"
    elif overall >= 60:
        level = "high"
    elif overall >= 35:
        level = "medium"
    else:
        level = "low"

    # Generate recommendations
    recs: list[str] = []
    categories = set(s.category for s in all_signals)
    if "data_sensitivity" in categories:
        recs.append("Review all data access patterns — sensitive data detected in tool arguments or file paths.")
    if "blast_radius" in categories:
        recs.append("Consider narrowing tool permissions to reduce the scope of potential changes.")
    if "external_exposure" in categories:
        recs.append("Verify all external communications (emails, HTTP requests) are expected and authorized.")
    if "reversibility" in categories:
        recs.append("Some actions are difficult to reverse — ensure backups exist before approving.")
    if "privilege_escalation" in categories:
        recs.append("Agent showed signs of privilege escalation reasoning — review thought chain carefully.")
    if not recs:
        recs.append("No significant risks detected. Standard review recommended.")

    # Summary
    summary_parts = []
    if total_mutations > 0:
        summary_parts.append(f"{total_mutations} write operation{'s' if total_mutations > 1 else ''}")
    if len(unique_systems) > 0:
        summary_parts.append(f"{len(unique_systems)} system{'s' if len(unique_systems) > 1 else ''} affected")
    summary_parts.append(f"{len(all_signals)} risk signal{'s' if len(all_signals) != 1 else ''} found")
    summary = f"Risk assessment: {level.upper()} ({overall}/100). " + ", ".join(summary_parts) + "."

    return RiskReport(
        overall_score=overall,
        risk_level=level,
        signals=all_signals,
        summary=summary,
        recommendations=recs,
    )
