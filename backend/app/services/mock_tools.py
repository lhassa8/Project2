"""Tool schemas for the Claude tool-use API.

Defines the JSON schemas that Claude uses to understand available tools.
Actual tool execution is handled by SandboxEnvironment — these schemas
are the contract between Claude and the sandbox.
"""

from __future__ import annotations

# Claude tool-use JSON schemas for each sandbox tool
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
