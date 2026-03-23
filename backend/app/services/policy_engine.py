"""Policy engine — configurable rules that auto-flag or block agent actions.

Policies are evaluated in real-time as the agent executes. Each policy can:
- WARN: flag the action but let it continue
- BLOCK: stop the action and fail the run
- REQUIRE_APPROVAL: pause and require human approval before continuing

Ships with sensible enterprise defaults.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyViolation:
    policy_name: str
    policy_action: PolicyAction
    description: str
    action_sequence: int | None = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "policy_name": self.policy_name,
            "policy_action": self.policy_action.value,
            "description": self.description,
            "action_sequence": self.action_sequence,
            "details": self.details,
        }


@dataclass
class Policy:
    name: str
    description: str
    enabled: bool = True
    action: PolicyAction = PolicyAction.WARN

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        raise NotImplementedError


# ── Built-in policies ────────────────────────────────────────────────────────

class NoProductionAccessPolicy(Policy):
    """Block access to production systems."""

    def __init__(self):
        super().__init__(
            name="no_production_access",
            description="Block file access and HTTP requests to production systems",
            action=PolicyAction.BLOCK,
        )
        self._patterns = [
            r"prod(?:uction)?[./\\-]",
            r"\.prod\.",
            r"prod\..*\.com",
            r"/prod/",
        ]

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        text = ""
        if tool_name == "read_file" or tool_name == "write_file":
            text = args.get("path", "")
        elif tool_name == "http_request":
            text = args.get("url", "")
        elif tool_name == "query_database":
            text = args.get("query", "")

        for pat in self._patterns:
            if re.search(pat, text, re.IGNORECASE):
                return PolicyViolation(
                    policy_name=self.name,
                    policy_action=self.action,
                    description=f"Production system access detected: {text[:100]}",
                    details={"pattern_matched": pat, "target": text},
                )
        return None


class MaxEmailRecipientsPolicy(Policy):
    """Limit the number of email recipients per send."""

    def __init__(self, max_recipients: int = 5):
        super().__init__(
            name="max_email_recipients",
            description=f"Limit emails to {max_recipients} recipients",
            action=PolicyAction.BLOCK,
        )
        self.max_recipients = max_recipients

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        if tool_name != "send_email":
            return None
        to = args.get("to", "")
        recipients = [r.strip() for r in re.split(r"[,;]", to) if r.strip()]
        if len(recipients) > self.max_recipients:
            return PolicyViolation(
                policy_name=self.name,
                policy_action=self.action,
                description=f"Email to {len(recipients)} recipients exceeds limit of {self.max_recipients}",
                details={"recipient_count": len(recipients), "limit": self.max_recipients},
            )
        return None


class NoDangerousSQLPolicy(Policy):
    """Block destructive SQL operations."""

    def __init__(self):
        super().__init__(
            name="no_dangerous_sql",
            description="Block DROP, TRUNCATE, and unscoped DELETE/UPDATE queries",
            action=PolicyAction.BLOCK,
        )
        self._patterns = [
            (r"\bDROP\s+(?:TABLE|DATABASE|INDEX)\b", "DROP statement"),
            (r"\bTRUNCATE\b", "TRUNCATE statement"),
            (r"\bDELETE\s+FROM\s+\w+\s*(?:;|$)", "DELETE without WHERE clause"),
        ]

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        if tool_name != "query_database":
            return None
        query = args.get("query", "")
        for pat, desc in self._patterns:
            if re.search(pat, query, re.IGNORECASE):
                return PolicyViolation(
                    policy_name=self.name,
                    policy_action=self.action,
                    description=f"Dangerous SQL detected: {desc}",
                    details={"query": query, "pattern": desc},
                )
        return None


class NoSensitiveFileAccessPolicy(Policy):
    """Warn when accessing sensitive file paths."""

    def __init__(self):
        super().__init__(
            name="no_sensitive_file_access",
            description="Warn on access to credential files, env files, and certificates",
            action=PolicyAction.WARN,
        )
        self._patterns = [
            (r"\.env(?:\.|$)", "environment file"),
            (r"(?:credential|secret|key)s?\.", "credentials file"),
            (r"\.pem$|\.key$|\.p12$|\.pfx$", "certificate/key file"),
            (r"(?:password|token|apikey)", "sensitive named file"),
        ]

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        if tool_name not in ("read_file", "write_file"):
            return None
        path = args.get("path", "")
        for pat, desc in self._patterns:
            if re.search(pat, path, re.IGNORECASE):
                return PolicyViolation(
                    policy_name=self.name,
                    policy_action=self.action,
                    description=f"Sensitive file access: {desc} ({path})",
                    details={"path": path, "file_type": desc},
                )
        return None


class MaxMutationsPolicy(Policy):
    """Limit total write operations per run."""

    def __init__(self, max_mutations: int = 20):
        super().__init__(
            name="max_mutations_per_run",
            description=f"Limit to {max_mutations} write operations per run",
            action=PolicyAction.REQUIRE_APPROVAL,
        )
        self.max_mutations = max_mutations
        self._count = 0

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        write_tools = {"write_file", "send_email"}
        write_methods = {"POST", "PUT", "PATCH", "DELETE"}

        is_write = tool_name in write_tools
        if tool_name == "http_request":
            is_write = args.get("method", "GET").upper() in write_methods
        if tool_name == "query_database":
            q = args.get("query", "").strip().lower()
            is_write = not q.startswith("select")

        if is_write:
            self._count += 1
            if self._count > self.max_mutations:
                return PolicyViolation(
                    policy_name=self.name,
                    policy_action=self.action,
                    description=f"Mutation count ({self._count}) exceeds limit ({self.max_mutations})",
                    details={"count": self._count, "limit": self.max_mutations},
                )
        return None


class NoExternalHTTPPolicy(Policy):
    """Warn on HTTP requests to external/unknown domains."""

    def __init__(self, allowed_domains: list[str] | None = None):
        super().__init__(
            name="no_external_http",
            description="Warn on HTTP requests to non-allowlisted domains",
            action=PolicyAction.WARN,
        )
        self.allowed_domains = allowed_domains or ["localhost", "127.0.0.1", "internal.corp.com"]

    def evaluate(self, tool_name: str, args: dict) -> PolicyViolation | None:
        if tool_name != "http_request":
            return None
        url = args.get("url", "")
        domain_match = re.search(r"://([^/:]+)", url)
        if not domain_match:
            return None
        domain = domain_match.group(1).lower()
        if not any(d in domain for d in self.allowed_domains):
            return PolicyViolation(
                policy_name=self.name,
                policy_action=self.action,
                description=f"External HTTP request to {domain}",
                details={"url": url, "domain": domain, "allowed": self.allowed_domains},
            )
        return None


# ── Policy engine ────────────────────────────────────────────────────────────

class PolicyEngine:
    """Evaluates all active policies against an action."""

    def __init__(self, policies: list[Policy] | None = None):
        if policies is None:
            policies = self.default_policies()
        self.policies = policies

    @staticmethod
    def default_policies() -> list[Policy]:
        return [
            NoProductionAccessPolicy(),
            MaxEmailRecipientsPolicy(),
            NoDangerousSQLPolicy(),
            NoSensitiveFileAccessPolicy(),
            MaxMutationsPolicy(),
            NoExternalHTTPPolicy(),
        ]

    def evaluate(self, tool_name: str, args: dict, sequence: int | None = None) -> list[PolicyViolation]:
        violations = []
        for policy in self.policies:
            if not policy.enabled:
                continue
            v = policy.evaluate(tool_name, args)
            if v is not None:
                v.action_sequence = sequence
                violations.append(v)
        return violations

    def has_blockers(self, violations: list[PolicyViolation]) -> bool:
        return any(
            v.policy_action in (PolicyAction.BLOCK, PolicyAction.REQUIRE_APPROVAL)
            for v in violations
        )

    def get_policy_config(self) -> list[dict]:
        return [
            {
                "name": p.name,
                "description": p.description,
                "enabled": p.enabled,
                "action": p.action.value,
            }
            for p in self.policies
        ]
