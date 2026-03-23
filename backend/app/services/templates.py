"""Template library — pre-built agent scenarios for common enterprise use cases.

Each template provides a complete agent definition + run context so teams
can immediately test realistic scenarios without writing configs from scratch.
"""

from __future__ import annotations

from ..models import AgentDefinition, RunContext, ToolConfig

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
            goal="P1 incident detected: 'Payment service returning 500 errors'. Handle this by: 1) Read the latest error logs from /var/log/payment-service/error.log, 2) Query the monitoring database for error rates (SELECT count(*), status_code FROM request_logs WHERE service='payment' AND timestamp > NOW() - INTERVAL '1 hour' GROUP BY status_code), 3) Check the deployment API for recent changes (GET https://deploy.internal.corp.com/api/v1/deployments?service=payment&limit=5), 4) Write a status page update to /var/www/status/incident-2025-001.md, 5) Send notification emails to oncall@ourcompany.com and engineering-leads@ourcompany.com with incident summary and initial findings.",
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
            goal="Perform Q1 2025 access review: 1) Query all users and their roles (SELECT u.name, u.email, u.role, u.last_login FROM users u ORDER BY u.last_login), 2) Query elevated permissions (SELECT * FROM permissions WHERE level='admin' OR level='superadmin'), 3) Check the identity provider for disabled accounts (GET https://identity.internal.corp.com/api/users?status=disabled), 4) Read the access policy document from /policies/access-control-policy.md, 5) Write the access review report to /reports/q1-2025-access-review.md listing all findings, 6) Send the report summary to security-team@ourcompany.com and compliance@ourcompany.com.",
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
