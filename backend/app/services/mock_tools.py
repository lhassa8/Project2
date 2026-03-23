"""Mock MCP tool implementations.

Each tool function accepts the tool-call arguments from Claude and returns a
realistic synthetic response plus any state diffs produced.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import string
import uuid
from typing import Any

from ..models import StateDiff

# ── Helpers ──────────────────────────────────────────────────────────────────

_FILE_TEMPLATES: dict[str, str] = {
    ".py": '"""Auto-generated module."""\n\ndef main():\n    print("Hello from {name}")\n\nif __name__ == "__main__":\n    main()\n',
    ".json": '{{\n  "name": "{name}",\n  "version": "1.0.0",\n  "description": "Configuration file"\n}}',
    ".csv": "id,name,email,created_at\n1,Alice,alice@example.com,2025-01-15\n2,Bob,bob@corp.io,2025-02-20\n3,Carol,carol@org.net,2025-03-10\n",
    ".md": "# {name}\n\nThis is the documentation for {name}.\n\n## Getting Started\n\nFollow the setup instructions below.\n",
    ".txt": "Contents of {name}\n\nLorem ipsum dolor sit amet, consectetur adipiscing elit.\nSed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n",
}

_HTTP_RESPONSE_TEMPLATES: dict[str, dict] = {
    "api": {"status": 200, "body": {"data": [{"id": 1, "name": "Sample Item"}], "meta": {"page": 1, "total": 42}}},
    "auth": {"status": 200, "body": {"access_token": "mock_tok_" + uuid.uuid4().hex[:16], "expires_in": 3600}},
    "webhook": {"status": 202, "body": {"received": True, "id": uuid.uuid4().hex[:8]}},
    "graphql": {"status": 200, "body": {"data": {"viewer": {"login": "sandbox-user", "name": "Sandbox User"}}}},
}

_SQL_TABLES: dict[str, list[dict]] = {
    "users": [
        {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "admin"},
        {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "editor"},
        {"id": 3, "name": "Carol White", "email": "carol@example.com", "role": "viewer"},
    ],
    "orders": [
        {"id": 101, "user_id": 1, "total": 249.99, "status": "shipped"},
        {"id": 102, "user_id": 2, "total": 89.50, "status": "pending"},
        {"id": 103, "user_id": 3, "total": 1200.00, "status": "delivered"},
    ],
    "products": [
        {"id": 1, "name": "Widget Pro", "price": 49.99, "stock": 150},
        {"id": 2, "name": "Gadget Plus", "price": 129.99, "stock": 42},
        {"id": 3, "name": "Thingamajig", "price": 9.99, "stock": 500},
    ],
}


def _ext(path: str) -> str:
    idx = path.rfind(".")
    return path[idx:] if idx != -1 else ".txt"


def _filename(path: str) -> str:
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def _random_id(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


# ── Tool implementations ────────────────────────────────────────────────────

def read_file(path: str, **_: Any) -> tuple[dict, list[StateDiff]]:
    """Return synthetic file content based on extension/path heuristics."""
    ext = _ext(path)
    name = _filename(path)
    template = _FILE_TEMPLATES.get(ext, _FILE_TEMPLATES[".txt"])
    content = template.format(name=name)
    return {"path": path, "content": content, "size": len(content)}, []


def write_file(path: str, content: str, **_: Any) -> tuple[dict, list[StateDiff]]:
    """Record a file write without touching the real filesystem."""
    diff = StateDiff(
        system="filesystem",
        resource_id=path,
        before=None,
        after=content,
        change_type="created",
    )
    return {
        "path": path,
        "bytes_written": len(content),
        "success": True,
    }, [diff]


def send_email(to: str, subject: str, body: str, **_: Any) -> tuple[dict, list[StateDiff]]:
    """Record an email send and return a fake message ID."""
    msg_id = f"msg_{_random_id(12)}"
    diff = StateDiff(
        system="email",
        resource_id=to,
        before=None,
        after={"to": to, "subject": subject, "body": body, "message_id": msg_id},
        change_type="created",
    )
    return {
        "message_id": msg_id,
        "status": "sent",
        "to": to,
        "subject": subject,
    }, [diff]


def http_request(method: str, url: str, body: Any = None, **_: Any) -> tuple[dict, list[StateDiff]]:
    """Return a plausible mock HTTP response based on URL patterns."""
    url_lower = url.lower()
    if "auth" in url_lower or "token" in url_lower or "login" in url_lower:
        template = _HTTP_RESPONSE_TEMPLATES["auth"]
    elif "graphql" in url_lower:
        template = _HTTP_RESPONSE_TEMPLATES["graphql"]
    elif "webhook" in url_lower or "hook" in url_lower:
        template = _HTTP_RESPONSE_TEMPLATES["webhook"]
    else:
        template = _HTTP_RESPONSE_TEMPLATES["api"]

    resp = {
        "status_code": template["status"],
        "headers": {"content-type": "application/json", "x-request-id": _random_id()},
        "body": template["body"],
    }

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


def query_database(query: str, **_: Any) -> tuple[dict, list[StateDiff]]:
    """Parse SQL query and return synthetic tabular results."""
    q = query.lower().strip()

    # Detect table name
    table_name = None
    for t in _SQL_TABLES:
        if t in q:
            table_name = t
            break

    if table_name is None:
        table_name = list(_SQL_TABLES.keys())[0]

    rows = _SQL_TABLES[table_name]

    # Handle SELECT vs INSERT/UPDATE/DELETE
    diffs: list[StateDiff] = []
    if q.startswith("select"):
        # Apply simple WHERE id = N filtering
        match = re.search(r"where\s+id\s*=\s*(\d+)", q)
        if match:
            target_id = int(match.group(1))
            rows = [r for r in rows if r.get("id") == target_id]

        # Apply LIMIT
        limit_match = re.search(r"limit\s+(\d+)", q)
        if limit_match:
            rows = rows[: int(limit_match.group(1))]

        return {
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
            "row_count": len(rows),
        }, []

    elif q.startswith("insert"):
        new_id = max(r["id"] for r in rows) + 1 if rows else 1
        diffs.append(StateDiff(
            system="database",
            resource_id=f"{table_name}/id={new_id}",
            before=None,
            after={"query": query, "generated_id": new_id},
            change_type="created",
        ))
        return {"affected_rows": 1, "generated_id": new_id}, diffs

    elif q.startswith("update"):
        diffs.append(StateDiff(
            system="database",
            resource_id=table_name,
            before={"note": "existing rows before update"},
            after={"query": query, "affected_rows": 1},
            change_type="modified",
        ))
        return {"affected_rows": 1}, diffs

    elif q.startswith("delete"):
        diffs.append(StateDiff(
            system="database",
            resource_id=table_name,
            before={"note": "rows before deletion"},
            after={"query": query, "affected_rows": 1},
            change_type="deleted",
        ))
        return {"affected_rows": 1}, diffs

    return {"columns": [], "rows": [], "row_count": 0, "note": "Unrecognized query type"}, []


# ── Registry ─────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, callable] = {
    "read_file": read_file,
    "write_file": write_file,
    "send_email": send_email,
    "http_request": http_request,
    "query_database": query_database,
}

# Claude tool-use JSON schemas for each mock tool
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path to read"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to the specified recipient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "http_request",
        "description": "Make an HTTP request to a URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE)"},
                "url": {"type": "string", "description": "Target URL"},
                "body": {"description": "Request body (for POST/PUT)"},
            },
            "required": ["method", "url"],
        },
    },
    {
        "name": "query_database",
        "description": "Execute a SQL query against the database.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "SQL query to execute"}},
            "required": ["query"],
        },
    },
]
