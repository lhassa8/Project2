# AgentSandbox

Enterprise simulation layer for previewing, debugging, and approving autonomous Claude agent actions before granting real-system access.

AgentSandbox intercepts every tool call an agent makes — file reads/writes, database queries, HTTP requests, emails — and routes them through a configurable in-memory environment. Teams review risk scores, approve behavior, and replay approved runs against production, all with full audit trails and webhook notifications.

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend proxies `/api` requests to the backend on port 8000.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript + Tailwind CSS + Vite)                │
│  Dashboard │ Runs │ Templates │ Compare │ Policies │ Audit │ Hooks  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST + WebSocket
┌──────────────────────────────▼──────────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy + SQLite)                             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Auth Layer   │  │ MCP Server   │  │ Sandbox Runner           │  │
│  │ API Keys     │  │ JSON-RPC     │  │ Claude SDK + Tool Loop   │  │
│  │ Workspaces   │  │ WS + HTTP    │  │ Policy + Risk Scoring    │  │
│  │ RBAC         │  │              │  │                          │  │
│  └──────────────┘  └──────────────┘  └────────────┬─────────────┘  │
│                                                    │                │
│  ┌─────────────────────────────────────────────────▼─────────────┐  │
│  │ Sandbox Environment (in-memory per run)                       │  │
│  │ Filesystem │ Database Tables │ HTTP Stubs │ Email Log          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ Audit Log   │  │ Webhooks     │  │ Risk Engine│  │ Policies  │ │
│  │ Immutable   │  │ HMAC-signed  │  │ 5-dim score│  │ CRUD      │ │
│  └─────────────┘  └──────────────┘  └────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Features

### Stateful Sandbox Environments

Each run executes against an isolated, in-memory environment seeded with configurable data:

- **Filesystem**: Seed files at arbitrary paths — agents read real content, writes persist within the run
- **Database tables**: Define tables with row data — agents run SELECT/INSERT/UPDATE/DELETE against actual rows with WHERE, ORDER BY, LIMIT support
- **HTTP stubs**: Configure response patterns by URL regex — agents get realistic API responses
- **Emails**: All sends are captured with message IDs for review

Environment state is snapshotted before and after each run for comparison.

### MCP-Compatible Server

Drop-in replacement for a real MCP server. Existing Claude agents connect without modification.

**Supported methods:**
- `initialize` / `initialized`
- `tools/list` / `tools/call`
- `resources/list` / `resources/read`
- `ping`

**Transports:** WebSocket (primary) and HTTP POST.

```bash
# Create a session
curl -X POST http://localhost:8000/api/mcp/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "My Agent", "environment": {"database": {"users": [{"id": 1, "name": "Alice"}]}}}'

# Connect via WebSocket at the returned endpoint
# Or send JSON-RPC messages via HTTP POST
```

### Authentication & Workspaces

- **API key auth**: `X-API-Key` header for programmatic access
- **Workspace scoping**: All data (runs, policies, webhooks, audit logs) isolated per workspace
- **RBAC**: Three roles — `admin` (full access), `reviewer` (approve + create runs), `viewer` (read-only)
- **Development mode**: No key required — auto-creates a default workspace
- **SSO-ready**: Single middleware swap point for OAuth2/SAML/OIDC

```bash
# Create a workspace and get an API key
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name": "My Team"}'

# Use the key for all subsequent requests
curl http://localhost:8000/api/runs -H "X-API-Key: ask_..."
```

### Risk Scoring Engine

Every action is automatically scored across 5 dimensions:

| Dimension | What it detects |
|-----------|----------------|
| **Data Sensitivity** | PII patterns (emails, SSNs, credit cards), sensitive file paths (.env, credentials) |
| **Blast Radius** | Write operations count, systems affected, mutation scope |
| **Reversibility** | DELETE operations, destructive actions that can't be undone |
| **Privilege Escalation** | Agent reasoning about admin access, bypassing controls |
| **External Exposure** | Emails sent, HTTP to external/production URLs |

Output: 0-100 score with risk level (low/medium/high/critical), individual signals, and actionable recommendations.

### Policy Engine

Real-time rule enforcement during agent execution.

**Built-in policies (6):**
- Block production system access
- Limit email recipients
- Block dangerous SQL (DROP, TRUNCATE, unscoped DELETE)
- Warn on sensitive file access
- Limit mutation count per run
- Warn on external HTTP requests

**Custom policies**: Create workspace-specific rules with regex pattern matching on tool arguments. Full CRUD via API and UI.

### Run Comparison

Side-by-side diff of any two completed runs:

- Tool usage comparison (per-tool counts, unique tools)
- Risk score diff with level change detection
- Action sequence alignment (LCS similarity metric)
- Environment state diff (filesystem, database, emails)
- Human-readable summary

### Approval-Gated Replay

1. Run completes in sandbox with risk assessment
2. Reviewer approves/rejects with notes (HMAC-signed)
3. Approved runs can be:
   - **Replayed in sandbox** with environment overrides (A/B testing)
   - **Queued for live execution** (integration point for your execution backend)

### Audit Logging

Immutable append-only event log for SOC 2 / ISO 27001 compliance:

- Run lifecycle (created, completed, failed)
- Approval decisions with reviewer identity
- Policy changes
- API key operations
- Exports and replays
- Queryable by event type, resource, time range

### Webhook Notifications

Configurable per-workspace webhooks with:

- **Events**: `run.completed`, `run.failed`, `approval.submitted`, `policy.violation`, `risk.critical`, `risk.high`
- **Security**: HMAC-SHA256 payload signing
- **Reliability**: Retry with exponential backoff (3 attempts)
- **Observability**: Full delivery history with status codes

## API Reference

### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/runs` | Create and start a sandbox run |
| `GET` | `/api/runs` | List runs (filterable by status, agent_name; paginated) |
| `GET` | `/api/runs/{id}` | Get run with full action timeline |
| `POST` | `/api/runs/{id}/approve` | Submit approval decision |
| `GET` | `/api/runs/{id}/export` | Export compliance audit artifact |
| `POST` | `/api/runs/compare` | Compare two runs side-by-side |
| `POST` | `/api/runs/{id}/replay` | Replay in sandbox or queue for live |
| `WS` | `/api/runs/{id}/ws` | Stream live actions via WebSocket |

### MCP Server

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/mcp/sessions` | Create MCP session |
| `POST` | `/api/mcp/sessions/{id}/message` | Send JSON-RPC message |
| `WS` | `/api/mcp/sessions/{id}/ws` | MCP over WebSocket |
| `POST` | `/api/mcp/sessions/{id}/finalize` | Finalize session and compute risk |

### Workspaces & Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/workspaces/me` | Get current workspace |
| `POST` | `/api/workspaces` | Create workspace (returns admin API key) |
| `POST` | `/api/workspaces/api-keys` | Create API key (admin) |
| `GET` | `/api/workspaces/api-keys` | List API keys (admin) |
| `DELETE` | `/api/workspaces/api-keys/{key}` | Revoke API key (admin) |

### Policies

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/policies` | List built-in + custom policies |
| `POST` | `/api/policies` | Create custom policy (admin) |
| `PUT` | `/api/policies/{id}` | Update custom policy (admin) |
| `DELETE` | `/api/policies/{id}` | Delete custom policy (admin) |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/webhooks` | List webhooks |
| `POST` | `/api/webhooks` | Create webhook (admin) |
| `PUT` | `/api/webhooks/{id}` | Update webhook (admin) |
| `DELETE` | `/api/webhooks/{id}` | Delete webhook (admin) |
| `GET` | `/api/webhooks/{id}/deliveries` | Delivery history |
| `POST` | `/api/webhooks/{id}/test` | Send test event |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/templates` | List scenario templates |
| `GET` | `/api/templates/{id}` | Get template details |
| `GET` | `/api/analytics` | Workspace analytics |
| `GET` | `/api/audit` | Query audit log |
| `GET` | `/api/audit/summary` | Audit event counts |
| `GET` | `/api/health` | Health check |

## Mock Tools

Five MCP-style tools are available to agents:

| Tool | Description |
|------|-------------|
| `read_file` | Read file content from the sandbox filesystem |
| `write_file` | Write content to a file (persists in sandbox state) |
| `send_email` | Send email (captured in sandbox, not delivered) |
| `http_request` | Make HTTP request (matched against stubs or default responses) |
| `query_database` | Execute SQL against sandbox database tables |

## Scenario Templates

Six pre-built enterprise scenarios with full environment configs:

| Template | Category | Difficulty | Description |
|----------|----------|------------|-------------|
| CRM Lead Enrichment | Sales & CRM | Medium | Enrich leads via Clearbit API, update DB, notify sales |
| Incident Response | DevOps & SRE | High | Gather logs, query monitoring, draft status update, alert team |
| Employee Onboarding | HR & People Ops | Medium | Create accounts, generate docs, send welcome emails |
| Data Pipeline Audit | Data Engineering | Low | Read config, check run history, assess data quality |
| Security Access Review | Security & Compliance | High | Audit permissions, flag anomalies, generate compliance report |
| Customer Support Escalation | Customer Success | Medium | Gather account history, check tickets, draft response |

## Project Structure

```
backend/
  app/
    main.py                      # FastAPI app entry point
    auth.py                      # API key auth + RBAC middleware
    database.py                  # SQLAlchemy models + data stores
    models.py                    # Pydantic data models
    routers/
      runs.py                    # Run CRUD, approval, comparison, replay
      mcp.py                     # MCP JSON-RPC server endpoints
      workspaces.py              # Workspace + API key management
      templates.py               # Template library
      policies.py                # Policy CRUD
      analytics.py               # Workspace analytics
      audit.py                   # Audit log queries
      webhooks.py                # Webhook CRUD + test delivery
    services/
      sandbox_runner.py          # Claude agent execution loop
      sandbox_environment.py     # Stateful in-memory environment
      mcp_server.py              # MCP protocol implementation
      mock_tools.py              # Tool schemas + legacy registry
      risk_engine.py             # 5-dimension risk scoring
      policy_engine.py           # Built-in policy evaluation
      comparison.py              # Run diff engine
      audit_log.py               # Audit event logging
      webhooks.py                # Webhook delivery + HMAC signing
      templates.py               # Template definitions
  requirements.txt

frontend/
  src/
    App.tsx                      # Main app with tab navigation
    types/index.ts               # TypeScript interfaces
    hooks/useApi.ts              # API hooks + auth headers
    components/
      Dashboard.tsx              # KPIs, risk distribution, tool usage
      RunHistory.tsx             # Run list with search + filter
      RunDetail.tsx              # Full run inspection + snapshots
      NewRunForm.tsx             # Create run with environment editor
      ActionTimeline.tsx         # Action sequence visualization
      RiskPanel.tsx              # Risk scores + signals
      ApprovalPanel.tsx          # Approval + replay controls
      DiffView.tsx               # State change visualization
      RunComparison.tsx          # Side-by-side run diff
      EnvironmentEditor.tsx      # Seed data configuration UI
      TemplateLibrary.tsx        # Template browser
      PoliciesView.tsx           # Policy management UI
      AuditLog.tsx               # Audit log viewer
      WebhooksView.tsx           # Webhook management UI
      StatusBadge.tsx            # Status indicator
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, SQLite |
| AI | Anthropic SDK (Claude Sonnet) |
| Frontend | React 18, TypeScript, Vite 6, Tailwind CSS 3 |
| Real-time | WebSocket (native) |
| Auth | API key + HMAC-SHA256 signing |
| Webhooks | aiohttp with retry + HMAC-SHA256 |
