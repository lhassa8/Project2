"""Template library — pre-built agent scenarios for common enterprise use cases.

Each template provides a complete agent definition + run context with rich
environment configs (filesystem, database tables, HTTP stubs) so the sandbox
produces realistic, consistent results.
"""

from __future__ import annotations

from ..models import AgentDefinition, EnvironmentConfig, RunContext, ToolConfig

TEMPLATES: dict[str, dict] = {
    "crm-lead-enrichment": {
        "name": "CRM Lead Enrichment",
        "description": "Agent enriches new CRM leads by querying external APIs, updating database records, and sending notification emails to the sales team.",
        "category": "Sales & CRM",
        "difficulty": "medium",
        "estimated_actions": 12,
        "agent_definition": AgentDefinition(
            name="Lead Enrichment Agent",
            goal="A new lead 'Acme Corp' (contact: jane@acme.com) was added to the CRM. Enrich this lead by: 1) Looking up company info via the Clearbit API (GET https://api.clearbit.com/v2/companies/find?domain=acme.com), 2) Query the database for any existing interactions (SELECT * FROM interactions WHERE company='Acme Corp'), 3) Update the lead record with enriched data (UPDATE leads SET enriched=true, company_size='500', industry='Technology' WHERE email='jane@acme.com'), 4) Send a summary email to sales@ourcompany.com with the enriched lead details.",
            tools=[
                ToolConfig(name="http_request", enabled=True),
                ToolConfig(name="query_database", enabled=True),
                ToolConfig(name="send_email", enabled=True),
                ToolConfig(name="read_file", enabled=False),
                ToolConfig(name="write_file", enabled=False),
            ],
        ).model_dump(),
        "run_context": RunContext(
            user_persona="Sales Operations Manager",
            initial_state={
                "crm_system": "Salesforce",
                "new_lead": {"company": "Acme Corp", "contact": "jane@acme.com", "source": "website"},
            },
            environment=EnvironmentConfig(
                database={
                    "leads": [
                        {"id": 1, "company": "Acme Corp", "email": "jane@acme.com", "enriched": False, "source": "website", "company_size": None, "industry": None},
                        {"id": 2, "company": "TechStart Inc", "email": "bob@techstart.io", "enriched": True, "source": "referral", "company_size": "50", "industry": "SaaS"},
                    ],
                    "interactions": [
                        {"id": 1, "company": "Acme Corp", "type": "website_visit", "date": "2025-01-10", "notes": "Viewed pricing page 3 times"},
                        {"id": 2, "company": "Acme Corp", "type": "demo_request", "date": "2025-01-12", "notes": "Requested enterprise demo via form"},
                        {"id": 3, "company": "Acme Corp", "type": "content_download", "date": "2025-01-14", "notes": "Downloaded ROI whitepaper"},
                    ],
                },
                http_stubs=[
                    {
                        "url_pattern": "clearbit.com",
                        "method": "GET",
                        "status_code": 200,
                        "response_body": {
                            "name": "Acme Corp",
                            "domain": "acme.com",
                            "category": {"sector": "Technology", "industryGroup": "Software"},
                            "metrics": {"employees": 500, "estimatedAnnualRevenue": "$50M-$100M", "raised": 50000000},
                            "location": "San Francisco, CA",
                            "description": "Enterprise collaboration platform",
                            "tech": ["Python", "React", "AWS", "PostgreSQL"],
                        },
                    },
                ],
            ),
        ).model_dump(),
    },
    "incident-response": {
        "name": "Incident Response Automation",
        "description": "Agent handles a P1 incident by gathering logs, querying monitoring systems, drafting a status page update, and notifying the on-call team.",
        "category": "DevOps & SRE",
        "difficulty": "high",
        "estimated_actions": 18,
        "agent_definition": AgentDefinition(
            name="Incident Response Agent",
            goal="P1 incident detected: 'Payment service returning 500 errors'. Handle this by: 1) Read the latest error logs from /var/log/payment-service/error.log, 2) Query the monitoring database for error rates (SELECT * FROM request_logs WHERE service='payment'), 3) Check the deployment API for recent changes (GET https://deploy.internal.corp.com/api/v1/deployments?service=payment&limit=5), 4) Write a status page update to /var/www/status/incident-2025-001.md, 5) Send notification emails to oncall@ourcompany.com and engineering-leads@ourcompany.com with incident summary and initial findings.",
            tools=[
                ToolConfig(name="read_file", enabled=True),
                ToolConfig(name="write_file", enabled=True),
                ToolConfig(name="query_database", enabled=True),
                ToolConfig(name="http_request", enabled=True),
                ToolConfig(name="send_email", enabled=True),
            ],
        ).model_dump(),
        "run_context": RunContext(
            user_persona="On-Call SRE Engineer",
            initial_state={
                "incident_id": "INC-2025-001",
                "severity": "P1",
                "service": "payment-service",
                "alert_source": "PagerDuty",
            },
            environment=EnvironmentConfig(
                filesystem={
                    "/var/log/payment-service/error.log": (
                        "[2025-01-20 14:32:01] ERROR PaymentProcessor: Connection timeout to payment gateway (attempt 1/3)\n"
                        "[2025-01-20 14:32:05] ERROR PaymentProcessor: Connection timeout to payment gateway (attempt 2/3)\n"
                        "[2025-01-20 14:32:09] ERROR PaymentProcessor: Connection timeout to payment gateway (attempt 3/3)\n"
                        "[2025-01-20 14:32:10] ERROR PaymentProcessor: HTTP 503 from gateway.stripe.internal\n"
                        "[2025-01-20 14:32:15] ERROR CircuitBreaker: OPEN state triggered for payment-gateway (threshold: 5 failures in 60s)\n"
                        "[2025-01-20 14:32:30] WARN  HealthCheck: Payment service health check failed - downstream dependency unavailable\n"
                        "[2025-01-20 14:33:01] ERROR PaymentProcessor: All retries exhausted, returning 500 to caller\n"
                        "[2025-01-20 14:33:15] FATAL PaymentService: Error rate exceeded 50% threshold, entering degraded mode\n"
                        "[2025-01-20 14:34:00] INFO  AutoScaler: Scaling payment-service from 3 to 6 replicas due to error rate\n"
                    ),
                    "/var/www/status/current.md": "# System Status\n\nAll systems operational.\n\nLast updated: 2025-01-20 14:00 UTC\n",
                },
                database={
                    "request_logs": [
                        {"id": 1, "service": "payment", "status_code": 500, "timestamp": "2025-01-20T14:32:01", "path": "/api/charge", "count": 142},
                        {"id": 2, "service": "payment", "status_code": 503, "timestamp": "2025-01-20T14:32:15", "path": "/api/charge", "count": 89},
                        {"id": 3, "service": "payment", "status_code": 200, "timestamp": "2025-01-20T14:30:00", "path": "/api/charge", "count": 1203},
                        {"id": 4, "service": "payment", "status_code": 200, "timestamp": "2025-01-20T14:00:00", "path": "/api/refund", "count": 45},
                        {"id": 5, "service": "user-auth", "status_code": 200, "timestamp": "2025-01-20T14:32:00", "path": "/api/login", "count": 567},
                    ],
                    "deployments": [
                        {"id": 1, "service": "payment", "version": "2.4.1", "deployed_at": "2025-01-20T13:45:00", "deployer": "ci-bot", "status": "success", "commit": "abc123f"},
                        {"id": 2, "service": "payment", "version": "2.4.0", "deployed_at": "2025-01-19T10:00:00", "deployer": "alice", "status": "success", "commit": "def456a"},
                        {"id": 3, "service": "payment", "version": "2.3.9", "deployed_at": "2025-01-17T15:30:00", "deployer": "bob", "status": "success", "commit": "ghi789b"},
                    ],
                },
                http_stubs=[
                    {
                        "url_pattern": "deploy.internal.corp.com",
                        "method": "GET",
                        "status_code": 200,
                        "response_body": {
                            "deployments": [
                                {"version": "2.4.1", "deployed_at": "2025-01-20T13:45:00", "commit": "abc123f", "deployer": "ci-bot", "changelog": "Fix: retry logic for gateway timeouts"},
                                {"version": "2.4.0", "deployed_at": "2025-01-19T10:00:00", "commit": "def456a", "deployer": "alice", "changelog": "Feature: add Stripe gateway fallback"},
                            ]
                        },
                    },
                ],
            ),
        ).model_dump(),
    },
    "employee-onboarding": {
        "name": "Employee Onboarding Workflow",
        "description": "Agent sets up a new employee by creating accounts, sending welcome emails, and preparing onboarding documents.",
        "category": "HR & People Ops",
        "difficulty": "medium",
        "estimated_actions": 14,
        "agent_definition": AgentDefinition(
            name="Onboarding Agent",
            goal="New employee starting: Sarah Chen, Engineering team, starting 2025-02-01. Complete onboarding: 1) Create user account in the identity system (POST https://identity.internal.corp.com/api/users with name, email, department, start_date), 2) Query the database for the Engineering team's onboarding checklist (SELECT * FROM onboarding_checklists WHERE department='Engineering'), 3) Generate a personalized welcome document and write it to /onboarding/sarah-chen/welcome.md, 4) Send welcome email to sarah.chen@ourcompany.com with first-day instructions, 5) Send notification to manager mike.johnson@ourcompany.com about the new hire setup, 6) Create a calendar invite via HTTP for the orientation session (POST https://calendar.internal.corp.com/api/events).",
            tools=[
                ToolConfig(name="http_request", enabled=True),
                ToolConfig(name="query_database", enabled=True),
                ToolConfig(name="send_email", enabled=True),
                ToolConfig(name="write_file", enabled=True),
                ToolConfig(name="read_file", enabled=True),
            ],
        ).model_dump(),
        "run_context": RunContext(
            user_persona="HR Operations Specialist",
            initial_state={
                "employee": {"name": "Sarah Chen", "email": "sarah.chen@ourcompany.com", "department": "Engineering", "manager": "Mike Johnson"},
                "start_date": "2025-02-01",
            },
            environment=EnvironmentConfig(
                database={
                    "onboarding_checklists": [
                        {"id": 1, "department": "Engineering", "item": "Set up development environment", "priority": 1, "owner": "IT"},
                        {"id": 2, "department": "Engineering", "item": "GitHub org invite and repo access", "priority": 2, "owner": "Engineering Lead"},
                        {"id": 3, "department": "Engineering", "item": "AWS IAM account creation", "priority": 3, "owner": "DevOps"},
                        {"id": 4, "department": "Engineering", "item": "Slack channels: #engineering, #standup, #incidents", "priority": 4, "owner": "IT"},
                        {"id": 5, "department": "Engineering", "item": "Schedule 1:1 with manager", "priority": 5, "owner": "HR"},
                        {"id": 6, "department": "Engineering", "item": "Security training completion", "priority": 6, "owner": "Security"},
                    ],
                    "employees": [
                        {"id": 1, "name": "Mike Johnson", "email": "mike.johnson@ourcompany.com", "department": "Engineering", "role": "Engineering Manager"},
                        {"id": 2, "name": "Alice Park", "email": "alice.park@ourcompany.com", "department": "Engineering", "role": "Senior Engineer"},
                    ],
                },
                http_stubs=[
                    {
                        "url_pattern": "identity.internal.corp.com/api/users",
                        "method": "POST",
                        "status_code": 201,
                        "response_body": {"user_id": "usr_sarah_chen_001", "email": "sarah.chen@ourcompany.com", "status": "active", "provisioned_at": "2025-01-25T10:00:00Z"},
                    },
                    {
                        "url_pattern": "calendar.internal.corp.com/api/events",
                        "method": "POST",
                        "status_code": 201,
                        "response_body": {"event_id": "evt_onboard_001", "title": "New Hire Orientation - Sarah Chen", "date": "2025-02-01T09:00:00Z", "status": "confirmed"},
                    },
                ],
            ),
        ).model_dump(),
    },
    "data-pipeline-audit": {
        "name": "Data Pipeline Audit",
        "description": "Agent audits a data pipeline by reading configs, querying run history, checking data quality, and generating a report.",
        "category": "Data Engineering",
        "difficulty": "low",
        "estimated_actions": 8,
        "agent_definition": AgentDefinition(
            name="Pipeline Audit Agent",
            goal="Audit the 'customer-analytics' data pipeline: 1) Read the pipeline configuration from /pipelines/customer-analytics/config.json, 2) Query the database for recent pipeline runs (SELECT * FROM pipeline_runs WHERE pipeline='customer-analytics' ORDER BY started_at DESC LIMIT 10), 3) Check the data quality API (GET https://dataquality.internal.corp.com/api/v1/reports?pipeline=customer-analytics&days=7), 4) Write an audit report to /reports/pipeline-audit-customer-analytics.md summarizing findings.",
            tools=[
                ToolConfig(name="read_file", enabled=True),
                ToolConfig(name="write_file", enabled=True),
                ToolConfig(name="query_database", enabled=True),
                ToolConfig(name="http_request", enabled=True),
                ToolConfig(name="send_email", enabled=False),
            ],
        ).model_dump(),
        "run_context": RunContext(
            user_persona="Data Engineering Lead",
            initial_state={
                "pipeline_name": "customer-analytics",
                "last_known_issue": "Data freshness delay on 2025-01-20",
            },
            environment=EnvironmentConfig(
                filesystem={
                    "/pipelines/customer-analytics/config.json": '{\n  "pipeline": "customer-analytics",\n  "version": "3.2.1",\n  "schedule": "0 */4 * * *",\n  "source": {\n    "type": "postgresql",\n    "database": "production_analytics",\n    "tables": ["events", "sessions", "conversions"]\n  },\n  "destination": {\n    "type": "bigquery",\n    "dataset": "analytics_warehouse",\n    "project": "acme-data-prod"\n  },\n  "transforms": [\n    {"name": "deduplicate_events", "type": "sql"},\n    {"name": "sessionize", "type": "python"},\n    {"name": "attribution_model", "type": "python"}\n  ],\n  "alerts": {\n    "freshness_threshold_hours": 6,\n    "row_count_drop_pct": 20,\n    "notify": ["data-team@ourcompany.com"]\n  }\n}',
                },
                database={
                    "pipeline_runs": [
                        {"id": 1, "pipeline": "customer-analytics", "started_at": "2025-01-20T16:00:00", "finished_at": "2025-01-20T16:23:45", "status": "success", "rows_processed": 145230},
                        {"id": 2, "pipeline": "customer-analytics", "started_at": "2025-01-20T12:00:00", "finished_at": "2025-01-20T12:18:32", "status": "success", "rows_processed": 132100},
                        {"id": 3, "pipeline": "customer-analytics", "started_at": "2025-01-20T08:00:00", "finished_at": None, "status": "failed", "rows_processed": 0},
                        {"id": 4, "pipeline": "customer-analytics", "started_at": "2025-01-20T04:00:00", "finished_at": "2025-01-20T04:21:10", "status": "success", "rows_processed": 98450},
                        {"id": 5, "pipeline": "customer-analytics", "started_at": "2025-01-20T00:00:00", "finished_at": "2025-01-20T00:19:55", "status": "success", "rows_processed": 87200},
                    ],
                },
                http_stubs=[
                    {
                        "url_pattern": "dataquality.internal.corp.com",
                        "method": "GET",
                        "status_code": 200,
                        "response_body": {
                            "pipeline": "customer-analytics",
                            "period": "7d",
                            "quality_score": 87,
                            "checks": [
                                {"name": "null_rate", "status": "pass", "value": 0.02, "threshold": 0.05},
                                {"name": "freshness", "status": "warn", "value": "8h", "threshold": "6h"},
                                {"name": "row_count_variance", "status": "pass", "value": 0.12, "threshold": 0.20},
                                {"name": "schema_drift", "status": "pass", "details": "No schema changes detected"},
                            ],
                            "last_failure": {"timestamp": "2025-01-20T08:00:00", "reason": "Source database connection timeout"},
                        },
                    },
                ],
            ),
        ).model_dump(),
    },
    "security-access-review": {
        "name": "Security Access Review",
        "description": "Agent performs a quarterly access review by checking user permissions, flagging anomalies, and generating a compliance report.",
        "category": "Security & Compliance",
        "difficulty": "high",
        "estimated_actions": 16,
        "agent_definition": AgentDefinition(
            name="Access Review Agent",
            goal="Perform Q1 2025 access review: 1) Query all users and their roles (SELECT * FROM users ORDER BY last_login), 2) Query elevated permissions (SELECT * FROM permissions WHERE level='admin' OR level='superadmin'), 3) Check the identity provider for disabled accounts (GET https://identity.internal.corp.com/api/users?status=disabled), 4) Read the access policy document from /policies/access-control-policy.md, 5) Write the access review report to /reports/q1-2025-access-review.md listing all findings, 6) Send the report summary to security-team@ourcompany.com and compliance@ourcompany.com.",
            tools=[
                ToolConfig(name="read_file", enabled=True),
                ToolConfig(name="write_file", enabled=True),
                ToolConfig(name="query_database", enabled=True),
                ToolConfig(name="http_request", enabled=True),
                ToolConfig(name="send_email", enabled=True),
            ],
        ).model_dump(),
        "run_context": RunContext(
            user_persona="Security Compliance Officer",
            initial_state={
                "review_period": "Q1 2025",
                "compliance_frameworks": ["SOC 2", "ISO 27001"],
            },
            environment=EnvironmentConfig(
                filesystem={
                    "/policies/access-control-policy.md": (
                        "# Access Control Policy v2.3\n\n"
                        "## Principles\n"
                        "1. **Least Privilege**: Users must only have access required for their role.\n"
                        "2. **Regular Review**: All elevated permissions reviewed quarterly.\n"
                        "3. **Separation of Duties**: No single user may both create and approve.\n"
                        "4. **Timely Deprovisioning**: Access removed within 24h of role change/termination.\n\n"
                        "## Elevated Access Requirements\n"
                        "- Admin access requires manager approval + security team sign-off.\n"
                        "- Superadmin restricted to SRE team leads (max 3 concurrent holders).\n"
                        "- All admin sessions logged and auditable.\n"
                        "- Inactive admin accounts (>90 days no login) auto-flagged for review.\n\n"
                        "## Compliance Controls\n"
                        "- SOC 2 CC6.1: Logical access controls implemented.\n"
                        "- ISO 27001 A.9.2.5: Review of user access rights at planned intervals.\n"
                    ),
                },
                database={
                    "users": [
                        {"id": 1, "name": "Alice Johnson", "email": "alice@corp.com", "role": "admin", "last_login": "2025-01-18", "department": "Engineering", "hire_date": "2022-03-15"},
                        {"id": 2, "name": "Bob Smith", "email": "bob@corp.com", "role": "editor", "last_login": "2025-01-20", "department": "Marketing", "hire_date": "2023-06-01"},
                        {"id": 3, "name": "Carol White", "email": "carol@corp.com", "role": "viewer", "last_login": "2024-11-05", "department": "Sales", "hire_date": "2021-09-20"},
                        {"id": 4, "name": "Dave Brown", "email": "dave@corp.com", "role": "admin", "last_login": "2025-01-19", "department": "SRE", "hire_date": "2020-01-10"},
                        {"id": 5, "name": "Eve Davis", "email": "eve@corp.com", "role": "superadmin", "last_login": "2025-01-20", "department": "SRE", "hire_date": "2019-07-01"},
                        {"id": 6, "name": "Frank Wilson", "email": "frank@corp.com", "role": "admin", "last_login": "2024-09-15", "department": "Finance", "hire_date": "2022-11-01"},
                        {"id": 7, "name": "Grace Lee", "email": "grace@corp.com", "role": "viewer", "last_login": "2025-01-20", "department": "Engineering", "hire_date": "2024-01-15"},
                    ],
                    "permissions": [
                        {"id": 1, "user_id": 1, "level": "admin", "resource": "production-db", "granted_at": "2024-06-01", "granted_by": "eve@corp.com", "justification": "On-call database access"},
                        {"id": 2, "user_id": 4, "level": "admin", "resource": "infrastructure", "granted_at": "2024-03-15", "granted_by": "eve@corp.com", "justification": "SRE infrastructure management"},
                        {"id": 3, "user_id": 5, "level": "superadmin", "resource": "*", "granted_at": "2024-01-01", "granted_by": "cto@corp.com", "justification": "SRE Lead - break-glass access"},
                        {"id": 4, "user_id": 6, "level": "admin", "resource": "finance-systems", "granted_at": "2024-04-10", "granted_by": "cfo@corp.com", "justification": "Financial reporting access"},
                    ],
                },
                http_stubs=[
                    {
                        "url_pattern": "identity.internal.corp.com",
                        "method": "GET",
                        "status_code": 200,
                        "response_body": {
                            "disabled_accounts": [
                                {"email": "former.employee@corp.com", "disabled_at": "2024-12-01", "reason": "termination", "had_admin": True},
                                {"email": "contractor.temp@corp.com", "disabled_at": "2025-01-05", "reason": "contract_ended", "had_admin": False},
                                {"email": "intern.summer@corp.com", "disabled_at": "2024-09-01", "reason": "internship_ended", "had_admin": False},
                            ]
                        },
                    },
                ],
            ),
        ).model_dump(),
    },
    "customer-support-escalation": {
        "name": "Customer Support Escalation",
        "description": "Agent handles a VIP customer escalation by gathering account history, checking recent tickets, and drafting a personalized response.",
        "category": "Customer Success",
        "difficulty": "medium",
        "estimated_actions": 10,
        "agent_definition": AgentDefinition(
            name="Support Escalation Agent",
            goal="Handle VIP escalation from customer 'GlobalTech Inc' (contact: cto@globaltech.io): 1) Query their account history (SELECT * FROM customers WHERE company='GlobalTech Inc'), 2) Check recent support tickets (SELECT * FROM tickets WHERE customer_id=42 ORDER BY created_at DESC LIMIT 5), 3) Look up their subscription details (GET https://billing.internal.corp.com/api/subscriptions?customer_id=42), 4) Draft a personalized response email to cto@globaltech.io addressing their concerns, 5) Send an internal notification to vp-cs@ourcompany.com about the escalation.",
            tools=[
                ToolConfig(name="query_database", enabled=True),
                ToolConfig(name="http_request", enabled=True),
                ToolConfig(name="send_email", enabled=True),
                ToolConfig(name="read_file", enabled=False),
                ToolConfig(name="write_file", enabled=False),
            ],
        ).model_dump(),
        "run_context": RunContext(
            user_persona="VP of Customer Success",
            initial_state={
                "customer": {"name": "GlobalTech Inc", "tier": "Enterprise", "arr": "$240,000"},
                "escalation_reason": "Repeated API outages affecting their integration",
            },
            environment=EnvironmentConfig(
                database={
                    "customers": [
                        {"id": 42, "company": "GlobalTech Inc", "contact_name": "James Chen", "contact_email": "cto@globaltech.io", "tier": "Enterprise", "arr": 240000, "joined": "2023-03-15", "health_score": 62},
                    ],
                    "tickets": [
                        {"id": 501, "customer_id": 42, "subject": "API returning 502 errors intermittently", "status": "open", "priority": "high", "created_at": "2025-01-18T09:30:00", "assigned_to": "support-team"},
                        {"id": 487, "customer_id": 42, "subject": "Webhook delivery delays >5 minutes", "status": "resolved", "priority": "medium", "created_at": "2025-01-10T14:00:00", "assigned_to": "eng-team"},
                        {"id": 465, "customer_id": 42, "subject": "API rate limit exceeded during bulk import", "status": "resolved", "priority": "high", "created_at": "2024-12-28T11:15:00", "assigned_to": "eng-team"},
                        {"id": 441, "customer_id": 42, "subject": "Dashboard loading timeout for large datasets", "status": "resolved", "priority": "low", "created_at": "2024-12-15T16:45:00", "assigned_to": "frontend-team"},
                        {"id": 420, "customer_id": 42, "subject": "SSO integration not redirecting properly", "status": "resolved", "priority": "medium", "created_at": "2024-12-01T08:00:00", "assigned_to": "auth-team"},
                    ],
                },
                http_stubs=[
                    {
                        "url_pattern": "billing.internal.corp.com",
                        "method": "GET",
                        "status_code": 200,
                        "response_body": {
                            "customer_id": 42,
                            "plan": "Enterprise",
                            "mrr": 20000,
                            "contract_end": "2025-09-15",
                            "api_calls_this_month": 2450000,
                            "api_limit": 5000000,
                            "features": ["SSO", "dedicated_support", "custom_webhooks", "priority_routing"],
                            "payment_status": "current",
                        },
                    },
                ],
            ),
        ).model_dump(),
    },
}


def list_templates() -> list[dict]:
    """Return all templates with metadata (no full definitions)."""
    return [
        {
            "id": tid,
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "difficulty": t["difficulty"],
            "estimated_actions": t["estimated_actions"],
        }
        for tid, t in TEMPLATES.items()
    ]


def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)
