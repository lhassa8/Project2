"""AgentSandbox — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import analytics, audit, mcp, policies, runs, templates, webhooks, workspaces

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
