"""Stateful sandbox environments with configurable seed data.

Provides a SandboxEnvironment that holds in-memory state (filesystem,
database tables, HTTP response stubs) so that mock tools read/write against
a realistic, user-configured world instead of static templates.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from ..models import StateDiff


class SandboxEnvironment:
    """In-memory simulated environment for a single sandbox run.

    Users seed the environment with files, DB tables, and HTTP stubs.
    Mock tools operate against this state, producing realistic, consistent
    results across the run.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.filesystem: dict[str, str] = dict(config.get("filesystem", {}))
        self.database: dict[str, list[dict]] = {
            k: [dict(row) for row in v]
            for k, v in config.get("database", {}).items()
        }
        self.http_stubs: list[HttpStub] = [
            HttpStub(**s) for s in config.get("http_stubs", [])
        ]
        self.emails_sent: list[dict] = []
        self.http_log: list[dict] = []
        # Auto-increment counters per DB table
        self._db_sequences: dict[str, int] = {}
        for table, rows in self.database.items():
            max_id = max((r.get("id", 0) for r in rows), default=0)
            self._db_sequences[table] = max_id + 1

    def to_snapshot(self) -> dict:
        """Serialize current state for comparison/export."""
        return {
            "filesystem": dict(self.filesystem),
            "database": {k: [dict(r) for r in v] for k, v in self.database.items()},
            "emails_sent": list(self.emails_sent),
            "http_log": list(self.http_log),
        }

    # ── File operations ─────────────────────────────────────────────────

    def read_file(self, path: str) -> tuple[dict, list[StateDiff]]:
        if path in self.filesystem:
            content = self.filesystem[path]
            return {"path": path, "content": content, "size": len(content)}, []
        return {
            "path": path,
            "error": f"File not found: {path}",
            "exists": False,
        }, []

    def write_file(self, path: str, content: str) -> tuple[dict, list[StateDiff]]:
        before = self.filesystem.get(path)
        self.filesystem[path] = content
        change_type = "modified" if before is not None else "created"
        diff = StateDiff(
            system="filesystem",
            resource_id=path,
            before=before,
            after=content,
            change_type=change_type,
        )
        return {
            "path": path,
            "bytes_written": len(content),
            "success": True,
        }, [diff]

    # ── Email operations ────────────────────────────────────────────────

    def send_email(self, to: str, subject: str, body: str) -> tuple[dict, list[StateDiff]]:
        import uuid
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        record = {
            "message_id": msg_id,
            "to": to,
            "subject": subject,
            "body": body,
        }
        self.emails_sent.append(record)
        diff = StateDiff(
            system="email",
            resource_id=to,
            before=None,
            after=record,
            change_type="created",
        )
        return {
            "message_id": msg_id,
            "status": "sent",
            "to": to,
            "subject": subject,
        }, [diff]

    # ── HTTP operations ─────────────────────────────────────────────────

    def http_request(self, method: str, url: str, body: Any = None) -> tuple[dict, list[StateDiff]]:
        # Check stubs first
        for stub in self.http_stubs:
            if stub.matches(method, url):
                resp = stub.response()
                self.http_log.append({"method": method, "url": url, "body": body, "response": resp})
                diffs: list[StateDiff] = []
                if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
                    diffs.append(StateDiff(
                        system="http",
                        resource_id=url,
                        before=None,
                        after={"method": method, "url": url, "request_body": body, "response": resp},
                        change_type="created",
                    ))
                return resp, diffs

        # Default fallback for unstubbed URLs
        resp = _default_http_response(method, url, body)
        self.http_log.append({"method": method, "url": url, "body": body, "response": resp})
        diffs = []
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            diffs.append(StateDiff(
                system="http",
                resource_id=url,
                before=None,
                after={"method": method, "url": url, "request_body": body, "response": resp},
                change_type="created",
            ))
        return resp, diffs

    # ── Database operations ─────────────────────────────────────────────

    def query_database(self, query: str) -> tuple[dict, list[StateDiff]]:
        q = query.strip()
        ql = q.lower()

        # Detect table name
        table_name = self._detect_table(ql)

        if ql.startswith("select"):
            return self._handle_select(ql, table_name)
        elif ql.startswith("insert"):
            return self._handle_insert(q, ql, table_name)
        elif ql.startswith("update"):
            return self._handle_update(q, ql, table_name)
        elif ql.startswith("delete"):
            return self._handle_delete(q, ql, table_name)
        else:
            return {"columns": [], "rows": [], "row_count": 0, "note": "Unrecognized query type"}, []

    def _detect_table(self, ql: str) -> str | None:
        for t in self.database:
            if t in ql:
                return t
        # Try to parse FROM/INTO/UPDATE clause
        m = re.search(r"(?:from|into|update|table)\s+(\w+)", ql)
        if m and m.group(1) in self.database:
            return m.group(1)
        return None

    def _handle_select(self, ql: str, table_name: str | None) -> tuple[dict, list[StateDiff]]:
        if table_name is None or table_name not in self.database:
            return {"columns": [], "rows": [], "row_count": 0, "note": f"Table not found"}, []

        rows = [dict(r) for r in self.database[table_name]]

        # Simple WHERE filtering
        where_match = re.search(r"where\s+(.+?)(?:\s+order|\s+limit|\s+group|\s*$)", ql)
        if where_match:
            rows = self._apply_where(rows, where_match.group(1))

        # ORDER BY
        order_match = re.search(r"order\s+by\s+(\w+)(?:\s+(asc|desc))?", ql)
        if order_match:
            col = order_match.group(1)
            desc = order_match.group(2) == "desc" if order_match.group(2) else False
            rows.sort(key=lambda r: r.get(col, ""), reverse=desc)

        # LIMIT
        limit_match = re.search(r"limit\s+(\d+)", ql)
        if limit_match:
            rows = rows[:int(limit_match.group(1))]

        return {
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
            "row_count": len(rows),
        }, []

    def _apply_where(self, rows: list[dict], clause: str) -> list[dict]:
        """Apply simple WHERE conditions (col = val, col > val, AND)."""
        conditions = re.split(r"\s+and\s+", clause)
        result = rows
        for cond in conditions:
            m = re.match(r"(\w+)\s*(=|!=|>|<|>=|<=|like)\s*['\"]?([^'\"]+?)['\"]?\s*$", cond.strip())
            if not m:
                continue
            col, op, val = m.group(1), m.group(2), m.group(3)
            result = [r for r in result if self._eval_condition(r.get(col), op, val)]
        return result

    @staticmethod
    def _eval_condition(field_val: Any, op: str, val: str) -> bool:
        if field_val is None:
            return False
        # Try numeric comparison
        try:
            fv = float(field_val)
            v = float(val)
            if op == "=":
                return fv == v
            elif op == "!=":
                return fv != v
            elif op == ">":
                return fv > v
            elif op == "<":
                return fv < v
            elif op == ">=":
                return fv >= v
            elif op == "<=":
                return fv <= v
        except (ValueError, TypeError):
            pass

        sv = str(field_val).lower()
        val_lower = val.lower()
        if op == "=":
            return sv == val_lower
        elif op == "!=":
            return sv != val_lower
        elif op == "like":
            pattern = val_lower.replace("%", ".*").replace("_", ".")
            return bool(re.match(f"^{pattern}$", sv))
        return False

    def _handle_insert(self, q: str, ql: str, table_name: str | None) -> tuple[dict, list[StateDiff]]:
        if table_name is None:
            table_name = "default"
        if table_name not in self.database:
            self.database[table_name] = []
            self._db_sequences[table_name] = 1

        new_id = self._db_sequences[table_name]
        self._db_sequences[table_name] += 1

        # Try to parse column values from INSERT
        new_row = {"id": new_id}
        cols_match = re.search(r"\(([^)]+)\)\s*values\s*\(([^)]+)\)", ql)
        if cols_match:
            cols = [c.strip() for c in cols_match.group(1).split(",")]
            vals = [v.strip().strip("'\"") for v in cols_match.group(2).split(",")]
            for c, v in zip(cols, vals):
                if c != "id":
                    new_row[c] = v

        self.database[table_name].append(new_row)
        diff = StateDiff(
            system="database",
            resource_id=f"{table_name}/id={new_id}",
            before=None,
            after=new_row,
            change_type="created",
        )
        return {"affected_rows": 1, "generated_id": new_id}, [diff]

    def _handle_update(self, q: str, ql: str, table_name: str | None) -> tuple[dict, list[StateDiff]]:
        if table_name is None or table_name not in self.database:
            return {"affected_rows": 0, "note": "Table not found"}, []

        rows = self.database[table_name]
        # Parse SET clause
        set_match = re.search(r"set\s+(.+?)(?:\s+where|$)", ql)
        where_match = re.search(r"where\s+(.+)$", ql)

        updates = {}
        if set_match:
            for pair in set_match.group(1).split(","):
                kv = pair.strip().split("=", 1)
                if len(kv) == 2:
                    updates[kv[0].strip()] = kv[1].strip().strip("'\"")

        affected = 0
        diffs: list[StateDiff] = []
        for row in rows:
            if where_match:
                if not self._apply_where([row], where_match.group(1)):
                    continue
            before = dict(row)
            for k, v in updates.items():
                row[k] = v
            affected += 1
            diffs.append(StateDiff(
                system="database",
                resource_id=f"{table_name}/id={row.get('id', '?')}",
                before=before,
                after=dict(row),
                change_type="modified",
            ))

        return {"affected_rows": affected}, diffs

    def _handle_delete(self, q: str, ql: str, table_name: str | None) -> tuple[dict, list[StateDiff]]:
        if table_name is None or table_name not in self.database:
            return {"affected_rows": 0, "note": "Table not found"}, []

        where_match = re.search(r"where\s+(.+)$", ql)
        rows = self.database[table_name]
        to_delete = rows if not where_match else self._apply_where(rows, where_match.group(1))

        diffs: list[StateDiff] = []
        for row in to_delete:
            diffs.append(StateDiff(
                system="database",
                resource_id=f"{table_name}/id={row.get('id', '?')}",
                before=dict(row),
                after={"deleted": True},
                change_type="deleted",
            ))

        self.database[table_name] = [r for r in rows if r not in to_delete]
        return {"affected_rows": len(to_delete)}, diffs


class HttpStub:
    """A configurable HTTP response stub for the sandbox."""

    def __init__(
        self,
        url_pattern: str,
        method: str = "*",
        status_code: int = 200,
        response_body: Any = None,
        response_headers: dict[str, str] | None = None,
    ):
        self.url_pattern = url_pattern
        self.method = method.upper()
        self.status_code = status_code
        self.response_body = response_body or {"status": "ok"}
        self.response_headers = response_headers or {"content-type": "application/json"}

    def matches(self, method: str, url: str) -> bool:
        if self.method != "*" and self.method != method.upper():
            return False
        try:
            return bool(re.search(self.url_pattern, url, re.IGNORECASE))
        except re.error:
            return self.url_pattern in url

    def response(self) -> dict:
        return {
            "status_code": self.status_code,
            "headers": dict(self.response_headers),
            "body": copy.deepcopy(self.response_body),
        }


def _default_http_response(method: str, url: str, body: Any) -> dict:
    """Fallback for URLs with no stub configured."""
    import uuid
    url_lower = url.lower()
    if "auth" in url_lower or "token" in url_lower or "login" in url_lower:
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"access_token": f"mock_tok_{uuid.uuid4().hex[:16]}", "expires_in": 3600},
        }
    elif "graphql" in url_lower:
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"data": {"viewer": {"login": "sandbox-user", "name": "Sandbox User"}}},
        }
    elif "webhook" in url_lower or "hook" in url_lower:
        return {
            "status_code": 202,
            "headers": {"content-type": "application/json"},
            "body": {"received": True, "id": uuid.uuid4().hex[:8]},
        }
    else:
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"data": [{"id": 1, "name": "Sample Item"}], "meta": {"page": 1, "total": 42}},
        }


# ── Default environment configs for templates ───────────────────────────

DEFAULT_ENVIRONMENTS: dict[str, dict] = {
    "crm-lead-enrichment": {
        "filesystem": {},
        "database": {
            "leads": [
                {"id": 1, "company": "Acme Corp", "email": "jane@acme.com", "enriched": False, "source": "website"},
                {"id": 2, "company": "TechStart Inc", "email": "bob@techstart.io", "enriched": True, "source": "referral"},
            ],
            "interactions": [
                {"id": 1, "company": "Acme Corp", "type": "website_visit", "date": "2025-01-10", "notes": "Viewed pricing page"},
                {"id": 2, "company": "Acme Corp", "type": "demo_request", "date": "2025-01-12", "notes": "Requested enterprise demo"},
            ],
        },
        "http_stubs": [
            {
                "url_pattern": "clearbit.com",
                "method": "GET",
                "status_code": 200,
                "response_body": {
                    "name": "Acme Corp",
                    "domain": "acme.com",
                    "category": {"sector": "Technology"},
                    "metrics": {"employees": 500, "raised": 50000000},
                    "location": "San Francisco, CA",
                },
            },
        ],
    },
    "incident-response": {
        "filesystem": {
            "/var/log/payment-service/error.log": (
                "[2025-01-20 14:32:01] ERROR PaymentProcessor: Connection timeout to payment gateway\n"
                "[2025-01-20 14:32:15] ERROR PaymentProcessor: HTTP 503 from gateway.stripe.internal\n"
                "[2025-01-20 14:32:30] ERROR PaymentProcessor: Circuit breaker OPEN - failing fast\n"
                "[2025-01-20 14:33:01] WARN  HealthCheck: Payment service unhealthy - 3 consecutive failures\n"
                "[2025-01-20 14:33:15] ERROR PaymentProcessor: Connection timeout to payment gateway\n"
                "[2025-01-20 14:34:00] FATAL PaymentService: Too many errors, entering degraded mode\n"
            ),
        },
        "database": {
            "request_logs": [
                {"id": 1, "service": "payment", "status_code": 500, "timestamp": "2025-01-20T14:32:01", "path": "/api/charge", "count": 142},
                {"id": 2, "service": "payment", "status_code": 503, "timestamp": "2025-01-20T14:32:15", "path": "/api/charge", "count": 89},
                {"id": 3, "service": "payment", "status_code": 200, "timestamp": "2025-01-20T14:30:00", "path": "/api/charge", "count": 1203},
            ],
            "deployments": [
                {"id": 1, "service": "payment", "version": "2.4.1", "deployed_at": "2025-01-20T13:45:00", "deployer": "ci-bot", "status": "success"},
                {"id": 2, "service": "payment", "version": "2.4.0", "deployed_at": "2025-01-19T10:00:00", "deployer": "alice", "status": "success"},
            ],
        },
        "http_stubs": [
            {
                "url_pattern": "deploy.internal.corp.com",
                "method": "GET",
                "status_code": 200,
                "response_body": {
                    "deployments": [
                        {"version": "2.4.1", "deployed_at": "2025-01-20T13:45:00", "commit": "abc123f", "deployer": "ci-bot"},
                        {"version": "2.4.0", "deployed_at": "2025-01-19T10:00:00", "commit": "def456a", "deployer": "alice"},
                    ]
                },
            },
        ],
    },
    "security-access-review": {
        "filesystem": {
            "/policies/access-control-policy.md": (
                "# Access Control Policy v2.3\n\n"
                "## Principles\n"
                "1. Least privilege: Users should only have access to resources required for their role.\n"
                "2. Regular review: All elevated permissions must be reviewed quarterly.\n"
                "3. Separation of duties: No single user should have both create and approve privileges.\n\n"
                "## Elevated Access Requirements\n"
                "- Admin access requires manager approval and security team sign-off.\n"
                "- Superadmin access restricted to SRE team leads only.\n"
                "- All admin sessions must be logged and auditable.\n"
            ),
        },
        "database": {
            "users": [
                {"id": 1, "name": "Alice Johnson", "email": "alice@corp.com", "role": "admin", "last_login": "2025-01-18", "department": "Engineering"},
                {"id": 2, "name": "Bob Smith", "email": "bob@corp.com", "role": "editor", "last_login": "2025-01-20", "department": "Marketing"},
                {"id": 3, "name": "Carol White", "email": "carol@corp.com", "role": "viewer", "last_login": "2024-11-05", "department": "Sales"},
                {"id": 4, "name": "Dave Brown", "email": "dave@corp.com", "role": "admin", "last_login": "2025-01-19", "department": "SRE"},
                {"id": 5, "name": "Eve Davis", "email": "eve@corp.com", "role": "superadmin", "last_login": "2025-01-20", "department": "SRE"},
                {"id": 6, "name": "Frank Wilson", "email": "frank@corp.com", "role": "admin", "last_login": "2024-09-15", "department": "Finance"},
            ],
            "permissions": [
                {"id": 1, "user_id": 1, "level": "admin", "resource": "production-db", "granted_at": "2024-06-01", "granted_by": "eve@corp.com"},
                {"id": 2, "user_id": 4, "level": "admin", "resource": "infrastructure", "granted_at": "2024-03-15", "granted_by": "eve@corp.com"},
                {"id": 3, "user_id": 5, "level": "superadmin", "resource": "*", "granted_at": "2024-01-01", "granted_by": "cto@corp.com"},
                {"id": 4, "user_id": 6, "level": "admin", "resource": "finance-systems", "granted_at": "2024-04-10", "granted_by": "cfo@corp.com"},
            ],
        },
        "http_stubs": [
            {
                "url_pattern": "identity.internal.corp.com/api/users",
                "method": "GET",
                "status_code": 200,
                "response_body": {
                    "disabled_accounts": [
                        {"email": "former.employee@corp.com", "disabled_at": "2024-12-01", "reason": "termination"},
                        {"email": "contractor.temp@corp.com", "disabled_at": "2025-01-05", "reason": "contract_ended"},
                    ]
                },
            },
        ],
    },
}
