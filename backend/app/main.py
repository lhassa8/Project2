"""AgentSandbox — FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .middleware import ErrorHandlingMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from .routers import analytics, audit, mcp, policies, runs, templates, webhooks, workspaces

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="AgentSandbox",
    description=(
        "Enterprise simulation layer for previewing, debugging, and approving "
        "autonomous Claude agent actions before granting real-system access. "
        "Features stateful sandbox environments, MCP-compatible server, "
        "workspace-scoped auth, run comparison, approval-gated replay, "
        "audit logging, webhook notifications, and configurable policies."
    ),
    version="1.0.0",
)

# Middleware stack (order matters — outermost runs first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimitMiddleware, read_limit=100, write_limit=30, window=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(templates.router)
app.include_router(analytics.router)
app.include_router(policies.router)
app.include_router(workspaces.router)
app.include_router(mcp.router)
app.include_router(audit.router)
app.include_router(webhooks.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AgentSandbox", "version": "1.0.0"}
