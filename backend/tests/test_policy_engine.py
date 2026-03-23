"""Tests for the policy engine — ensures every policy fires correctly."""

import pytest
from app.services.policy_engine import (
    MaxEmailRecipientsPolicy,
    MaxMutationsPolicy,
    NoDangerousSQLPolicy,
    NoExternalHTTPPolicy,
    NoProductionAccessPolicy,
    NoSensitiveFileAccessPolicy,
    PolicyAction,
    PolicyEngine,
    PolicyViolation,
)


# ── NoProductionAccessPolicy ────────────────────────────────────────────────

class TestNoProductionAccessPolicy:
    @pytest.fixture()
    def policy(self):
        return NoProductionAccessPolicy()

    @pytest.mark.parametrize("tool,args", [
        ("read_file", {"path": "/etc/production/config.yml"}),
        ("write_file", {"path": "/data/prod.db"}),
        ("http_request", {"url": "https://prod.api.com/v1/users"}),
        ("query_database", {"query": "SELECT * FROM production.users"}),
        ("read_file", {"path": "/var/log/prod-service/app.log"}),
    ])
    def test_blocks_production_access(self, policy, tool, args):
        v = policy.evaluate(tool, args)
        assert v is not None
        assert v.policy_action == PolicyAction.BLOCK

    @pytest.mark.parametrize("tool,args", [
        ("read_file", {"path": "/data/staging/config.yml"}),
        ("http_request", {"url": "https://api.staging.com/v1/users"}),
        ("query_database", {"query": "SELECT * FROM users"}),
    ])
    def test_allows_non_production(self, policy, tool, args):
        assert policy.evaluate(tool, args) is None


# ── MaxEmailRecipientsPolicy ───────────────────────────────────────────────

class TestMaxEmailRecipientsPolicy:
    def test_blocks_over_limit(self):
        policy = MaxEmailRecipientsPolicy(max_recipients=3)
        v = policy.evaluate("send_email", {"to": "a@x.com,b@x.com,c@x.com,d@x.com"})
        assert v is not None
        assert v.policy_action == PolicyAction.BLOCK

    def test_allows_under_limit(self):
        policy = MaxEmailRecipientsPolicy(max_recipients=3)
        assert policy.evaluate("send_email", {"to": "a@x.com,b@x.com"}) is None

    def test_ignores_non_email_tools(self):
        policy = MaxEmailRecipientsPolicy()
        assert policy.evaluate("read_file", {"path": "/x"}) is None


# ── NoDangerousSQLPolicy ──────────────────────────────────────────────────

class TestNoDangerousSQLPolicy:
    @pytest.fixture()
    def policy(self):
        return NoDangerousSQLPolicy()

    @pytest.mark.parametrize("query", [
        "DROP TABLE users",
        "DROP DATABASE main",
        "TRUNCATE orders",
        "DELETE FROM users;",
    ])
    def test_blocks_dangerous_sql(self, policy, query):
        v = policy.evaluate("query_database", {"query": query})
        assert v is not None
        assert v.policy_action == PolicyAction.BLOCK

    def test_allows_safe_queries(self, policy):
        assert policy.evaluate("query_database", {"query": "SELECT * FROM users WHERE id = 1"}) is None
        assert policy.evaluate("query_database", {"query": "DELETE FROM users WHERE id = 1"}) is None

    def test_ignores_non_db_tools(self, policy):
        assert policy.evaluate("read_file", {"path": "DROP TABLE"}) is None


# ── NoSensitiveFileAccessPolicy ───────────────────────────────────────────

class TestNoSensitiveFileAccessPolicy:
    @pytest.fixture()
    def policy(self):
        return NoSensitiveFileAccessPolicy()

    @pytest.mark.parametrize("path", [
        ".env",
        "config/.env.production",
        "credentials.json",
        "server.key",
        "cert.pem",
        "secrets.yml",
    ])
    def test_warns_on_sensitive_files(self, policy, path):
        v = policy.evaluate("read_file", {"path": path})
        assert v is not None
        assert v.policy_action == PolicyAction.WARN

    def test_allows_normal_files(self, policy):
        assert policy.evaluate("read_file", {"path": "README.md"}) is None
        assert policy.evaluate("write_file", {"path": "data.csv"}) is None


# ── MaxMutationsPolicy ────────────────────────────────────────────────────

class TestMaxMutationsPolicy:
    def test_triggers_after_limit(self):
        policy = MaxMutationsPolicy(max_mutations=2)
        assert policy.evaluate("write_file", {"path": "/a"}) is None
        assert policy.evaluate("write_file", {"path": "/b"}) is None
        v = policy.evaluate("write_file", {"path": "/c"})
        assert v is not None
        assert v.policy_action == PolicyAction.REQUIRE_APPROVAL

    def test_counts_all_write_types(self):
        policy = MaxMutationsPolicy(max_mutations=2)
        policy.evaluate("send_email", {"to": "x@x.com"})
        policy.evaluate("http_request", {"method": "POST", "url": "http://x"})
        v = policy.evaluate("query_database", {"query": "INSERT INTO t VALUES(1)"})
        assert v is not None

    def test_ignores_reads(self):
        policy = MaxMutationsPolicy(max_mutations=1)
        assert policy.evaluate("read_file", {"path": "/a"}) is None
        assert policy.evaluate("query_database", {"query": "SELECT * FROM t"}) is None
        assert policy.evaluate("http_request", {"method": "GET", "url": "http://x"}) is None


# ── NoExternalHTTPPolicy ──────────────────────────────────────────────────

class TestNoExternalHTTPPolicy:
    @pytest.fixture()
    def policy(self):
        return NoExternalHTTPPolicy(allowed_domains=["internal.corp.com"])

    def test_warns_external(self, policy):
        v = policy.evaluate("http_request", {"url": "https://evil.com/api"})
        assert v is not None
        assert v.policy_action == PolicyAction.WARN

    def test_allows_internal(self, policy):
        assert policy.evaluate("http_request", {"url": "https://internal.corp.com/api"}) is None

    def test_ignores_non_http(self, policy):
        assert policy.evaluate("read_file", {"path": "/x"}) is None


# ── PolicyEngine integration ──────────────────────────────────────────────

class TestPolicyEngine:
    def test_default_policies_loaded(self):
        engine = PolicyEngine()
        assert len(engine.policies) == 6

    def test_evaluate_returns_violations(self):
        engine = PolicyEngine()
        violations = engine.evaluate("read_file", {"path": "/etc/production/secrets.key"})
        # Should match production access (BLOCK) + sensitive file (WARN)
        assert len(violations) >= 1
        assert any(v.policy_action == PolicyAction.BLOCK for v in violations)

    def test_has_blockers_detects_block(self):
        engine = PolicyEngine()
        v = PolicyViolation("test", PolicyAction.BLOCK, "blocked")
        assert engine.has_blockers([v]) is True

    def test_has_blockers_detects_require_approval(self):
        engine = PolicyEngine()
        v = PolicyViolation("test", PolicyAction.REQUIRE_APPROVAL, "needs approval")
        assert engine.has_blockers([v]) is True

    def test_has_blockers_false_for_warn(self):
        engine = PolicyEngine()
        v = PolicyViolation("test", PolicyAction.WARN, "just a warning")
        assert engine.has_blockers([v]) is False

    def test_evaluate_sets_sequence(self):
        engine = PolicyEngine()
        violations = engine.evaluate("read_file", {"path": ".env"}, sequence=42)
        assert violations[0].action_sequence == 42

    def test_disabled_policies_skipped(self):
        engine = PolicyEngine()
        for p in engine.policies:
            p.enabled = False
        violations = engine.evaluate("read_file", {"path": ".env"})
        assert violations == []

    def test_get_policy_config(self):
        engine = PolicyEngine()
        config = engine.get_policy_config()
        assert len(config) == 6
        assert all("name" in c and "action" in c for c in config)
